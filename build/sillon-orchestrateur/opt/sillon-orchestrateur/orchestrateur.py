"""SILLON - Orchestrateur applicatif.

Service HTTP synchrone (Flask/Gunicorn) exposé derrière Nginx sous
/orchestrateur/, complété par un consommateur asynchrone en tâche de fond
pour la file d'attente. Couvre les opérations que l'API de requêtage seule
ne peut pas exécuter (§4.4 du cahier des charges) : création/suppression de
base, requêtes SQL libres, import CSV, complément multi-base du partage.

Chaque worker Gunicorn démarre sa propre écoute LISTEN/NOTIFY (§9) ; le
verrouillage "FOR UPDATE SKIP LOCKED" lors de la prise en charge d'un job
rend cette redondance sûre plutôt que problématique (aucun job n'est traité
deux fois, quel que soit le nombre de workers).
"""

import csv
import io
import json
import mimetypes
import os
import queue
import re
import smtplib
import threading
import time
import unicodedata
import uuid
import zipfile
from datetime import date, datetime
from email.message import EmailMessage

import jwt
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from flask import Flask, Response, g, jsonify, request, send_file, stream_with_context

# =============================================================================
# CONFIGURATION (§4.3, §12.2)
# =============================================================================
JWT_SECRET = os.environ["SILLON_JWT_SECRET"]
DB_HOST = os.environ.get("SILLON_DB_HOST", "localhost")
DB_PORT = os.environ.get("SILLON_DB_PORT", "5432")
DB_NAME = os.environ.get("SILLON_DB_NAME", "sillon_catalog")
DB_USER = "sillon_orchestrateur"
DB_PASSWORD = os.environ["SILLON_ORCHESTRATEUR_PASS"]
SMTP_HOTE = os.environ.get("SILLON_SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SILLON_SMTP_PORT", "25"))
SMTP_EXPEDITEUR = os.environ.get("SILLON_SMTP_FROM", "sillon@sillon.local")
URL_APPLICATION = os.environ.get("SILLON_URL", "https://localhost")

# Repertoire de dépôt temporaire des CSV en cours de qualification (§5.1) :
# créé au démarrage, avec repli sur /tmp si /var/lib/sillon n'est pas encore
# préparé côté paquet (à ajouter au postinst - voir note de fin de fichier).
STAGING_DIR = os.environ.get("SILLON_STAGING_DIR", "/var/lib/sillon/staging")
try:
    os.makedirs(STAGING_DIR, exist_ok=True)
except OSError:
    import tempfile

    STAGING_DIR = os.path.join(tempfile.gettempdir(), "sillon-staging")
    os.makedirs(STAGING_DIR, exist_ok=True)

# Même répertoire et même convention de repli que sillon-worker (§5.4) : les
# résultats de job, quel que soit le processus qui les produit, sont tous
# servis par le même endpoint /jobs/<id>/telecharger (§8.10), qui ne
# s'intéresse qu'au chemin enregistré en base.
RESULTATS_DIR = os.environ.get("SILLON_RESULTATS_DIR", "/var/lib/sillon/resultats")
try:
    os.makedirs(RESULTATS_DIR, exist_ok=True)
except OSError:
    import tempfile

    RESULTATS_DIR = os.path.join(tempfile.gettempdir(), "sillon-resultats")
    os.makedirs(RESULTATS_DIR, exist_ok=True)

TYPES_SQL = {
    "Texte": "TEXT",
    "Entier": "BIGINT",
    "Décimal": "NUMERIC",
    "Date": "DATE",
    "Date/Heure": "TIMESTAMP",
    "Booléen": "BOOLEAN",
    "JSON": "JSONB",
}

app = Flask(__name__)


# =============================================================================
# ACCES A LA BASE DE DONNEES (§4.3, §4.4)
# =============================================================================
def connexion_catalogue(claims=None):
    """Connexion au catalogue avec le rôle sillon_orchestrateur.

    Sans argument : identité propre de l'orchestrateur, pour ses lectures
    internes (quotas, résolution nom_pg/role_pg - §4.4), couvertes par des
    GRANT dédiés (schema.sql §10) distincts des droits des profils
    utilisateurs.

    Avec `claims` : bascule en plus vers le rôle personnel de l'appelant
    ET pose "request.jwt.claims" (§4.3), exactement comme le ferait l'API
    de requêtage - indispensable pour tout appel à une fonction ou une vue
    qui s'appuie sur _id_courant() (creer_job, partager_base,
    revoquer_partage, vue_mes_bases...).
    """
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    if claims:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(claims["role"])))
            cur.execute("SELECT set_config('request.jwt.claims', %s, false)", (json.dumps(claims),))
    return conn


def connexion_base(nom_pg, role_pg):
    """Connexion à une base utilisateur avec le rôle personnel de
    l'appelant (§4.4, §8.8) : la portée des droits est celle de ce rôle,
    jamais plus."""
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=nom_pg, user=DB_USER, password=DB_PASSWORD)
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_pg)))
    return conn


def lire_parametre(cle, defaut=None):
    with connexion_catalogue() as conn, conn.cursor() as cur:
        cur.execute("SELECT valeur FROM public.parametres WHERE cle = %s", (cle,))
        ligne = cur.fetchone()
    return ligne[0] if ligne else defaut


# =============================================================================
# AUTHENTIFICATION (§4.3, §8.1, §8.2)
# =============================================================================
class ErreurAuthentification(Exception):
    pass


def verifier_jeton():
    """Extrait et vérifie le jeton JWT posé par Nginx dans l'en-tête
    Authorization à partir du cookie HttpOnly (§4.3, §8.2)."""
    entete = request.headers.get("Authorization", "")
    if not entete.startswith("Bearer "):
        raise ErreurAuthentification("Jeton absent")
    jeton = entete[len("Bearer "):]
    try:
        claims = jwt.decode(jeton, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise ErreurAuthentification(f"Jeton invalide : {exc}") from exc

    # Le controle d'acces reel est le "SET ROLE" lui-meme (§8.2, §8.3) : un
    # compte desactive perd la qualite de membre de sillon_orchestrateur
    # (schema.sql, fonction desactiver_utilisateur), donc cette bascule
    # echoue d'elle-meme, sans verification dupliquee cote applicatif.
    try:
        conn = connexion_catalogue(claims=claims)
        conn.close()
    except psycopg2.Error as exc:
        raise ErreurAuthentification("Compte désactivé ou rôle invalide") from exc

    return claims


@app.before_request
def authentifier():
    try:
        g.claims = verifier_jeton()
    except ErreurAuthentification as exc:
        return jsonify(erreur=str(exc)), 401


# =============================================================================
# UTILITAIRES SQL LIBRE (§5.3, §8.8)
# =============================================================================
_MOTS_ECRITURE = re.compile(r"^\s*(insert|update|delete|create|drop|alter|truncate|grant|revoke)\b", re.IGNORECASE)


def est_requete_lecture(texte_sql):
    """Détection du type de requête (§5.3) : heuristique par mot-clé de
    tête, suffisante pour distinguer confirmation requise ou non côté
    interface - la portée réelle des dégâts possibles reste bornée par le
    rôle Postgres de l'appelant (§8.8), pas par cette détection."""
    return not _MOTS_ECRITURE.match(texte_sql.strip())


def base_accessible(claims, base_id, exiger_script=False):
    """Vérifie que l'appelant a accès à la base (propriétaire ou
    bénéficiaire d'un partage, §8.4) et retourne son nom PostgreSQL, ou
    None si l'accès est refusé.

    `exiger_script=True` ajoute la contrainte du §5.2 : le partage donne un
    accès en lecture par défaut, l'exécution de script est une autorisation
    distincte que seul le propriétaire n'a pas besoin qu'on lui accorde
    explicitement (autorise_scripts vaut NULL pour ses propres bases,
    vue_mes_bases §7 du schéma)."""
    with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT nom_pg, je_suis_proprietaire, autorise_scripts FROM public.vue_mes_bases WHERE id = %s",
            (base_id,),
        )
        ligne = cur.fetchone()
    if not ligne:
        return None
    nom_pg, je_suis_proprietaire, autorise_scripts = ligne
    if exiger_script and not je_suis_proprietaire and not autorise_scripts:
        return None
    return nom_pg


def base_dont_je_suis_proprietaire(claims, base_id):
    """Comme base_accessible, mais réservé aux actions du §5.2 marquées
    « Propriétaire uniquement » (partage, suppression de table ou de
    base) : un accès en lecture seule ne suffit pas."""
    with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT nom_pg FROM public.vue_mes_bases WHERE id = %s AND je_suis_proprietaire",
            (base_id,),
        )
        ligne = cur.fetchone()
    return ligne[0] if ligne else None


# =============================================================================
# ENDPOINT : REQUETES SQL LIBRES (§5.3, §8.8)
# =============================================================================
LIGNES_MAX_APERCU = 1000


def _serialiser(valeur):
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    return valeur


def enregistrer_historique(claims, base_id, requete, type_requete, succes, duree_ms, message_erreur=None):
    """Historique persistant des requêtes (§5.3) : ne doit jamais faire
    échouer l'exécution elle-même si l'écriture de l'historique échoue -
    d'où le try/except centralisé ici plutôt que répété à chaque appelant."""
    try:
        with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT public.enregistrer_historique(%s, %s, %s, %s, %s, %s)",
                (base_id, requete, type_requete, succes, duree_ms, message_erreur),
            )
            conn.commit()
    except psycopg2.Error:
        pass


