#!/usr/bin/env python3
"""SILLON - Téléchargement et import du jeu de données SIRENE (paquet sillon-demo-sirene).

Appelé par le postinst de sillon-demo-sirene, sur le même principe que
peupler_tutoriel.py (sillon-tutoriel) : jeton JWT du compte demo fourni
directement par le postinst (auth.sign_jwt(), jamais de mot de passe), et
import réalisé via la vraie API HTTP (/orchestrateur/import/...), pas un
COPY direct en base - le but est aussi de faire passer un jeu de données
massif par le chemin réellement emprunté par un utilisateur.

Ce paquet est la seule dérogation du projet à "aucun accès réseau sur la
cible en dehors du proxy Debian" (cf. cahier des charges §12.1) : le
fichier Sirene StockEtablissement (INSEE, ~43,9 millions de lignes, environ
2,86 Go compressé) est bien trop volumineux pour être vendorisé dans le
dépôt (même via Git LFS - déjà ~400 Mo utilisés pour l'image d'exécution).
Comme sillon-tutoriel, ce paquet n'est donc jamais installé en production
(cf. §12.7-bis du cahier des charges) : uniquement sur une VM de
démonstration ou de test disposant d'un accès Internet réel.
"""
import argparse
import csv
import http.client
import io
import json
import mimetypes
import os
import shutil
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(ICI, "scripts")

# Identifiant stable du jeu de données sur data.gouv.fr (son slug/URL
# publique change de forme au fil des refontes du site, l'identifiant
# interne non). Résolu à l'installation plutôt que de figer une URL de
# ressource datée (le fichier est republié chaque mois à une nouvelle
# adresse - une URL codée en dur serait périmée dès le mois suivant).
ID_JEU_DE_DONNEES = "5b7ffc618b4c4169d30727e0"
URL_API_DATAGOUV = f"https://www.data.gouv.fr/api/1/datasets/{ID_JEU_DE_DONNEES}/"

NOM_TABLE = "sirene_etablissements"

# Sous-ensemble des 54 colonnes du fichier source (§ liste-csv-des-
# variables-du-dessin-du-fichier-stocketablissement-311.csv) : celles
# utiles à une démonstration statistique/cartographique, pas une copie
# intégrale (adresses complémentaires, coordonnées Lambert, enseignes
# secondaires... hors sujet ici et alourdissent l'import pour rien).
# "dep_code" n'existe pas dans le fichier source : calculée ci-dessous à
# partir de codeCommuneEtablissement, sur le même principe que
# communes_france.dep_code (sillon-tutoriel) pour rester croisable avec
# ce jeu de données existant (jointure possible entre les deux paquets).
#
# Volontairement réduit par rapport à un premier essai qui incluait aussi
# code_postal, libelleCommuneEtablissement, codeCommuneEtablissement (gardé
# uniquement pour calculer dep_code, jamais persisté tel quel), enseigne1 et
# denomination : aucun des scripts de démonstration de ce paquet ne les
# utilise, et chaque colonne Texte supplémentaire ajoute un index GIN
# trigram (§7.4) coûteux en espace disque à la construction - constaté en
# pratique, l'import échouait avec "espace disque insuffisant" sur une VM
# de test à 18 Go avec le jeu de colonnes complet.
COLONNES_SOURCE = [
    "siren", "siret", "dateCreationEtablissement", "trancheEffectifsEtablissement",
    "etablissementSiege", "codeCommuneEtablissement", "etatAdministratifEtablissement",
    "activitePrincipaleEtablissement", "caractereEmployeurEtablissement",
]
COLONNES_SORTIE = [
    "siren", "siret", "date_creation", "tranche_effectifs", "etablissement_siege",
    "dep_code", "etat_administratif", "activite_principale", "caractere_employeur",
]

# Mêmes deux angles morts que sillon-tutoriel (TYPES_FORCES,
# peupler_tutoriel.py) : suggerer_type() n'échantillonne que les 50
# premières lignes de l'aperçu, jamais le fichier entier - un identifiant
# ou un code à zéros de tête (siren, siret, dep_code) doit donc toujours
# être forcé en Texte, jamais laissé à la détection automatique.
TYPES_FORCES = {
    "siren": "Texte", "siret": "Texte", "tranche_effectifs": "Texte",
    "dep_code": "Texte", "activite_principale": "Texte",
    "etat_administratif": "Texte", "caractere_employeur": "Texte",
    "etablissement_siege": "Booléen", "date_creation": "Date",
}

