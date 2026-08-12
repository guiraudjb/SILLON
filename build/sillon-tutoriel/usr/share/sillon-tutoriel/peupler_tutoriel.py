#!/usr/bin/env python3
"""SILLON - Peuplement du compte de démonstration du paquet sillon-tutoriel.

Contrairement à outils/peupler_demo.py (script volontaire, jamais exécuté par
un paquet - voir sa docstring), celui-ci est appelé par le postinst de
sillon-tutoriel : un paquet séparé et explicitement optionnel, à installer
uniquement sur une VM de démonstration/formation, jamais sur un déploiement
de production (§12.6 - un compte au mot de passe fixe et documenté ne doit
jamais apparaître sans décision explicite de l'administrateur qui installe
CE paquet précisément pour ça).

Le postinst tourne en root et n'a jamais accès au mot de passe administrateur
(généré aléatoirement une seule fois à l'installation de sillon-server,
jamais stocké en clair, §12.3) : il fournit donc directement à ce script un
jeton JWT valide pour le compte demo (signé côté PostgreSQL avec
auth.sign_jwt(), le même mécanisme que login()), plutôt qu'un couple
email/mot de passe à échanger contre un jeton.
"""
import argparse
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.path.join(ICI, "donnees")
SCRIPTS = os.path.join(ICI, "scripts")

# Sous-ensemble des exercices du tutoriel PDF (§5.3) : préchargé dans
# l'historique pour que le compte demo ait déjà des exemples travaillés à
# consulter/réexécuter dès le premier login - le PDF en propose davantage,
# à écrire soi-même.
REQUETES_EXEMPLE = [
    "SELECT * FROM communes_france WHERE dep_code = '75' ORDER BY nom_standard LIMIT 20",
    "SELECT nom_standard, population FROM communes_france WHERE dep_code = '13' ORDER BY population DESC LIMIT 10",
    "SELECT COUNT(*) AS nb_communes, SUM(population) AS population_totale FROM communes_france WHERE dep_code = '69'",
    "SELECT dep_nom, COUNT(*) AS nb_communes, SUM(population) AS population_totale FROM communes_france "
    "GROUP BY dep_nom ORDER BY population_totale DESC LIMIT 15",
    "SELECT reg_nom, ROUND(AVG(densite)::numeric, 1) AS densite_moyenne FROM communes_france "
    "GROUP BY reg_nom HAVING AVG(densite) > 200 ORDER BY densite_moyenne DESC",
    "SELECT nom_standard, dep_nom, population FROM communes_france "
    "WHERE population > (SELECT AVG(population) FROM communes_france) ORDER BY population DESC LIMIT 20",
    "SELECT c.nom_standard AS commune, c.population AS population_chef_lieu, r.reg_nom "
    "FROM communes_france c JOIN regions_france r ON c.code_insee = r.chef_lieu_code_insee "
    "ORDER BY c.population DESC",
]

SCRIPTS_EXEMPLE = ["analyse_demographie.py", "analyse_densite.R", "carte_departements.py", "carte_departements.R"]

TABLES = [
    ("communes_france.csv", "communes_france"),
    ("regions_france.csv", "regions_france"),
    # Contours départementaux réels (source IGN ADMIN EXPRESS, Licence
    # Ouverte 2.0), aplatis en points ordonnés (dep_code, groupe, ordre,
    # longitude, latitude) : pas de format géospatial (GeoJSON...) en base,
    # ni Python ni R n'ont de librairie dédiée dans l'image d'exécution
    # (§7.7) - un simple CSV de points reste lisible en SQL basique et
    # suffit à reconstituer chaque polygone (cf. carte_departements.py/.R).
    ("contours_departements.csv", "contours_departements"),
]

# La détection automatique de type (suggerer_type(), orchestrateur.py)
# n'échantillonne que les 50 premières lignes de l'aperçu (§5.1), jamais
# le fichier entier - deux angles morts constatés en pratique sur ce jeu
# de données précis :
#  - "code_insee"/"dep_code" : entièrement numériques dans l'échantillon
#    (département 01), donc suggérés "Entier" - qui échoue plus loin dans
#    le fichier complet, en Corse ("2A001", "2B033"...). Un identifiant
#    reste de toute façon un Texte par nature (un "Entier" perdrait aussi
#    les zéros de tête, ex. "01001" -> 1001).
#  - "groupe"/"ordre" (contours_departements) : le premier département
#    (Ain, un seul anneau, largement plus de 50 points) remplit tout
#    l'échantillon avec "groupe" = "1" - qui coche la case "ressemble à
#    un booléen" du détecteur (valeurs dans vrai/faux/true/false/0/1),
#    avant même que "Entier" ne soit envisagé.
# Aucune de ces colonnes n'est donc laissée à la suggestion automatique.
TYPES_FORCES = {
    "code_insee": "Texte", "dep_code": "Texte", "reg_code": "Texte", "chef_lieu_code_insee": "Texte",
    "groupe": "Entier", "ordre": "Entier",
}


class ErreurHTTP(Exception):
    def __init__(self, status, corps):
        super().__init__(f"HTTP {status} : {corps}")