@app.route("/sql", methods=["POST"])
def executer_sql():
    donnees = request.get_json(force=True)
    base_id = donnees.get("base_id")
    requete_utilisateur = (donnees.get("requete") or "").strip()
    if not requete_utilisateur:
        return jsonify(erreur="Requête vide"), 400

    nom_pg = base_accessible(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    delai_minutes = int(lire_parametre("duree_max_job_minutes", "30"))
    lecture = est_requete_lecture(requete_utilisateur)
    type_requete = "lecture" if lecture else "ecriture"
    debut = time.monotonic()

    try:
        conn = connexion_base(nom_pg, g.claims["role"])
    except psycopg2.Error as exc:
        return jsonify(erreur=f"Connexion refusée : {exc}"), 403

    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("SET LOCAL statement_timeout = {}").format(sql.Literal(f"{delai_minutes}min")))

            if lecture:
                # Enveloppe non destructive : permet de compter jusqu'à
                # LIGNES_MAX_APERCU + 1 lignes pour savoir si le résultat
                # affiché à l'écran est tronqué, sans limiter l'export
                # complet (§5.3 : l'affichage et l'export n'ont pas la
                # même limite).
                requete_enveloppee = sql.SQL("SELECT * FROM ({}) AS _sillon_apercu LIMIT {}").format(
                    sql.SQL(requete_utilisateur), sql.Literal(LIGNES_MAX_APERCU + 1)
                )
                cur.execute(requete_enveloppee)
                colonnes = [d.name for d in cur.description]
                lignes = cur.fetchall()
                tronque = len(lignes) > LIGNES_MAX_APERCU
                lignes = lignes[:LIGNES_MAX_APERCU]
                conn.rollback()  # aucune écriture n'est jamais laissée en attente pour une lecture
                resultat = {
                    "type": "lecture",
                    "colonnes": colonnes,
                    "lignes": [[_serialiser(v) for v in ligne] for ligne in lignes],
                    "tronque": tronque,
                    "duree_ms": round((time.monotonic() - debut) * 1000),
                }
            else:
                cur.execute(requete_utilisateur)
                lignes_affectees = cur.rowcount
                conn.commit()
                resultat = {
                    "type": "ecriture",
                    "lignes_affectees": lignes_affectees,
                    "duree_ms": round((time.monotonic() - debut) * 1000),
                }
        enregistrer_historique(g.claims, base_id, requete_utilisateur, type_requete, True, resultat["duree_ms"])
        return jsonify(resultat)
    except psycopg2.Error as exc:
        conn.rollback()
        duree_ms = round((time.monotonic() - debut) * 1000)
        enregistrer_historique(g.claims, base_id, requete_utilisateur, type_requete, False, duree_ms, str(exc))
        # 57014 = query_canceled (SQLSTATE) : le cas précis du statement_timeout
        # ci-dessus, à distinguer d'une erreur SQL ordinaire pour orienter
        # l'utilisateur vers l'exécution en tâche de fond (§5.3, §11).
        if exc.pgcode == "57014":
            return jsonify(
                erreur=f"Requête interrompue : délai maximal dépassé ({delai_minutes} min).",
                delai_depasse=True,
            ), 400
        return jsonify(erreur=str(exc)), 400
    finally:
        conn.close()


@app.route("/sql/job", methods=["POST"])
def executer_sql_en_tache_de_fond():
    """Bascule d'une exécution longue en job asynchrone (§5.3, §11) : même
    requête, même délai maximal (duree_max_job_minutes), mais exécutée en
    fond avec notification par mail plutôt que de bloquer la requête HTTP
    synchrone (et le navigateur avec elle) jusqu'à 30 minutes."""
    donnees = request.get_json(force=True)
    base_id = donnees.get("base_id")
    requete_utilisateur = (donnees.get("requete") or "").strip()
    if not requete_utilisateur:
        return jsonify(erreur="Requête vide"), 400

    nom_pg = base_accessible(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    # try/except (constaté en pratique) : sans lui, un quota de jobs
    # simultanés déjà atteint (creer_job, §11) ou tout autre refus
    # PostgreSQL remontait en 500 générique non intercepté au lieu d'un
    # message clair - même garde que /scripts/deposer pour le même appel.
    with connexion_catalogue(claims=g.claims) as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT public.creer_job('requete_sql', %s, %s::jsonb)",
                (base_id, psycopg2.extras.Json({
                    "requete": requete_utilisateur,
                    "role_pg": g.claims["role"],
                    "nom_pg": nom_pg,
                })),
            )
        except psycopg2.Error as exc:
            return jsonify(erreur=str(exc)), 400
        id_job = cur.fetchone()[0]
        conn.commit()

    return jsonify(statut="en_attente", id_job=id_job)