SCRIPTS_EXEMPLE_PYTHON = [
    "graphiques_couverture.py", "tableau_pandas.py", "export_excel.py", "rapport_pdf_multipages.py",
    "diagramme_mermaid.py", "carte_choroplethe.py",
]
SCRIPTS_EXEMPLE_R = ["graphiques_ggplot.R", "analyse_dplyr.R", "diagramme_mermaid.R"]


def calculer_dep_code(code_commune):
    """Reproduit la convention INSEE déjà utilisée par communes_france.dep_code
    (sillon-tutoriel) : Corse sur les 2 premiers caractères (2A/2B), outre-mer
    sur 3 (97x/98x), métropole sur 2 - pour rester croisable entre les deux
    jeux de données."""
    if not code_commune or len(code_commune) < 2:
        return ""
    prefixe2 = code_commune[:2]
    if prefixe2 in ("2A", "2B"):
        return prefixe2
    if prefixe2 in ("97", "98") and len(code_commune) >= 3:
        return code_commune[:3]
    return prefixe2


# =============================================================================
# 1. RESOLUTION DE L'URL DE LA RESSOURCE COURANTE
# =============================================================================
def resoudre_ressource_stock_etablissement():
    with urllib.request.urlopen(URL_API_DATAGOUV, timeout=30) as reponse:
        jeu = json.loads(reponse.read())

    for ressource in jeu.get("resources", []):
        titre = ressource.get("title", "")
        # "StockEtablissement -" (avec l'espace-tiret) exclut à la fois
        # "StockEtablissementHistorique" et "StockEtablissementLiensSuccession"
        # (préfixe différent après "StockEtablissement") ; l'exclusion
        # explicite du parquet retire la variante non-CSV du même titre.
        if titre.startswith("Sirene : Fichier StockEtablissement -") and "parquet" not in titre.lower():
            return ressource["url"], ressource.get("filesize")

    raise RuntimeError("Ressource StockEtablissement introuvable dans le jeu de données data.gouv.fr")


# =============================================================================
# 2. TELECHARGEMENT EN FLUX (fichier de plusieurs Go, jamais chargé entier
#    en mémoire - même exigence que le reste de SILLON, cf. FluxCSVNormalise
#    dans orchestrateur.py)
# =============================================================================
def telecharger(url, chemin_cible, taille_attendue):
    print(f"Téléchargement de {url} ({(taille_attendue or 0) / 1e9:.2f} Go attendus)...")
    with urllib.request.urlopen(url, timeout=60) as reponse, open(chemin_cible, "wb") as sortie:
        recu = 0
        dernier_affichage = 0
        while True:
            bloc = reponse.read(1024 * 1024)
            if not bloc:
                break
            sortie.write(bloc)
            recu += len(bloc)
            if recu - dernier_affichage >= 200_000_000:
                print(f"  {recu / 1e9:.2f} Go téléchargés...")
                dernier_affichage = recu
    print(f"Téléchargement terminé : {os.path.getsize(chemin_cible) / 1e9:.2f} Go.")


# =============================================================================
# 3. EXTRACTION + REDUCTION EN FLUX (jamais le fichier CSV source, ~10 Go,
#    chargé entier en mémoire non plus - zipfile.ZipFile.open() permet de
#    lire un membre de l'archive en flux, comme un fichier normal)
# =============================================================================
def extraire_et_reduire(chemin_zip, chemin_csv_sortie):
    print("Extraction et réduction aux colonnes utiles (lecture en flux)...")
    with zipfile.ZipFile(chemin_zip) as archive:
        noms_csv = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(noms_csv) != 1:
            raise RuntimeError(f"Archive inattendue, {len(noms_csv)} fichier(s) CSV au lieu de 1 : {noms_csv}")
        with archive.open(noms_csv[0]) as source_brute:
            source = io.TextIOWrapper(source_brute, encoding="utf-8", newline="")
            lecteur = csv.DictReader(source)
            indices_manquants = [c for c in COLONNES_SOURCE if c not in lecteur.fieldnames]
            if indices_manquants:
                raise RuntimeError(f"Colonnes attendues absentes du fichier source : {indices_manquants}")

            with open(chemin_csv_sortie, "w", encoding="utf-8", newline="") as sortie:
                ecrivain = csv.writer(sortie)
                ecrivain.writerow(COLONNES_SORTIE)
                nb_lignes = 0
                for ligne in lecteur:
                    code_commune = ligne["codeCommuneEtablissement"]
                    ecrivain.writerow([
                        ligne["siren"], ligne["siret"], ligne["dateCreationEtablissement"],
                        ligne["trancheEffectifsEtablissement"], ligne["etablissementSiege"],
                        calculer_dep_code(code_commune),
                        ligne["etatAdministratifEtablissement"], ligne["activitePrincipaleEtablissement"],
                        ligne["caractereEmployeurEtablissement"],
                    ])
                    nb_lignes += 1
                    if nb_lignes % 5_000_000 == 0:
                        print(f"  {nb_lignes:,} lignes traitées...".replace(",", " "))
    taille_go = os.path.getsize(chemin_csv_sortie) / 1e9
    print(f"Réduction terminée : {nb_lignes:,} lignes, {taille_go:.2f} Go.".replace(",", " "))