class Client:
    def __init__(self, url_base, jeton, contexte_ssl):
        self.url_base = url_base.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=contexte_ssl))
        self.jeton = jeton

    def _ouvrir(self, requete):
        requete.add_header("Cookie", f"sillon_token={self.jeton}")
        try:
            with self.opener.open(requete, timeout=60) as reponse:
                return reponse.status, reponse.read()
        except urllib.error.HTTPError as exc:
            raise ErreurHTTP(exc.code, exc.read().decode("utf-8", errors="replace")) from exc

    def get_json(self, chemin):
        _statut, corps = self._ouvrir(urllib.request.Request(self.url_base + chemin, method="GET"))
        return json.loads(corps)

    def post_json(self, chemin, objet):
        donnees = json.dumps(objet).encode("utf-8")
        requete = urllib.request.Request(
            self.url_base + chemin, data=donnees, method="POST",
            headers={"Content-Type": "application/json"},
        )
        _statut, corps = self._ouvrir(requete)
        return json.loads(corps) if corps else None

    def post_multipart(self, chemin, champs, fichiers):
        frontiere = uuid.uuid4().hex
        parties = []
        for cle, valeur in champs.items():
            parties.append(
                f'--{frontiere}\r\nContent-Disposition: form-data; name="{cle}"\r\n\r\n{valeur}\r\n'.encode("utf-8")
            )
        for cle, (nom_fichier, contenu) in fichiers.items():
            type_mime = mimetypes.guess_type(nom_fichier)[0] or "application/octet-stream"
            entete = (
                f'--{frontiere}\r\nContent-Disposition: form-data; name="{cle}"; filename="{nom_fichier}"\r\n'
                f"Content-Type: {type_mime}\r\n\r\n"
            ).encode("utf-8")
            parties.append(entete + contenu + b"\r\n")
        parties.append(f"--{frontiere}--\r\n".encode("utf-8"))
        corps = b"".join(parties)
        requete = urllib.request.Request(
            self.url_base + chemin, data=corps, method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={frontiere}"},
        )
        _statut, reponse_corps = self._ouvrir(requete)
        return json.loads(reponse_corps) if reponse_corps else None


def base_personnelle(client):
    bases = client.get_json("/api/vue_mes_bases?je_suis_proprietaire=eq.true")
    return bases[0] if bases else None


def importer_table(client, nom_fichier, nom_table, base_id):
    chemin_csv = os.path.join(DONNEES, nom_fichier)
    with open(chemin_csv, "rb") as f:
        contenu_csv = f.read()

    apercu = client.post_multipart(
        "/orchestrateur/import/apercu", {"avec_entete": "true"}, {"fichier": (nom_fichier, contenu_csv)},
    )
    colonnes = [
        {"nom_normalise": c["nom_normalise"], "type": TYPES_FORCES.get(c["nom_normalise"], c["type_suggere"])}
        for c in apercu["colonnes"]
    ]

    corps = {
        "jeton": apercu["jeton"], "nom_table": nom_table, "colonnes": colonnes,
        "encodage": apercu["encodage_detecte"], "delimiteur": apercu["delimiteur_detecte"],
        "avec_entete": True, "remplacer": True,
    }
    if base_id:
        corps["base_id"] = base_id
    resultat = client.post_json("/orchestrateur/import/valider", corps)
    print(f"  {nom_table} : {resultat}")


def attendre_job(client, id_job, delai_max_s=180):
    fin = time.monotonic() + delai_max_s
    while time.monotonic() < fin:
        jobs = client.get_json(f"/api/vue_mes_jobs?id=eq.{id_job}")
        if jobs and jobs[0]["statut"] in ("termine", "erreur"):
            return jobs[0]
        time.sleep(2)
    raise TimeoutError(f"Job {id_job} toujours en cours après {delai_max_s}s.")


def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--url", default="https://localhost")
    analyseur.add_argument("--jeton", required=True, help="Jeton JWT du compte demo, signé côté PostgreSQL")
    analyseur.add_argument("--cacert", default=None)
    args = analyseur.parse_args()

    if args.cacert and os.path.isfile(args.cacert):
        contexte = ssl.create_default_context(cafile=args.cacert)
    else:
        contexte = ssl._create_unverified_context()

    client = Client(args.url, args.jeton, contexte)

    print("Import du jeu de données réel (communes, régions et contours départementaux)...")
    base = base_personnelle(client)
    base_id = base["id"] if base else None
    for nom_fichier, nom_table in TABLES:
        importer_table(client, nom_fichier, nom_table, base_id)
        if not base_id:
            base_id = base_personnelle(client)["id"]
    base = {"id": base_id}

    print("Exécution des requêtes d'exemple (historique)...")
    for requete in REQUETES_EXEMPLE:
        try:
            client.post_json("/orchestrateur/sql", {"base_id": base["id"], "requete": requete})
        except ErreurHTTP as exc:
            print(f"  AVERTISSEMENT requête ignorée : {exc}", file=sys.stderr)

    print("Dépôt et exécution des scripts d'exemple...")
    for nom_fichier in SCRIPTS_EXEMPLE:
        chemin = os.path.join(SCRIPTS, nom_fichier)
        with open(chemin, "rb") as f:
            contenu = f.read()
        resultat = client.post_multipart(
            "/orchestrateur/scripts/deposer", {"base_id": str(base["id"])}, {"fichier": (nom_fichier, contenu)},
        )
        id_job = resultat["id_job"]
        print(f"  {nom_fichier} (job n°{id_job})...")
        try:
            job = attendre_job(client, id_job)
            print(f"    -> {job['statut']}")
        except TimeoutError as exc:
            print(f"  AVERTISSEMENT : {exc}", file=sys.stderr)

    print("Peuplement du compte de démonstration terminé.")


if __name__ == "__main__":
    try:
        main()
    except ErreurHTTP as exc:
        print(f"Erreur HTTP lors du peuplement : {exc}", file=sys.stderr)
        sys.exit(1)