@app.route("/sql/export", methods=["POST"])
def exporter_sql():
    donnees = request.get_json(force=True)
    base_id = donnees.get("base_id")
    requete_utilisateur = (donnees.get("requete") or "").strip()

    nom_pg = base_accessible(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404
    if not est_requete_lecture(requete_utilisateur):
        return jsonify(erreur="Seule une requête de lecture peut être exportée"), 400

    delai_minutes = int(lire_parametre("duree_max_job_minutes", "30"))
    role_pg = g.claims["role"]
    resultat_erreur = {}

    # Pont entre l'écriture synchrone de psycopg2 (COPY TO STDOUT) et un
    # générateur Flask en flux : une file bornée absorbe la contrepression
    # du client HTTP sans jamais retenir l'export entier en mémoire (§13).
    tampon = queue.Queue(maxsize=8)
    FIN = object()

    class AdaptateurFlux:
        def write(self, donnees_brutes):
            tampon.put(bytes(donnees_brutes))

    def produire():
        try:
            conn = connexion_base(nom_pg, role_pg)
            try:
                with conn.cursor() as cur:
                    cur.execute(sql.SQL("SET LOCAL statement_timeout = {}").format(sql.Literal(f"{delai_minutes}min")))
                    requete_copy = sql.SQL(
                        "COPY ({}) TO STDOUT WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
                    ).format(sql.SQL(requete_utilisateur))
                    cur.copy_expert(requete_copy.as_string(conn), AdaptateurFlux())
                conn.commit()
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001 - relayé au flux, cf. limite ci-dessous
            resultat_erreur["message"] = str(exc)
        finally:
            tampon.put(FIN)

    threading.Thread(target=produire, daemon=True).start()

    def flux():
        while True:
            bloc = tampon.get()
            if bloc is FIN:
                # Limite connue : une erreur survenant après le premier
                # bloc envoyé ne peut plus être signalée par un code HTTP
                # (les en-têtes sont déjà partis) - seule la troncature du
                # fichier le révèle côté client pour cette première version.
                break
            yield bloc

    return Response(
        stream_with_context(flux()),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=export.csv"},
    )


# =============================================================================
# UTILITAIRES IMPORT CSV (§5.1, §7.4)
# =============================================================================
def normaliser_identifiant(texte, longueur_max=63):
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")
    texte = re.sub(r"[^a-zA-Z0-9_]", "_", texte).strip("_").lower()
    if not texte or texte[0].isdigit():
        texte = "t_" + texte
    return texte[:longueur_max] or "table"


def detecter_encodage(donnees_brutes):
    try:
        donnees_brutes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        import chardet

        detection = chardet.detect(donnees_brutes[:100_000])
        if detection.get("encoding"):
            return detection["encoding"]
    except ImportError:
        pass
    return "latin-1"  # repli usuel pour les exports administratifs (§5.1)


def detecter_delimiteur(echantillon_texte):
    # "|" ajouté après coup : certains jeux de données administratifs
    # volumineux (ex. Demandes de Valeurs Foncières / DGFiP) l'utilisent
    # au lieu de ";", jamais couvert par le jeu de candidats initial.
    try:
        return csv.Sniffer().sniff(echantillon_texte, delimiters=";,\t|").delimiter
    except csv.Error:
        return ";"  # repli usuel des exports français (§5.1)


def suggerer_type(valeurs):
    valeurs = [v for v in valeurs if v not in ("", None)]
    if not valeurs:
        return "Texte"
    if all(v.lower() in ("vrai", "faux", "true", "false", "0", "1") for v in valeurs):
        return "Booléen"
    try:
        for v in valeurs:
            int(v)
        return "Entier"
    except ValueError:
        pass
    try:
        for v in valeurs:
            float(v.replace(",", "."))
        return "Décimal"
    except ValueError:
        pass
    for motif in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            for v in valeurs:
                datetime.strptime(v, motif)
            return "Date"
        except ValueError:
            continue
    return "Texte"


# Mêmes formats acceptés que suggerer_type() ci-dessus (booléens, dates), mais
# ici pour valider une valeur contre un type déjà choisi par l'utilisateur,
# pas pour en deviner un - Date/Heure et JSON n'apparaissent donc que dans
# cette fonction, jamais suggérés automatiquement.
def valeur_valide_pour_type(valeur, type_col, valeur_manquante):
    if valeur == valeur_manquante:
        return True  # converti en NULL à l'import (§5.1 étape 5) : jamais une anomalie de type
    if type_col == "Texte":
        return True
    if type_col == "Entier":
        try:
            int(valeur)
            return True
        except ValueError:
            return False
    if type_col == "Décimal":
        try:
            float(valeur.replace(",", "."))
            return True
        except ValueError:
            return False
    if type_col == "Booléen":
        return valeur.lower() in ("vrai", "faux", "true", "false", "0", "1")
    if type_col in ("Date", "Date/Heure"):
        motifs = ("%Y-%m-%d", "%d/%m/%Y") if type_col == "Date" \
            else ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S")
        return any(_motif_correspond(valeur, motif) for motif in motifs)
    if type_col == "JSON":
        try:
            json.loads(valeur)
            return True
        except ValueError:
            return False
    return True


def _motif_correspond(valeur, motif):
    try:
        datetime.strptime(valeur, motif)
        return True
    except ValueError:
        return False


# =============================================================================
# ENDPOINT : CONTROLE DE COHERENCE AVANT VALIDATION (§5.1, étape 4)
# =============================================================================
# Nombre d'anomalies détaillées renvoyées au client : un fichier massivement
# mal typé pourrait sinon produire une réponse JSON disproportionnée (§13).
# lignes_anomalies (les seuls numéros, pas le détail) reste lui complet :
# nécessaire à l'exclusion demandée à l'étape suivante, qui doit pouvoir
# écarter CHAQUE ligne en anomalie, pas seulement les premières affichées.
ANOMALIES_DETAIL_MAX = 200


@app.route("/import/verifier", methods=["POST"])
def verifier_import():
    donnees = request.get_json(force=True)
    jeton = donnees.get("jeton")
    colonnes = donnees.get("colonnes") or []
    encodage = donnees.get("encodage") or "utf-8"
    delimiteur = donnees.get("delimiteur") or ";"
    valeur_manquante = donnees.get("valeur_manquante") or ""
    avec_entete = bool(donnees.get("avec_entete", True))

    chemin_fichier = os.path.join(STAGING_DIR, f"{jeton}.csv")
    if not jeton or not os.path.isfile(chemin_fichier):
        return jsonify(erreur="Fichier en attente introuvable ou expiré"), 404
    for c in colonnes:
        if c.get("type") not in TYPES_SQL:
            return jsonify(erreur=f"Type de colonne invalide : {c.get('type')}"), 400

    anomalies_detail = []
    lignes_anomalies = []
    nb_lignes_totales = 0
    with open(chemin_fichier, "r", encoding=encodage, newline="", errors="replace") as f:
        lecteur = csv.reader(f, delimiter=delimiteur)
        if avec_entete:
            next(lecteur, None)
        for numero_ligne, ligne in enumerate(lecteur, start=1):
            nb_lignes_totales += 1
            ligne_en_anomalie = False
            for i, c in enumerate(colonnes):
                if i >= len(ligne):
                    continue
                if not valeur_valide_pour_type(ligne[i], c["type"], valeur_manquante):
                    ligne_en_anomalie = True
                    if len(anomalies_detail) < ANOMALIES_DETAIL_MAX:
                        anomalies_detail.append({
                            "ligne": numero_ligne, "colonne": c["nom_normalise"], "valeur": ligne[i],
                        })
            if ligne_en_anomalie:
                lignes_anomalies.append(numero_ligne)

    return jsonify({
        "nb_lignes_totales": nb_lignes_totales,
        "nb_lignes_anomalies": len(lignes_anomalies),
        "anomalies": anomalies_detail,
        "lignes_anomalies": lignes_anomalies,
    })


# =============================================================================
# ENDPOINT : APERCU D'IMPORT (§5.1, étapes 1 à 3)
# =============================================================================
@app.route("/import/apercu", methods=["POST"])
def apercu_import():
    fichier = request.files.get("fichier")
    if not fichier:
        return jsonify(erreur="Aucun fichier reçu"), 400

    # Écrit directement en flux vers le répertoire de dépôt (Werkzeug lit
    # le corps de la requête par blocs, jamais un .read() unique) : un
    # fichier de plusieurs centaines de Mo ne doit jamais transiter par un
    # seul objet bytes/str en mémoire (§12/§13) - constaté en pratique
    # avec un vrai jeu de données de test (~500 Mo).
    jeton = uuid.uuid4().hex
    chemin_stage = os.path.join(STAGING_DIR, f"{jeton}.csv")
    fichier.save(chemin_stage)

    avec_entete = request.form.get("avec_entete", "true").lower() != "false"
    return _analyser_fichier_stage(jeton, chemin_stage, avec_entete)


# =============================================================================
# ENDPOINT : APERCU D'IMPORT - DEPOT LOCAL DIRECT (§12.8)
# =============================================================================
# Une requête HTTP multipart classique (/import/apercu) fait transiter le
# fichier par deux tampons disque successifs (celui de Werkzeug le temps
# du parsing, puis la copie de fichier.save()) - négligeable pour un import
# ordinaire, mais un fichier de plusieurs Go en fait déjà trois copies
# simultanées avec celle du script appelant, pour un gain nul quand ce
# dernier tourne déjà sur la même machine que l'orchestrateur (§12.8,
# sillon-demo-sirene : constaté en pratique, "No space left on device" sur
# la VM de test avec seulement 9 Go libres). Cet endpoint se contente d'un
# renommage (même disque, donc atomique et sans copie) plutôt que d'une
# réception réseau.
#
# Jamais exposé publiquement (bloqué explicitement côté Nginx, cf.
# sillon-server/etc/nginx/sites-available/sillon) : accessible uniquement
# en direct sur 127.0.0.1:5000, jamais via le reverse proxy - sans quoi un
# agent authentifié quelconque pourrait faire lire n'importe quel fichier
# accessible à www-data. Restreint en plus, ici, à un unique répertoire de
# dépôt local (jamais un chemin arbitraire, même pour un appel qui
# parviendrait malgré tout jusqu'ici).
REPERTOIRE_DEPOT_LOCAL = os.path.realpath("/var/lib/sillon-demo-sirene")


@app.route("/import/apercu_local", methods=["POST"])
def apercu_import_local():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(erreur="Endpoint réservé aux appels locaux"), 403

    donnees = request.get_json(force=True)
    chemin_source = os.path.realpath(donnees.get("chemin") or "")
    if not chemin_source.startswith(REPERTOIRE_DEPOT_LOCAL + os.sep):
        return jsonify(erreur="Chemin source non autorisé"), 400
    if not os.path.isfile(chemin_source):
        return jsonify(erreur="Fichier source introuvable"), 404

    jeton = uuid.uuid4().hex
    chemin_stage = os.path.join(STAGING_DIR, f"{jeton}.csv")
    os.rename(chemin_source, chemin_stage)

    avec_entete = str(donnees.get("avec_entete", "true")).lower() != "false"
    return _analyser_fichier_stage(jeton, chemin_stage, avec_entete)


def _analyser_fichier_stage(jeton, chemin_stage, avec_entete):
    taille_max_mo = int(lire_parametre("taille_max_csv_mo", "2048"))
    if os.path.getsize(chemin_stage) > taille_max_mo * 1024 * 1024:
        os.remove(chemin_stage)
        return jsonify(erreur=f"Fichier trop volumineux (> {taille_max_mo} Mo)"), 413

    with open(chemin_stage, "rb") as f:
        echantillon_brut = f.read(1_000_000)
    encodage = detecter_encodage(echantillon_brut)
    delimiteur = detecter_delimiteur(echantillon_brut.decode(encodage, errors="replace")[:10_000])

    # Un seul passage en flux : compte le nombre réel de lignes tout en
    # conservant seulement les 50 premières pour l'aperçu, sans jamais
    # matérialiser le fichier entier en mémoire.
    entetes = None
    echantillon = []
    nb_lignes = 0
    with open(chemin_stage, "r", encoding=encodage, newline="", errors="replace") as f:
        lecteur = csv.reader(f, delimiter=delimiteur)
        if avec_entete:
            entetes = next(lecteur, None)
        for ligne in lecteur:
            if entetes is None:
                entetes = [f"colonne_{i+1}" for i in range(len(ligne))]
            nb_lignes += 1
            if len(echantillon) < 50:
                echantillon.append(ligne)

    if entetes is None:
        os.remove(chemin_stage)
        return jsonify(erreur="Fichier vide"), 400

    colonnes = []
    for i, nom in enumerate(entetes):
        valeurs_colonne = [ligne[i] for ligne in echantillon if i < len(ligne)]
        colonnes.append({
            "nom_source": nom,
            "nom_normalise": normaliser_identifiant(nom or f"colonne_{i+1}"),
            "type_suggere": suggerer_type(valeurs_colonne),
        })

    return jsonify({
        "jeton": jeton,
        "encodage_detecte": encodage,
        "delimiteur_detecte": delimiteur,
        "avec_entete": avec_entete,
        "nb_lignes_totales": nb_lignes,
        "colonnes": colonnes,
        "apercu": echantillon,
    })


# =============================================================================
# ENDPOINT : VALIDATION D'IMPORT (§5.1, étapes 4 à 9 ; §7.4)
# =============================================================================
class FluxCSVNormalise:
    """Adapte le fichier source pour COPY, ligne à ligne, sans jamais le
    charger entier en mémoire (§12/§13) : lire un fichier de plusieurs
    centaines de Mo via un seul .read() (constaté avec un vrai jeu de
    données de test) contredit directement cette exigence. Convertit au
    passage la virgule décimale française ("468000,00") en notation à
    point attendue par PostgreSQL pour les colonnes Décimal : COPY ne fait
    aucune conversion de ce type lui-même et échouerait sinon sur un jeu
    de données français typique (ex. Valeurs Foncières / DGFiP)."""

    def __init__(self, chemin_fichier, encodage, delimiteur, colonnes, avec_entete=True, lignes_exclues=None):
        self._source = open(chemin_fichier, "r", encoding=encodage, newline="")
        self._delimiteur = delimiteur
        self._lecteur = csv.reader(self._source, delimiter=delimiteur)
        self._indices_decimaux = {i for i, c in enumerate(colonnes) if c["type"] == "Décimal"}
        self._tampon = io.StringIO()
        self._ecrivain = csv.writer(self._tampon, delimiter=delimiteur)
        self._epuise = False
        # La ligne d'en-tête, si elle existe, est transmise telle quelle -
        # c'est le HEADER de la commande COPY elle-même qui la traite côté
        # serveur (§5.1 étape 2) - mais ne doit jamais compter comme une
        # ligne de données pour l'exclusion ci-dessous, sous peine de
        # décaler tous les numéros de ligne d'un cran par rapport à
        # /import/verifier (qui ne compte, lui, que les lignes de données).
        self._entete_a_transmettre = avec_entete
        self._numero_ligne = 0
        self._lignes_exclues = lignes_exclues or set()

    def read(self, taille=65536):
        while self._tampon.tell() < taille and not self._epuise:
            try:
                ligne = next(self._lecteur)
            except StopIteration:
                self._epuise = True
                self._source.close()
                break
            if self._entete_a_transmettre:
                self._entete_a_transmettre = False
                self._ecrivain.writerow(ligne)
                continue
            self._numero_ligne += 1
            if self._numero_ligne in self._lignes_exclues:
                continue
            for i in self._indices_decimaux:
                if i < len(ligne) and ligne[i]:
                    ligne[i] = ligne[i].replace(",", ".")
            self._ecrivain.writerow(ligne)
        valeur = self._tampon.getvalue()
        self._tampon = io.StringIO()
        self._ecrivain = csv.writer(self._tampon, delimiter=self._delimiteur)
        return valeur


def rafraichir_taille_base(base_id, nom_pg):
    """Met à jour bases.taille_estimee_mo (§5.2, « Mes bases » : sa taille) -
    jamais tenu à jour ailleurs, sans quoi chaque base afficherait
    éternellement 0 Mo. pg_database_size() est un catalogue global : il se
    lit depuis la connexion au catalogue, sans avoir à se connecter à la
    base cible elle-même. Appelé après import et après suppression de
    table (les deux opérations qui font varier la taille physique) - pas
    après chaque écriture libre de l'onglet Travaux, dont le volume ne
    justifie pas ce coût à chaque requête (§7, profil analytique)."""
    with connexion_catalogue() as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_database_size(%s)", (nom_pg,))
        taille_octets = cur.fetchone()[0]
        cur.execute("SELECT public.maj_taille_base(%s, %s)", (base_id, taille_octets / (1024 * 1024)))
        conn.commit()


def consigner_audit(claims, action, cible, details):
    """Journalise une création/suppression de table (§8.12, §5.2) : ces
    opérations ont lieu dans la base physique de l'agent, jamais dans
    sillon_catalog, donc aucun trigger de table (contrairement à
    utilisateurs/bases/partages) ne peut les capturer automatiquement.
    L'identité de l'auteur est dérivée par consigner_audit() lui-même à
    partir de "request.jwt.claims" (posé par le SET ROLE ci-dessous) plutôt
    que passée en paramètre texte, pour ne jamais dépendre d'une valeur que
    l'appelant pourrait falsifier - la valeur probante du journal (§8.12)
    en dépend."""
    with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
        cur.execute("SELECT public.consigner_audit(%s, %s, %s)", (action, cible, details))
        conn.commit()


def table_existe(conn, nom_table):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = %s AND c.relkind = 'r'",
            (nom_table,),
        )
        return cur.fetchone() is not None