# =============================================================================
# 4. CLIENT HTTP - IDENTIQUE A CELUI DE peupler_tutoriel.py POUR LE JSON,
#    MAIS AVEC UN ENVOI MULTIPART EN FLUX POUR LE FICHIER (peupler_tutoriel
#    charge le fichier entier en mémoire avant envoi - acceptable pour les
#    quelques Mo du tutoriel, exclu ici pour un fichier de plusieurs Go).
# =============================================================================
class ErreurHTTP(Exception):
    def __init__(self, status, corps):
        super().__init__(f"HTTP {status} : {corps}")


class Client:
    def __init__(self, url_base, jeton, contexte_ssl):
        analyse = urllib.parse.urlsplit(url_base)
        self.hote = analyse.hostname
        self.port = analyse.port or 443
        self.contexte_ssl = contexte_ssl
        self.jeton = jeton

    def _connexion(self, timeout=120):
        return http.client.HTTPSConnection(self.hote, self.port, timeout=timeout, context=self.contexte_ssl)

    def get_json(self, chemin):
        conn = self._connexion()
        try:
            conn.request("GET", chemin, headers={"Cookie": f"sillon_token={self.jeton}"})
            reponse = conn.getresponse()
            corps = reponse.read()
            if reponse.status >= 400:
                raise ErreurHTTP(reponse.status, corps.decode("utf-8", errors="replace"))
            return json.loads(corps)
        finally:
            conn.close()

    def post_json(self, chemin, objet):
        corps = json.dumps(objet).encode("utf-8")
        conn = self._connexion()
        try:
            conn.request("POST", chemin, body=corps, headers={
                "Cookie": f"sillon_token={self.jeton}", "Content-Type": "application/json",
            })
            reponse = conn.getresponse()
            corps_reponse = reponse.read()
            if reponse.status >= 400:
                raise ErreurHTTP(reponse.status, corps_reponse.decode("utf-8", errors="replace"))
            return json.loads(corps_reponse) if corps_reponse else None
        finally:
            conn.close()

def base_personnelle(client):
    bases = client.get_json("/api/vue_mes_bases?je_suis_proprietaire=eq.true")
    return bases[0] if bases else None


def table_deja_importee(client, base_id):
    """Idempotence de bout en bout (au même titre que --remplacer pour
    peupler_tutoriel.py) : une réinstallation ne doit jamais redéclencher un
    téléchargement + une extraction de plusieurs heures si la table est déjà
    en place - y compris quand le fichier réduit local a déjà été consommé
    par un essai précédent (renommé vers STAGING_DIR par /import/apercu_local,
    cf. apercu_local ci-dessus), constaté en pratique lors des tests de ce
    paquet."""
    if not base_id:
        return False
    resultat = client.post_json("/orchestrateur/sql", {
        "base_id": base_id, "requete": f"SELECT to_regclass('{NOM_TABLE}') IS NOT NULL AS existe",
    })
    return bool(resultat["lignes"][0][0])


def attendre_job(client, id_job, delai_max_s):
    fin = time.monotonic() + delai_max_s
    dernier_statut = None
    while time.monotonic() < fin:
        jobs = client.get_json(f"/api/vue_mes_jobs?id=eq.{id_job}")
        if jobs and jobs[0]["statut"] != dernier_statut:
            dernier_statut = jobs[0]["statut"]
            print(f"  job n°{id_job} : {dernier_statut}")
        if jobs and jobs[0]["statut"] in ("termine", "erreur"):
            return jobs[0]
        time.sleep(5)
    raise TimeoutError(f"Job {id_job} toujours en cours après {delai_max_s}s.")


