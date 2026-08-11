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
import os
import queue
import re
import smtplib
import threading
import time
import unicodedata
import uuid
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


# =============================================================================
# ENDPOINT : REQUETES SQL LIBRES (§5.3, §8.8)
# =============================================================================
LIGNES_MAX_APERCU = 1000


def _serialiser(valeur):
    if isinstance(valeur, (datetime, date)):
        return valeur.isoformat()
    return valeur


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
        return jsonify(resultat)
    except psycopg2.Error as exc:
        conn.rollback()
        return jsonify(erreur=str(exc)), 400
    finally:
        conn.close()


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
        for i, ligne in enumerate(csv.reader(f, delimiter=delimiteur)):
            if i == 0:
                entetes = ligne
                continue
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

    def __init__(self, chemin_fichier, encodage, delimiteur, colonnes):
        self._source = open(chemin_fichier, "r", encoding=encodage, newline="")
        self._delimiteur = delimiteur
        self._lecteur = csv.reader(self._source, delimiter=delimiteur)
        self._indices_decimaux = {i for i, c in enumerate(colonnes) if c["type"] == "Décimal"}
        self._tampon = io.StringIO()
        self._ecrivain = csv.writer(self._tampon, delimiter=delimiteur)
        self._epuise = False

    def read(self, taille=65536):
        while self._tampon.tell() < taille and not self._epuise:
            try:
                ligne = next(self._lecteur)
            except StopIteration:
                self._epuise = True
                self._source.close()
                break
            for i in self._indices_decimaux:
                if i < len(ligne) and ligne[i]:
                    ligne[i] = ligne[i].replace(",", ".")
            self._ecrivain.writerow(ligne)
        valeur = self._tampon.getvalue()
        self._tampon = io.StringIO()
        self._ecrivain = csv.writer(self._tampon, delimiter=self._delimiteur)
        return valeur


def creer_table_et_charger(conn, nom_table, colonnes, chemin_fichier, encodage, delimiteur, valeur_manquante):
    with conn.cursor() as cur:
        # 0. suggerer_type() reconnaît le format "%d/%m/%Y" (jour/mois/année,
        #    usuel dans les exports administratifs français) : sans ce
        #    réglage, le style par défaut de PostgreSQL (MDY) rejette toute
        #    date où le jour dépasse 12, ex. "13/01/2025" - constaté en
        #    pratique sur le jeu de données DVF.
        cur.execute("SET datestyle = 'ISO, DMY'")

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
        #    (§13), avec normalisation des décimaux à la volée.
        noms_colonnes = sql.SQL(", ").join(sql.Identifier(c["nom_normalise"]) for c in colonnes)
        requete_copy = sql.SQL(
            "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL {}, ENCODING 'UTF8')"
        ).format(sql.Identifier(nom_table), noms_colonnes, sql.Literal(valeur_manquante))
        if delimiteur != ",":
            # copy_expert n'accepte pas de DELIMITER autre que le format CSV
            # standard sans le préciser explicitement ; on le fait ici.
            requete_copy = sql.SQL(
                "COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER {}, NULL {}, ENCODING 'UTF8')"
            ).format(sql.Identifier(nom_table), noms_colonnes, sql.Literal(delimiteur), sql.Literal(valeur_manquante))

        flux = FluxCSVNormalise(chemin_fichier, encodage, delimiteur, colonnes)
        cur.copy_expert(requete_copy.as_string(conn), flux)

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

    conn.commit()


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
        with connexion_catalogue(claims=claims) as conn, conn.cursor() as cur:
            cur.execute("SELECT public.creer_job('creation_base', NULL, '{}'::jsonb)")
            id_job = cur.fetchone()[0]
            conn.commit()

        base_id = _attendre_job_termine(id_job, timeout_s=15)
        if base_id is None:
            return jsonify(erreur="Création de la base non aboutie, réessayez"), 202

    nom_pg = base_accessible(claims, base_id)
    if not nom_pg:
        return jsonify(erreur="Base introuvable ou inaccessible"), 404

    taille_octets = os.path.getsize(chemin_fichier)
    seuil_sync_mo = int(lire_parametre("seuil_import_synchrone_mo", "10"))

    if taille_octets <= seuil_sync_mo * 1024 * 1024:
        try:
            conn = connexion_base(nom_pg, claims["role"])
            try:
                creer_table_et_charger(conn, nom_table, colonnes, chemin_fichier, encodage, delimiteur, valeur_manquante)
            finally:
                conn.close()
        except psycopg2.Error as exc:
            return jsonify(erreur=str(exc)), 400
        finally:
            os.remove(chemin_fichier)
        return jsonify(statut="termine", table=nom_table)

    # Fichier volumineux : traitement différé par le consommateur de jobs
    # (§5.1, étape 7 ; §9).
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
            })),
        )
        id_job = cur.fetchone()[0]
        conn.commit()

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
TYPES_GERES = ("creation_base", "suppression_base", "import_csv")


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
        if type_job == "creation_base":
            nom_base_pg = f"sillon_{role_pg}"
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
            finally:
                conn_neuve.close()

            with conn.cursor() as cur:
                cur.execute("SELECT public.enregistrer_base(%s, %s)", (nom_base_pg, utilisateur_id))
                nouvelle_base_id = cur.fetchone()[0]
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
                creer_table_et_charger(
                    conn_cible, payload["nom_table"], payload["colonnes"],
                    payload["chemin_fichier"], payload["encodage"],
                    payload["delimiteur"], payload["valeur_manquante"],
                )
            finally:
                conn_cible.close()
            if os.path.exists(payload["chemin_fichier"]):
                os.remove(payload["chemin_fichier"])

            with conn.cursor() as cur:
                cur.execute("SELECT public.maj_statut_job(%s, 'termine')", (id_job,))
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
            cur.execute("SELECT public.maj_statut_job(%s, 'erreur', NULL, %s)", (id_job, str(exc)))
        conn.commit()
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