def creer_table_et_charger(conn, nom_table, colonnes, chemin_fichier, encodage, delimiteur, valeur_manquante, remplacer=False, avec_entete=True, lignes_exclues=None):
    with conn.cursor() as cur:
        # 0. suggerer_type() reconnaît le format "%d/%m/%Y" (jour/mois/année,
        #    usuel dans les exports administratifs français) : sans ce
        #    réglage, le style par défaut de PostgreSQL (MDY) rejette toute
        #    date où le jour dépasse 12, ex. "13/01/2025" - constaté en
        #    pratique sur le jeu de données DVF.
        cur.execute("SET datestyle = 'ISO, DMY'")

        # 0bis. Remplacement explicite (§5.1, gestion de collision) : la
        # détection de la collision elle-même a déjà eu lieu avant l'appel
        # (valider_import), pour pouvoir la signaler au client avant tout
        # chargement - ce DROP n'est atteint que si l'utilisateur a
        # confirmé vouloir remplacer le contenu existant.
        if remplacer:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(nom_table)))

        # 1. Table + clé primaire technique (§7.4).
        colonnes_sql = [sql.SQL("id BIGSERIAL PRIMARY KEY")]
        for c in colonnes:
            colonnes_sql.append(
                sql.SQL("{} {}").format(sql.Identifier(c["nom_normalise"]), sql.SQL(TYPES_SQL[c["type"]]))
            )
        cur.execute(sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(nom_table), sql.SQL(", ").join(colonnes_sql)
        ))

        # 2. Chargement en masse SANS index intermédiaire (§7.4), en flux
        #    (§13), avec normalisation des décimaux à la volée. HEADER
        #    reflète avec_entete (§5.1, étape 2) : sans ligne d'en-tête, la
        #    première ligne du fichier est une ligne de données comme les
        #    autres, à charger elle aussi.
        entete_sql = sql.SQL("true" if avec_entete else "false")
        noms_colonnes = sql.SQL(", ").join(sql.Identifier(c["nom_normalise"]) for c in colonnes)
        requete_copy = sql.SQL(
            "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER {}, NULL {}, ENCODING 'UTF8')"
        ).format(sql.Identifier(nom_table), noms_colonnes, entete_sql, sql.Literal(valeur_manquante))
        if delimiteur != ",":
            # copy_expert n'accepte pas de DELIMITER autre que le format CSV
            # standard sans le préciser explicitement ; on le fait ici.
            requete_copy = sql.SQL(
                "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER {}, DELIMITER {}, NULL {}, ENCODING 'UTF8')"
            ).format(sql.Identifier(nom_table), noms_colonnes, entete_sql, sql.Literal(delimiteur), sql.Literal(valeur_manquante))

        flux = FluxCSVNormalise(chemin_fichier, encodage, delimiteur, colonnes, avec_entete, lignes_exclues)
        cur.copy_expert(requete_copy.as_string(conn), flux)
        nb_lignes_chargees = cur.rowcount

        # 3. Index proposés selon le type (§7.4) - créés après coup.
        for c in colonnes:
            if c["type"] in ("Date", "Date/Heure"):
                cur.execute(sql.SQL("CREATE INDEX ON {} ({})").format(
                    sql.Identifier(nom_table), sql.Identifier(c["nom_normalise"])
                ))
            elif c["type"] == "Texte":
                cur.execute(sql.SQL("CREATE INDEX ON {} USING gin ({} gin_trgm_ops)").format(
                    sql.Identifier(nom_table), sql.Identifier(c["nom_normalise"])
                ))

        # 4. Statistiques de planification (§7.4).
        cur.execute(sql.SQL("ANALYZE {}").format(sql.Identifier(nom_table)))

        # 5. Date et taille du dernier import (§5.2, fiche d'une table) :
        # public._sillon_imports est créée pour chaque base au moment de sa
        # création (cf. _traiter_job, branche "creation_base") - jamais ici,
        # pour ne pas exiger de privilège CREATE supplémentaire d'un
        # bénéficiaire de partage qui importerait dans une base qui n'est
        # pas la sienne (cas exclu en pratique par les GRANT du §5.2, mais
        # cette fonction ne doit pas en dépendre pour rester correcte).
        cur.execute(
            """
            INSERT INTO public._sillon_imports (nom_table, nb_lignes, taille_octets)
            VALUES (%s, %s, pg_total_relation_size(%s))
            ON CONFLICT (nom_table) DO UPDATE SET
                date_import = now(), nb_lignes = EXCLUDED.nb_lignes, taille_octets = EXCLUDED.taille_octets
            """,
            (nom_table, nb_lignes_chargees, nom_table),
        )

    conn.commit()
    return nb_lignes_chargees