def apercu_local(jeton, chemin_csv):
    """Dépôt local direct (§12.8) plutôt qu'un envoi multipart classique :
    ce script tourne déjà en root sur la même machine que l'orchestrateur,
    inutile de faire transiter un fichier de plusieurs Go par un tampon
    HTTP pour ensuite le recopier - un simple renommage sur le même disque
    suffit (orchestrateur.py /import/apercu_local, jamais exposé par
    Nginx). Appelé en direct sur le port local de l'orchestrateur plutôt
    que via Nginx : l'authentification par jeton reste exigée comme pour
    tout autre endpoint (before_request, §4.3) - seule la traduction
    cookie -> en-tête Authorization habituellement faite par Nginx doit
    être reproduite ici à la main, Nginx n'étant pas dans le chemin."""
    corps = json.dumps({"chemin": chemin_csv, "avec_entete": "true"}).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", 5000, timeout=1800)
    try:
        conn.request("POST", "/import/apercu_local", body=corps, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {jeton}",
        })
        reponse = conn.getresponse()
        corps_reponse = reponse.read()
        if reponse.status >= 400:
            raise ErreurHTTP(reponse.status, corps_reponse.decode("utf-8", errors="replace"))
        return json.loads(corps_reponse)
    finally:
        conn.close()


def importer_sirene(client, chemin_csv, base_id):
    print("Aperçu du fichier réduit auprès de l'orchestrateur (dépôt local direct)...")
    apercu = apercu_local(client.jeton, chemin_csv)
    colonnes = [
        {"nom_normalise": c["nom_normalise"], "type": TYPES_FORCES.get(c["nom_normalise"], c["type_suggere"])}
        for c in apercu["colonnes"]
    ]

    corps = {
        "jeton": apercu["jeton"], "nom_table": NOM_TABLE, "colonnes": colonnes,
        "encodage": apercu["encodage_detecte"], "delimiteur": apercu["delimiteur_detecte"],
        "avec_entete": True, "remplacer": True,
    }
    if base_id:
        corps["base_id"] = base_id

    print("Validation de l'import (file d'attente attendue, fichier volumineux)...")
    resultat = client.post_json("/orchestrateur/import/valider", corps)
    if resultat.get("statut") == "termine":
        print(f"  {NOM_TABLE} importée directement (import synchrone).")
        return

    id_job = resultat["id_job"]
    # Plusieurs dizaines de minutes possibles pour ~43,9 millions de lignes
    # selon la machine (COPY + construction d'index) : un délai de 4h reste
    # trois fois la limite déjà généreuse fixée pour ce paquet
    # (duree_max_job_minutes relevé par le postinst, cf. commentaire dédié).
    job = attendre_job(client, id_job, delai_max_s=4 * 3600)
    if job["statut"] != "termine":
        raise RuntimeError(f"Import échoué : {job.get('message_utilisateur') or job.get('message_erreur')}")
    print(f"  {NOM_TABLE} importée avec succès (job n°{id_job}).")


def deposer_scripts_exemple(client, base_id):
    print("Dépôt et exécution des scripts de démonstration...")
    for sous_dossier, noms in (("python", SCRIPTS_EXEMPLE_PYTHON), ("r", SCRIPTS_EXEMPLE_R)):
        for nom_fichier in noms:
            chemin = os.path.join(SCRIPTS, sous_dossier, nom_fichier)
            if not os.path.isfile(chemin):
                print(f"  AVERTISSEMENT : script introuvable, ignoré : {chemin}", file=sys.stderr)
                continue
            with open(chemin, "rb") as f:
                contenu = f.read()
            resultat = _deposer_petit_fichier(client, base_id, nom_fichier, contenu)
            id_job = resultat["id_job"]
            print(f"  {nom_fichier} (job n°{id_job})...")
            try:
                job = attendre_job(client, id_job, delai_max_s=600)
                print(f"    -> {job['statut']}")
            except TimeoutError as exc:
                print(f"  AVERTISSEMENT : {exc}", file=sys.stderr)