@app.route("/import/valider", methods=["POST"])
def valider_import():
    donnees = request.get_json(force=True)
    jeton = donnees.get("jeton")
    base_id = donnees.get("base_id")
    nom_table = normaliser_identifiant(donnees.get("nom_table") or "")
    colonnes = donnees.get("colonnes") or []
    encodage = donnees.get("encodage") or "utf-8"
    delimiteur = donnees.get("delimiteur") or ";"
    valeur_manquante = donnees.get("valeur_manquante") or ""
    avec_entete = bool(donnees.get("avec_entete", True))
    # Lignes écartées après confirmation explicite du contrôle de cohérence
    # (§5.1 étape 4) : numérotées comme /import/verifier, 1-based sur les
    # seules lignes de données.
    lignes_exclues = set(donnees.get("exclure_lignes") or [])

    chemin_fichier = os.path.join(STAGING_DIR, f"{jeton}.csv")
    if not jeton or not os.path.isfile(chemin_fichier):
        return jsonify(erreur="Fichier en attente introuvable ou expiré"), 404
    for c in colonnes:
        if c.get("type") not in TYPES_SQL:
            return jsonify(erreur=f"Type de colonne invalide : {c.get('type')}"), 400

    claims = g.claims

    # Base personnelle inexistante : créée via la file d'attente (§4.4),
    # avec une courte attente active puisqu'une base neuve est rapide à
    # créer - cf. note de conception en fin de fichier.
    if not base_id:
        try:
            with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
                cur.execute("SELECT public.creer_job('creation_base', NULL, '{}'::jsonb)")
                id_job = cur.fetchone()[0]
                conn.commit()
        except psycopg2.Error:
            # Profil sans droit d'import (§3, lecteur) : creer_job refuse
            # l'appel côté PostgreSQL (droit_refuse) - message clair plutôt
            # que de laisser remonter une erreur SQL brute en 500.
            return jsonify(erreur="Votre profil n'autorise pas l'import de fichiers CSV"), 403

        base_id = _attendre_job_termine(id_job, timeout_s=15)
        if base_id is None:
            return jsonify(erreur="Création de la base non aboutie, réessayez"), 202

    nom_pg = base_accessible(claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    # Collision de nom de table (§5.1, étape 6) : vérifiée avant tout
    # chargement, pas seulement laissée à un CREATE TABLE qui échouerait
    # avec une erreur Postgres brute - le fichier reste en attente (jeton
    # toujours valide) pour permettre à l'utilisateur de renommer ou de
    # confirmer explicitement le remplacement sans avoir à re-déposer.
    remplacer = bool(donnees.get("remplacer", False))
    if not remplacer:
        try:
            conn_verif = connexion_base(nom_pg, claims["role"])
            try:
                collision = table_existe(conn_verif, nom_table)
            finally:
                conn_verif.close()
        except psycopg2.Error as exc:
            return jsonify(erreur=str(exc)), 400
        if collision:
            return jsonify(statut="collision", table=nom_table), 409

    taille_octets = os.path.getsize(chemin_fichier)
    seuil_sync_mo = int(lire_parametre("seuil_import_synchrone_mo", "10"))

    if taille_octets <= seuil_sync_mo * 1024 * 1024:
        try:
            conn = connexion_base(nom_pg, claims["role"])
            try:
                nb_lignes = creer_table_et_charger(conn, nom_table, colonnes, chemin_fichier, encodage, delimiteur, valeur_manquante, remplacer, avec_entete, lignes_exclues)
            finally:
                conn.close()
        except psycopg2.Error as exc:
            # Import échoué (§5.1 étape 9, §8.12) : journalisé au même titre
            # qu'un import réussi, avec le motif plutôt qu'un nombre de
            # lignes puisqu'aucune n'a été retenue (COPY entièrement annulé
            # avec le reste de la transaction). Un échec de la journalisation
            # elle-même ne doit pas remplacer la réponse 400 attendue par un
            # 500 non lié à l'erreur d'import initiale.
            try:
                consigner_audit(claims, "ERREUR", nom_table, f"import échoué (base #{base_id}) : {exc}")
            except psycopg2.Error:
                pass
            return jsonify(erreur=str(exc)), 400
        finally:
            os.remove(chemin_fichier)
        rafraichir_taille_base(base_id, nom_pg)
        consigner_audit(claims, "CREATION", nom_table, f"table : CREATION (base #{base_id}), {nb_lignes} ligne(s) importée(s)")
        return jsonify(statut="termine", table=nom_table)

    # Fichier volumineux : traitement différé par le consommateur de jobs
    # (§5.1, étape 7 ; §9).
    try:
        with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT public.creer_job('import_csv', %s, %s::jsonb)",
                (base_id, psycopg2.extras.Json({
                    "chemin_fichier": chemin_fichier,
                    "nom_table": nom_table,
                    "colonnes": colonnes,
                    "encodage": encodage,
                    "delimiteur": delimiteur,
                    "valeur_manquante": valeur_manquante,
                    "role_pg": claims["role"],
                    "nom_pg": nom_pg,
                    "remplacer": remplacer,
                    "avec_entete": avec_entete,
                    "lignes_exclues": list(lignes_exclues),
                })),
            )
            id_job = cur.fetchone()[0]
            conn.commit()
    except psycopg2.Error:
        return jsonify(erreur="Votre profil n'autorise pas l'import de fichiers CSV"), 403

    return jsonify(statut="en_attente", id_job=id_job)


def _attendre_job_termine(id_job, timeout_s=15):
    """Attente active courte, réservée aux jobs dont la durée normale est
    de l'ordre de la seconde (création d'une base vide, §4.4)."""
    fin = time.monotonic() + timeout_s
    while time.monotonic() < fin:
        with connexion_catalogue() as conn, conn.cursor() as cur:
            cur.execute("SELECT statut, base_id FROM public.jobs WHERE id = %s", (id_job,))
            statut, base_id = cur.fetchone()
        if statut == "termine":
            return base_id
        if statut == "erreur":
            return None
        time.sleep(0.3)
    return None


# =============================================================================
# ENDPOINT : DEPOT DE SCRIPT (§5.4)
# =============================================================================
EXTENSIONS_SCRIPT = {".py": "script_python", ".R": "script_r", ".r": "script_r"}


@app.route("/scripts/deposer", methods=["POST"])
def deposer_script():
    fichier = request.files.get("fichier")
    base_id = request.form.get("base_id", type=int)
    if not fichier or not base_id:
        return jsonify(erreur="Fichier ou base manquant"), 400

    extension = os.path.splitext(fichier.filename or "")[1]
    type_job = EXTENSIONS_SCRIPT.get(extension)
    if not type_job:
        return jsonify(erreur="Extension non supportée : déposez un fichier .py ou .R"), 400

    # L'exécution de script est une autorisation distincte du simple accès
    # en lecture à une base partagée (§5.2) : exiger_script=True applique
    # cette règle en plus de la vérification d'accès habituelle.
    nom_pg = base_accessible(g.claims, base_id, exiger_script=True)
    if not nom_pg:
        return jsonify(erreur="Base introuvable, inaccessible, ou exécution de script non autorisée sur cette base"), 404

    contenu = fichier.read()
    taille_max_mo = int(lire_parametre("taille_max_script_mo", "10"))
    if len(contenu) > taille_max_mo * 1024 * 1024:
        return jsonify(erreur=f"Script trop volumineux (> {taille_max_mo} Mo)"), 413

    jeton = uuid.uuid4().hex
    chemin_script = os.path.join(STAGING_DIR, f"{jeton}{extension}")
    with open(chemin_script, "wb") as f:
        f.write(contenu)

    # Le job est systématiquement mis en file d'attente, quelle que soit sa
    # durée estimée (§5.4) : c'est sillon-worker, pas cet endpoint, qui le
    # traitera en lançant un conteneur isolé.
    with connexion_catalogue(claims=g.claims) as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT public.creer_job(%s, %s, %s::jsonb)",
                (type_job, base_id, psycopg2.extras.Json({
                    "chemin_script": chemin_script,
                    "nom_pg": nom_pg,
                    "role_pg": g.claims["role"],
                })),
            )
        except psycopg2.Error as exc:
            os.remove(chemin_script)
            return jsonify(erreur=str(exc)), 400
        id_job = cur.fetchone()[0]
        conn.commit()

    return jsonify(statut="en_attente", id_job=id_job)


# =============================================================================
# ENDPOINT : COMPLEMENT MULTI-BASE DU PARTAGE (§4.4, §5.2)
# =============================================================================
@app.route("/bases/<int:base_id>/partager", methods=["POST"])
def partager_base(base_id):
    donnees = request.get_json(force=True)
    email_beneficiaire = donnees.get("email")
    autorise_scripts = bool(donnees.get("autorise_scripts", False))
    claims = g.claims

    # Appel RPC avec le role personnel de l'appelant (verification de
    # propriete portee par partager_base lui-meme, §7 du schema).
    with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT public.partager_base(%s, %s, %s)",
                (base_id, email_beneficiaire, autorise_scripts),
            )
        except psycopg2.Error as exc:
            return jsonify(erreur=str(exc)), 400
        conn.commit()

    # Lectures internes avec l'identite propre de l'orchestrateur (§4.4) :
    # le role personnel de l'appelant n'a lui-meme aucun GRANT direct sur
    # les tables brutes bases/utilisateurs (§8.4), seulement sur les vues
    # filtrees et les fonctions dediees.
    with connexion_catalogue() as conn, conn.cursor() as cur:
        cur.execute("SELECT nom_pg FROM public.bases WHERE id = %s", (base_id,))
        nom_pg = cur.fetchone()[0]
        cur.execute("SELECT role_pg FROM public.utilisateurs WHERE email = %s", (email_beneficiaire,))
        role_beneficiaire = cur.fetchone()[0]

    # Complément nécessitant une connexion à la base cible elle-même
    # (§4.4) : GRANT USAGE/SELECT et privilèges par défaut pour les tables
    # futures (§5.2, réponse retenue lors du cahier des charges).
    try:
        conn_cible = connexion_base(nom_pg, claims["role"])
        try:
            with conn_cible.cursor() as cur:
                cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role_beneficiaire)))
                cur.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}").format(sql.Identifier(role_beneficiaire)))
                cur.execute(
                    sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public GRANT SELECT ON TABLES TO {}").format(
                        sql.Identifier(claims["role"]), sql.Identifier(role_beneficiaire)
                    )
                )
            conn_cible.commit()
        finally:
            conn_cible.close()
    except psycopg2.Error as exc:
        return jsonify(erreur=f"Partage enregistré mais application des droits incomplète : {exc}"), 500

    return jsonify(statut="ok")


@app.route("/bases/<int:base_id>/revoquer", methods=["POST"])
def revoquer_partage(base_id):
    donnees = request.get_json(force=True)
    email_beneficiaire = donnees.get("email")
    claims = g.claims

    with connexion_catalogue() as conn, conn.cursor() as cur:
        cur.execute("SELECT nom_pg FROM public.bases WHERE id = %s", (base_id,))
        ligne = cur.fetchone()
        nom_pg = ligne[0] if ligne else None
        cur.execute("SELECT role_pg FROM public.utilisateurs WHERE email = %s", (email_beneficiaire,))
        ligne2 = cur.fetchone()
        role_beneficiaire = ligne2[0] if ligne2 else None

    with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
        try:
            cur.execute("SELECT public.revoquer_partage(%s, %s)", (base_id, email_beneficiaire))
        except psycopg2.Error as exc:
            return jsonify(erreur=str(exc)), 400
        conn.commit()

    if nom_pg and role_beneficiaire:
        try:
            conn_cible = connexion_base(nom_pg, claims["role"])
            try:
                with conn_cible.cursor() as cur:
                    cur.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(sql.Identifier(role_beneficiaire)))
                    cur.execute(
                        sql.SQL("ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public REVOKE SELECT ON TABLES FROM {}").format(
                            sql.Identifier(claims["role"]), sql.Identifier(role_beneficiaire)
                        )
                    )
                conn_cible.commit()
            finally:
                conn_cible.close()
        except psycopg2.Error:
            pass  # le retrait du GRANT CONNECT (dans revoquer_partage) suffit deja a couper l'acces

    return jsonify(statut="ok")


# =============================================================================
# ENDPOINT : SCHEMA D'UNE BASE (§5.3 - auto-complétion de l'éditeur SQL)
# =============================================================================
@app.route("/bases/<int:base_id>/schema", methods=["GET"])
def schema_base(base_id):
    nom_pg = base_accessible(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    try:
        conn = connexion_base(nom_pg, g.claims["role"])
    except psycopg2.Error as exc:
        return jsonify(erreur=f"Connexion refusée : {exc}"), 403
    try:
        with conn.cursor() as cur:
            # information_schema.columns ne liste déjà que les colonnes sur
            # lesquelles l'appelant a un privilège (même filtrage implicite
            # que dans fiche_table, §5.2) : rien à ajouter pour respecter
            # l'isolation des bases (§8.4).
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name <> '_sillon_imports' "
                "ORDER BY table_name, ordinal_position"
            )
            lignes = cur.fetchall()
        conn.rollback()
    except psycopg2.Error as exc:
        return jsonify(erreur=str(exc)), 400
    finally:
        conn.close()

    tables = {}
    for nom_table, nom_colonne in lignes:
        tables.setdefault(nom_table, []).append(nom_colonne)
    return jsonify(tables)


# =============================================================================
# ENDPOINTS : TABLES D'UNE BASE (§5.2 - fiche d'une table, suppression)
# =============================================================================
# nb_lignes est estime via pg_class.reltuples (mis a jour par l'ANALYZE de fin
# d'import, §7.4) plutot que compte exactement : un COUNT(*) sur une table de
# plusieurs millions de lignes contredirait le profil de charge analytique
# vise par le reglage du moteur (§7). public._sillon_imports.nb_lignes, quand
# disponible, est exact puisqu'il vient du COPY qui a cree la table - dans ce
# cas prefere a l'estimation.
_REQUETE_TABLES = """
    SELECT c.relname,
           COALESCE(i.nb_lignes, GREATEST(c.reltuples, 0)::bigint) AS nb_lignes,
           pg_total_relation_size(c.oid) AS taille_octets,
           i.date_import
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN public._sillon_imports i ON i.nom_table = c.relname
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> '_sillon_imports'
      AND has_table_privilege(c.oid, 'SELECT')
"""


@app.route("/bases/<int:base_id>/tables", methods=["GET"])
def lister_tables(base_id):
    nom_pg = base_accessible(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    try:
        conn = connexion_base(nom_pg, g.claims["role"])
    except psycopg2.Error as exc:
        return jsonify(erreur=f"Connexion refusée : {exc}"), 403
    try:
        with conn.cursor() as cur:
            cur.execute(_REQUETE_TABLES + " ORDER BY c.relname")
            lignes = cur.fetchall()
        conn.rollback()
    except psycopg2.Error as exc:
        return jsonify(erreur=str(exc)), 400
    finally:
        conn.close()

    return jsonify([
        {"nom_table": nom, "nb_lignes": nb_lignes, "taille_octets": taille, "date_dernier_import": _serialiser(date_import)}
        for nom, nb_lignes, taille, date_import in lignes
    ])


@app.route("/bases/<int:base_id>/tables/<nom_table>", methods=["GET"])
def fiche_table(base_id, nom_table):
    nom_pg = base_accessible(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    try:
        conn = connexion_base(nom_pg, g.claims["role"])
    except psycopg2.Error as exc:
        return jsonify(erreur=f"Connexion refusée : {exc}"), 403
    try:
        with conn.cursor() as cur:
            cur.execute(_REQUETE_TABLES + " AND c.relname = %s", (nom_table,))
            ligne = cur.fetchone()
            if not ligne:
                return jsonify(erreur="Table introuvable ou inaccessible"), 404
            _, nb_lignes, taille_octets, date_import = ligne

            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
                (nom_table,),
            )
            colonnes = [{"nom": nom, "type": type_} for nom, type_ in cur.fetchall()]

            cur.execute(sql.SQL("SELECT * FROM {} LIMIT 20").format(sql.Identifier(nom_table)))
            entetes_apercu = [d.name for d in cur.description]
            lignes_apercu = [[_serialiser(v) for v in ligne] for ligne in cur.fetchall()]
        conn.rollback()
    except psycopg2.Error as exc:
        return jsonify(erreur=str(exc)), 400
    finally:
        conn.close()

    return jsonify({
        "nom_table": nom_table,
        "nb_lignes": nb_lignes,
        "taille_octets": taille_octets,
        "date_dernier_import": _serialiser(date_import),
        "colonnes": colonnes,
        "apercu_entetes": entetes_apercu,
        "apercu_lignes": lignes_apercu,
    })


@app.route("/bases/<int:base_id>/tables/<nom_table>", methods=["DELETE"])
def supprimer_table(base_id, nom_table):
    nom_pg = base_dont_je_suis_proprietaire(g.claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou vous n'en êtes pas propriétaire"), 404

    try:
        conn = connexion_base(nom_pg, g.claims["role"])
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP TABLE {}").format(sql.Identifier(nom_table)))
            cur.execute("DELETE FROM public._sillon_imports WHERE nom_table = %s", (nom_table,))
        conn.commit()
    except psycopg2.Error as exc:
        return jsonify(erreur=str(exc)), 400
    finally:
        conn.close()

    rafraichir_taille_base(base_id, nom_pg)
    consigner_audit(g.claims, "SUPPRESSION", nom_table, f"table : SUPPRESSION (base #{base_id})")
    return jsonify(statut="ok")


# =============================================================================
# ENDPOINT : SUPPRESSION D'UNE BASE (§5.2, §9)
# =============================================================================
@app.route("/bases/<int:base_id>/supprimer", methods=["POST"])
def supprimer_base(base_id):
    # Action irreversible (§5.2) : la confirmation renforcee (saisie du nom
    # de la base) est portee par l'interface, pas par cet endpoint - mais la
    # verification de propriete, elle, ne peut reposer que sur le serveur.
    if not base_dont_je_suis_proprietaire(g.claims, base_id):
        return jsonify(erreur="Base introuvable ou vous n'en êtes pas propriétaire"), 404

    with connexion_catalogue(claims=g.claims) as conn, conn.cursor() as cur:
        try:
            cur.execute("SELECT public.creer_job('suppression_base', %s, '{}'::jsonb)", (base_id,))
        except psycopg2.Error as exc:
            return jsonify(erreur=str(exc)), 400
        id_job = cur.fetchone()[0]
        conn.commit()

    return jsonify(statut="en_attente", id_job=id_job)


# =============================================================================
# ENDPOINT : TELECHARGEMENT DU RESULTAT D'UN JOB (§5.5, §8.10)
# =============================================================================
@app.route("/jobs/<int:id_job>/telecharger", methods=["GET"])
def telecharger_resultat(id_job):
    # vue_mes_jobs filtre déjà sur l'appelant courant (§8.4) : la
    # vérification d'appartenance est donc portée par cette même requête,
    # pas ajoutée après coup (§8.10 - jamais un accès basé sur le seul
    # fait de connaître l'identifiant du job).
    with connexion_catalogue(claims=g.claims) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT statut, chemin_resultat FROM public.vue_mes_jobs WHERE id = %s",
            (id_job,),
        )
        ligne = cur.fetchone()

    if not ligne:
        return jsonify(erreur="Job introuvable ou inaccessible"), 404
    statut, chemin_resultat = ligne
    if statut != "termine" or not chemin_resultat or not os.path.isfile(chemin_resultat):
        return jsonify(erreur="Aucun résultat disponible pour ce job"), 404

    return send_file(chemin_resultat, as_attachment=True, download_name=os.path.basename(chemin_resultat))


# =============================================================================
# ENDPOINT : JOURNAL D'UN SCRIPT EN COURS (§5.4, §5.5)
# =============================================================================
# journal.log vit dans RESULTATS_DIR/<id_job>/ (sillon-worker,
# executer_conteneur) tant que le job n'est pas terminé - une fois
# empaqueter_resultats() passé, il n'existe plus qu'à l'intérieur de
# l'archive zip renvoyée par /telecharger. Cet endpoint ne sert donc que
# la fenêtre "en_cours", ce que demande le §5.4 ("pas seulement disponibles
# une fois le job terminé").
TAILLE_JOURNAL_MAX = 100_000  # derniers octets renvoyés, pas le fichier entier (§13)


@app.route("/jobs/<int:id_job>/journal", methods=["GET"])
def journal_job(id_job):
    with connexion_catalogue(claims=g.claims) as conn, conn.cursor() as cur:
        cur.execute("SELECT statut FROM public.vue_mes_jobs WHERE id = %s", (id_job,))
        ligne = cur.fetchone()
    if not ligne:
        return jsonify(erreur="Job introuvable ou inaccessible"), 404
    statut = ligne[0]

    chemin_journal = os.path.join(RESULTATS_DIR, str(id_job), "journal.log")
    if not os.path.isfile(chemin_journal):
        return jsonify(statut=statut, journal="")

    taille = os.path.getsize(chemin_journal)
    with open(chemin_journal, "rb") as f:
        if taille > TAILLE_JOURNAL_MAX:
            f.seek(taille - TAILLE_JOURNAL_MAX)
        contenu = f.read().decode("utf-8", errors="replace")

    return jsonify(statut=statut, journal=contenu, tronque=taille > TAILLE_JOURNAL_MAX)


# =============================================================================
# ENDPOINTS : APERCU DES RESULTATS D'UN JOB (§5.4/§5.5)
# =============================================================================
# Certains types de résultats se consultent utilement sans télécharger
# l'archive complète : diagrammes Mermaid (texte .mmd - le bac à sable ne
# peut pas les rendre lui-même en image, aucun Node/Chromium dans
# sillon-image-execution, §8.7), images (graphiques matplotlib/ggplot2) et
# tableaux CSV. Rendu entièrement côté navigateur (mermaid.min.js
# vendorisé pour les diagrammes, une balise <img> pour les images, un
# tableau HTML construit par app.js pour les CSV) - ces deux endpoints ne
# font que donner accès, en lecture, au contenu déjà présent dans
# l'archive résultat.
TYPES_APERCU = {
    ".mmd": "mermaid", ".csv": "csv",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".svg": "image", ".gif": "image",
}
TAILLES_MAX_APERCU = {"mermaid": 200_000, "csv": 5_000_000, "image": 20_000_000}


def _job_resultat_accessible(id_job):
    """Même garantie d'appartenance que /telecharger (§8.10) : la
    vérification passe par vue_mes_jobs, jamais par le seul identifiant."""
    with connexion_catalogue(claims=g.claims) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT statut, chemin_resultat FROM public.vue_mes_jobs WHERE id = %s",
            (id_job,),
        )
        ligne = cur.fetchone()
    if not ligne:
        return None
    statut, chemin_resultat = ligne
    if statut != "termine" or not chemin_resultat or not os.path.isfile(chemin_resultat):
        return None
    return chemin_resultat