def _deposer_petit_fichier(client, base_id, nom_fichier, contenu):
    """Scripts de démonstration : quelques Ko, un envoi bufferisé classique
    suffit (contrairement au CSV Sirene, cf. apercu_local)."""
    frontiere = uuid.uuid4().hex
    type_mime = mimetypes.guess_type(nom_fichier)[0] or "text/plain"
    corps = (
        f'--{frontiere}\r\nContent-Disposition: form-data; name="base_id"\r\n\r\n{base_id}\r\n'
        f'--{frontiere}\r\nContent-Disposition: form-data; name="fichier"; filename="{nom_fichier}"\r\n'
        f"Content-Type: {type_mime}\r\n\r\n"
    ).encode("utf-8") + contenu + f"\r\n--{frontiere}--\r\n".encode("utf-8")
    conn = client._connexion()
    try:
        conn.request("POST", "/orchestrateur/scripts/deposer", body=corps, headers={
            "Cookie": f"sillon_token={client.jeton}", "Content-Type": f"multipart/form-data; boundary={frontiere}",
        })
        reponse = conn.getresponse()
        corps_reponse = reponse.read()
        if reponse.status >= 400:
            raise ErreurHTTP(reponse.status, corps_reponse.decode("utf-8", errors="replace"))
        return json.loads(corps_reponse)
    finally:
        conn.close()


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--url", default="https://localhost")
    analyseur.add_argument("--jeton", required=True, help="Jeton JWT du compte demo, signé côté PostgreSQL")
    analyseur.add_argument("--cacert", default=None)
    analyseur.add_argument("--repertoire-travail", default="/var/lib/sillon-demo-sirene")
    args = analyseur.parse_args()

    if args.cacert and os.path.isfile(args.cacert):
        contexte = ssl.create_default_context(cafile=args.cacert)
    else:
        contexte = ssl._create_unverified_context()

    client = Client(args.url, args.jeton, contexte)
    base = base_personnelle(client)
    base_id = base["id"] if base else None

    if table_deja_importee(client, base_id):
        print(f"Table {NOM_TABLE} déjà présente - import ignoré, dépôt des scripts de démonstration uniquement.")
        deposer_scripts_exemple(client, base_id)
        print("Préparation du jeu de données Sirene terminée.")
        return

    os.makedirs(args.repertoire_travail, exist_ok=True)
    # Groupe www-data avec droit d'écriture (0775) : /import/apercu_local
    # (orchestrateur.py, exécuté sous www-data) déplace le fichier réduit
    # hors de ce répertoire par un simple renommage - qui exige un droit
    # d'écriture sur le répertoire source, pas seulement sur le fichier.
    shutil.chown(args.repertoire_travail, group="www-data")
    os.chmod(args.repertoire_travail, 0o775)
    chemin_zip = os.path.join(args.repertoire_travail, "stock_etablissement.zip")
    chemin_csv = os.path.join(args.repertoire_travail, "sirene_reduit.csv")

    # Reprise sans refaire une étape déjà accomplie - deux cas concrets :
    # un précédent essai a échoué après le téléchargement/l'extraction
    # (constaté en pratique sur la VM de test, plusieurs heures à ne pas
    # perdre), ou l'administrateur a lui-même déposé l'archive à l'avance
    # dans ce répertoire (§7.2 du guide d'installation) - machine cible sans
    # accès Internet direct, ou simplement pour ne pas dépendre de la durée
    # du téléchargement au moment de l'installation du paquet.
    if os.path.isfile(chemin_csv):
        print(f"Fichier réduit déjà présent ({os.path.getsize(chemin_csv) / 1e9:.2f} Go) - reprise sans nouveau téléchargement.")
    else:
        if os.path.isfile(chemin_zip):
            print(f"Archive déjà présente ({os.path.getsize(chemin_zip) / 1e9:.2f} Go, déposée manuellement ou reprise d'un essai précédent) - pas de nouveau téléchargement.")
        else:
            url_ressource, taille_attendue = resoudre_ressource_stock_etablissement()
            telecharger(url_ressource, chemin_zip, taille_attendue)
        extraire_et_reduire(chemin_zip, chemin_csv)
        os.remove(chemin_zip)  # ne garder que le CSV réduit le temps de l'import

    importer_sirene(client, chemin_csv, base_id)
    # /import/apercu_local (orchestrateur.py) a déjà consommé ce fichier par
    # un renommage (§12.8) : plus rien à supprimer ici sauf si l'import a
    # échoué avant d'atteindre cette étape (fichier alors toujours présent).
    if os.path.isfile(chemin_csv):
        os.remove(chemin_csv)

    if not base_id:
        base_id = base_personnelle(client)["id"]
    deposer_scripts_exemple(client, base_id)

    print("Préparation du jeu de données Sirene terminée.")


if __name__ == "__main__":
    try:
        main()
    except ErreurHTTP as exc:
        print(f"Erreur HTTP lors de la préparation Sirene : {exc}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, TimeoutError, OSError, urllib.error.URLError) as exc:
        print(f"Échec de la préparation Sirene : {exc}", file=sys.stderr)
        sys.exit(1)