@app.route("/jobs/<int:id_job>/apercus", methods=["GET"])
def liste_apercus(id_job):
    chemin_resultat = _job_resultat_accessible(id_job)
    if not chemin_resultat:
        return jsonify(erreur="Aucun résultat disponible pour ce job"), 404

    apercus = []
    with zipfile.ZipFile(chemin_resultat) as archive:
        for info in archive.infolist():
            _racine, extension = os.path.splitext(info.filename)
            type_apercu = TYPES_APERCU.get(extension.lower())
            if not type_apercu or info.file_size > TAILLES_MAX_APERCU[type_apercu]:
                continue
            apercus.append({"nom": info.filename, "type": type_apercu})

    return jsonify(apercus=apercus)


@app.route("/jobs/<int:id_job>/apercu/<path:nom_fichier>", methods=["GET"])
def contenu_apercu(id_job, nom_fichier):
    chemin_resultat = _job_resultat_accessible(id_job)
    if not chemin_resultat:
        return jsonify(erreur="Aucun résultat disponible pour ce job"), 404

    _racine, extension = os.path.splitext(nom_fichier)
    type_apercu = TYPES_APERCU.get(extension.lower())
    if not type_apercu:
        return jsonify(erreur="Type de fichier non prévisualisable"), 400

    with zipfile.ZipFile(chemin_resultat) as archive:
        try:
            info = archive.getinfo(nom_fichier)
        except KeyError:
            return jsonify(erreur="Fichier introuvable dans le résultat"), 404
        if info.file_size > TAILLES_MAX_APERCU[type_apercu]:
            return jsonify(erreur="Fichier trop volumineux pour un aperçu"), 413
        contenu = archive.read(info)

    type_mime = mimetypes.guess_type(nom_fichier)[0] or "application/octet-stream"
    return Response(contenu, mimetype=type_mime)


# =============================================================================
# NOTIFICATIONS PAR MAIL (§9, §10)
# =============================================================================
def envoyer_notification(email_destinataire, sujet, corps):
    message = EmailMessage()
    message["Subject"] = sujet
    message["From"] = SMTP_EXPEDITEUR
    message["To"] = email_destinataire
    message.set_content(corps)
    try:
        with smtplib.SMTP(SMTP_HOTE, SMTP_PORT, timeout=10) as serveur:
            serveur.send_message(message)
    except OSError as exc:
        app.logger.warning("Échec d'envoi de la notification à %s : %s", email_destinataire, exc)


# =============================================================================
# CONSOMMATEUR ASYNCHRONE DE LA FILE D'ATTENTE (§9)
# =============================================================================
# Types de jobs traités par l'orchestrateur ; script_python/script_r sont du
# ressort exclusif de sillon-worker (isolation par conteneur, §8.7).
TYPES_GERES = ("creation_base", "suppression_base", "import_csv", "requete_sql")

# Reformulation du message technique (§5.5 : "un message technique (pour
# investigation) et un message utilisateur reformulé de façon
# compréhensible") - couvre les codes SQLSTATE rencontrés en pratique sur ce
# projet, pas l'ensemble du référentiel Postgres : le repli générique reste
# volontairement honnête plutôt que de prétendre reconnaître des cas non
# couverts.
_MESSAGES_PGCODE = {
    "57014": "Délai maximal dépassé : le traitement a été interrompu avant de se terminer.",
    "42501": "Vous n'avez pas les droits nécessaires pour cette opération.",
    "23505": "Une donnée en conflit avec une autre déjà existante a empêché l'opération.",
    "42P01": "Une table référencée par ce traitement est introuvable (a-t-elle été supprimée entre-temps ?).",
    "53100": "Espace disque insuffisant côté serveur pour terminer l'opération.",
    "53200": "Mémoire insuffisante côté serveur pour terminer l'opération.",
    "53300": "Trop de connexions simultanées côté serveur, réessayez plus tard.",
}
_MESSAGE_PGCODE_GENERIQUE = "Une erreur technique est survenue pendant le traitement ; voir le message technique pour le détail."


def reformuler_erreur(exc):
    pgcode = getattr(exc, "pgcode", None)
    return _MESSAGES_PGCODE.get(pgcode, _MESSAGE_PGCODE_GENERIQUE)


def _prochain_job(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, type, utilisateur_id, base_id, payload
            FROM public.jobs
            WHERE statut = 'en_attente' AND type = ANY(%s::public.type_job[])
            ORDER BY date_creation
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """,
            (list(TYPES_GERES),),
        )
        return cur.fetchone()


def _traiter_job(conn, id_job, type_job, utilisateur_id, base_id, payload):
    with conn.cursor() as cur:
        cur.execute("SELECT public.maj_statut_job(%s, 'en_cours')", (id_job,))
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT email, role_pg FROM public.utilisateurs WHERE id = %s", (utilisateur_id,))
        email_utilisateur, role_pg = cur.fetchone()

    try:
        debut = time.monotonic()  # utilisé par la branche "requete_sql", y compris dans le except ci-dessous
        if type_job == "creation_base":
            nom_base_pg = f"sillon_{role_pg}"

            # Idempotence (§5.1 : le sélecteur d'import propose "Ma base
            # personnelle (créée si nécessaire)") : ce job est redéclenché à
            # chaque import tant qu'aucune autre base n'est choisie
            # explicitement, y compris quand la base personnelle existe déjà
            # - un nouveau CREATE DATABASE échouerait alors systématiquement
            # ("la base ... existe déjà"), constaté en pratique. Le nom est
            # déterministe par rôle (sillon_<role_pg>) : une ligne déjà
            # présente dans le catalogue suffit à savoir qu'il n'y a rien à
            # (re)créer.
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM public.bases WHERE nom_pg = %s", (nom_base_pg,))
                ligne_existante = cur.fetchone()

            if ligne_existante:
                nouvelle_base_id = ligne_existante[0]
            else:
                conn_admin = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname="postgres", user=DB_USER, password=DB_PASSWORD)
                conn_admin.autocommit = True
                try:
                    with conn_admin.cursor() as cur:
                        cur.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                            sql.Identifier(nom_base_pg), sql.Identifier(role_pg)
                        ))
                finally:
                    conn_admin.close()

                # pg_trgm est nécessaire aux index de recherche approchée créés
                # à l'import (§7.4) ; il n'existe que dans le catalogue tant
                # qu'il n'est pas explicitement activé dans chaque nouvelle
                # base utilisateur.
                conn_neuve = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=nom_base_pg, user=DB_USER, password=DB_PASSWORD)
                conn_neuve.autocommit = True
                try:
                    with conn_neuve.cursor() as cur:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                        # Catalogue local de date/taille du dernier import par
                        # table (§5.2, fiche d'une table) : distinct du
                        # catalogue applicatif sillon_catalog, qui ne connaît
                        # que les bases, jamais leurs tables individuelles (§6).
                        # "SET ROLE" avant le CREATE TABLE (constaté en pratique
                        # sur la VM de test) : sillon_orchestrateur a bien le
                        # droit de créer la table sans bascule de rôle, en
                        # héritant des privilèges de role_pg dont il est membre
                        # (§4.4), mais l'objet créé appartiendrait alors à
                        # sillon_orchestrateur lui-même, pas à role_pg - le
                        # propriétaire d'une table est toujours le rôle courant
                        # au moment du CREATE, jamais un rôle dont les
                        # privilèges sont seulement hérités. Sans ce SET ROLE,
                        # creer_table_et_charger (exécuté avec le rôle personnel
                        # de l'agent, §4.4) se voit ensuite refuser l'INSERT.
                        cur.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role_pg)))
                        cur.execute("""
                            CREATE TABLE public._sillon_imports (
                                nom_table     TEXT PRIMARY KEY,
                                date_import   TIMESTAMPTZ NOT NULL DEFAULT now(),
                                nb_lignes     BIGINT NOT NULL,
                                taille_octets BIGINT NOT NULL
                            )
                        """)
                finally:
                    conn_neuve.close()

                with conn.cursor() as cur:
                    cur.execute("SELECT public.enregistrer_base(%s, %s)", (nom_base_pg, utilisateur_id))
                    nouvelle_base_id = cur.fetchone()[0]
                conn.commit()

            with conn.cursor() as cur:
                cur.execute("SELECT public.maj_statut_job(%s, 'termine')", (id_job,))
                cur.execute(
                    "UPDATE public.jobs SET base_id = %s WHERE id = %s",
                    (nouvelle_base_id, id_job),
                )
            conn.commit()

        elif type_job == "suppression_base":
            with conn.cursor() as cur:
                cur.execute("SELECT nom_pg FROM public.bases WHERE id = %s", (base_id,))
                nom_base_pg = cur.fetchone()[0]
                cur.execute("SELECT public.retirer_base(%s)", (base_id,))
            conn.commit()

            conn_admin = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname="postgres", user=DB_USER, password=DB_PASSWORD)
            conn_admin.autocommit = True
            try:
                with conn_admin.cursor() as cur:
                    cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(nom_base_pg)))
            finally:
                conn_admin.close()

            with conn.cursor() as cur:
                cur.execute("SELECT public.maj_statut_job(%s, 'termine')", (id_job,))
            conn.commit()

        elif type_job == "import_csv":
            conn_cible = connexion_base(payload["nom_pg"], payload["role_pg"])
            try:
                nb_lignes = creer_table_et_charger(
                    conn_cible, payload["nom_table"], payload["colonnes"],
                    payload["chemin_fichier"], payload["encodage"],
                    payload["delimiteur"], payload["valeur_manquante"],
                    payload.get("remplacer", False), payload.get("avec_entete", True),
                    set(payload.get("lignes_exclues") or []),
                )
            finally:
                conn_cible.close()
            if os.path.exists(payload["chemin_fichier"]):
                os.remove(payload["chemin_fichier"])
            rafraichir_taille_base(base_id, payload["nom_pg"])
            # Hors contexte HTTP ici (consommateur de fond, §9) : pas de
            # g.claims. role_pg/email_utilisateur, déjà résolus plus haut
            # pour ce job, suffisent à simuler les claims nécessaires à
            # consigner_audit() pour qu'il attribue l'entrée au bon agent.
            consigner_audit(
                {"role": role_pg, "email": email_utilisateur}, "CREATION",
                payload["nom_table"], f"table : CREATION (base #{base_id}), {nb_lignes} ligne(s) importée(s)",
            )

            with conn.cursor() as cur:
                cur.execute("SELECT public.maj_statut_job(%s, 'termine')", (id_job,))
            conn.commit()

        elif type_job == "requete_sql":
            lecture = est_requete_lecture(payload["requete"])
            delai_minutes = int(lire_parametre("duree_max_job_minutes", "30"))
            conn_cible = connexion_base(payload["nom_pg"], payload["role_pg"])
            try:
                with conn_cible.cursor() as cur:
                    cur.execute(sql.SQL("SET LOCAL statement_timeout = {}").format(sql.Literal(f"{delai_minutes}min")))
                    if lecture:
                        # Export complet en flux (§5.3 : même principe que
                        # /sql/export - jamais matérialiser le résultat
                        # entier en mémoire, §13), mais vers un fichier
                        # plutôt qu'un flux HTTP puisqu'il n'y a ici aucune
                        # requête HTTP à qui répondre en direct.
                        chemin_resultat = os.path.join(RESULTATS_DIR, f"{id_job}.csv")
                        requete_copy = sql.SQL(
                            "COPY ({}) TO STDOUT WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')"
                        ).format(sql.SQL(payload["requete"]))
                        with open(chemin_resultat, "wb") as f:
                            cur.copy_expert(requete_copy.as_string(conn_cible), f)
                        conn_cible.commit()
                        detail = "Résultat exporté en CSV, disponible au téléchargement."
                    else:
                        cur.execute(payload["requete"])
                        detail = f"{cur.rowcount} ligne(s) affectée(s)."
                        chemin_resultat = None
                        conn_cible.commit()
            finally:
                conn_cible.close()
            duree_ms = round((time.monotonic() - debut) * 1000)
            # user_id indispensable ici (contrairement à consigner_audit
            # ci-dessus, qui ne lit que l'email) : enregistrer_historique()
            # insère via _id_courant(), qui a besoin de "user_id" dans les
            # claims pour ne pas violer la contrainte NOT NULL de
            # requetes_historique.utilisateur_id - constaté en pratique.
            enregistrer_historique(
                {"role": payload["role_pg"], "email": email_utilisateur, "user_id": utilisateur_id},
                base_id, payload["requete"], "lecture" if lecture else "ecriture", True, duree_ms,
            )

            with conn.cursor() as cur:
                cur.execute("SELECT public.maj_statut_job(%s, 'termine', %s, %s)", (id_job, chemin_resultat, detail))
            conn.commit()

        if email_utilisateur:
            envoyer_notification(
                email_utilisateur,
                "[SILLON] Traitement terminé",
                f"Votre traitement ({type_job}) est terminé.\n"
                f"Consultez le résultat : {URL_APPLICATION}/#/suivi\n",
            )

    except Exception as exc:  # noqa: BLE001 - un job en erreur ne doit jamais faire tomber le consommateur
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT public.maj_statut_job(%s, 'erreur', NULL, %s, %s)",
                (id_job, str(exc), reformuler_erreur(exc)),
            )
        conn.commit()
        if type_job == "import_csv":
            # Import différé échoué (§5.1 étape 9, §8.12) : symétrique à la
            # journalisation du chemin synchrone dans valider_import().
            # try/except dédié : cette branche est déjà le gestionnaire
            # d'erreur du job (cf. note ci-dessus) - un échec de la
            # journalisation elle-même ne doit pas se propager plus loin.
            try:
                consigner_audit(
                    {"role": role_pg, "email": email_utilisateur}, "ERREUR",
                    payload.get("nom_table"), f"import échoué (base #{base_id}) : {exc}",
                )
            except psycopg2.Error:
                pass
        elif type_job == "requete_sql":
            # enregistrer_historique() a déjà sa propre protection interne
            # (cf. sa docstring) : pas besoin d'un try/except supplémentaire
            # ici, contrairement à consigner_audit() ci-dessus.
            enregistrer_historique(
                {"role": payload.get("role_pg"), "email": email_utilisateur, "user_id": utilisateur_id},
                base_id, payload.get("requete"),
                "lecture" if est_requete_lecture(payload.get("requete") or "") else "ecriture",
                False, round((time.monotonic() - debut) * 1000), str(exc),
            )
        if email_utilisateur:
            envoyer_notification(
                email_utilisateur,
                "[SILLON] Échec du traitement",
                f"Votre traitement ({type_job}) a échoué : {exc}\n",
            )


def ecouter_jobs():
    """Boucle de fond : un job non traité au réveil précédent (redémarrage
    du service, par exemple) est repris au sondage périodique - le LISTEN
    ne fait qu'accélérer la prise en charge, il n'est jamais la seule
    garantie de traitement (§9)."""
    while True:
        try:
            conn = connexion_catalogue()
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("LISTEN sillon_jobs;")

            while True:
                conn.poll()
                while conn.notifies:
                    conn.notifies.pop()

                conn.autocommit = False
                job = _prochain_job(conn)
                if job:
                    _traiter_job(conn, *job)
                else:
                    conn.rollback()
                conn.autocommit = True

                time.sleep(2)  # sondage de repli, cf. docstring
        except psycopg2.Error as exc:
            app.logger.warning("Connexion à la file d'attente perdue, nouvelle tentative : %s", exc)
            time.sleep(5)


# Démarré une fois par worker Gunicorn au chargement du module (§9) :
# volontairement pas dans un bloc "if __name__" puisque Gunicorn importe le
# module sans l'exécuter comme script.
threading.Thread(target=ecouter_jobs, daemon=True).start()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)


# =============================================================================
# NOTES DE CONCEPTION POUR LA SUITE
# =============================================================================
# - Packaging : le postinst de sillon-server devrait créer
#   /var/lib/sillon/staging (chown www-data), pour que le repli sur /tmp
#   ci-dessus ne soit plus nécessaire en production.
# - Le paramètre "seuil_import_synchrone_mo" est nouveau par rapport au
#   schema.sql déjà déployé : à ajouter à la table parametres (§11) avant
#   la mise en production, faute de quoi lire_parametre() retombera sur sa
#   valeur par défaut (10 Mo) sans erreur.
# - public._sillon_imports (§5.2, fiche d'une table) est créée par
#   _traiter_job à la création de chaque nouvelle base : les bases déjà
#   présentes sur la VM de test (créées avant l'ajout de cette table) n'en
#   disposent pas encore et feront échouer /bases/<id>/tables avec "relation
#   _sillon_imports does not exist" tant qu'elles ne sont pas recréées.
