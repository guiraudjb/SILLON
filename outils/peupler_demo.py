#!/usr/bin/env python3
"""SILLON - Peuplement d'un compte de démonstration.

Script autonome, à lancer VOLONTAIREMENT par l'administrateur sur une VM
de démonstration ou de formation - jamais exécuté par les paquets Debian
eux-mêmes (§12.6 : un compte au mot de passe fixe et documenté ne doit
jamais apparaître sur un déploiement sans décision explicite de
l'administrateur qui l'exploite).

Crée, ou réutilise s'il existe déjà (script rejouable sans effet de bord
en double) :
  - un compte "demo" de profil agent (§3), mot de passe fixe (--demo-password) ;
  - sa base personnelle, avec le jeu de données fictif communes_exemple.csv
    importé dedans (table "communes_exemple") ;
  - trois requêtes SQL d'exemple, déjà exécutées et donc déjà présentes
    dans son historique au premier login (§5.3) ;
  - un script Python et un script R d'exemple (donnees_demo/), réellement
    soumis à la file d'attente et attendus jusqu'à leur terme (§5.4, §9) :
    leurs résultats sont déjà téléchargeables depuis l'onglet Suivi.

Usage :
    ./peupler_demo.py --url https://mon-serveur-sillon --admin-password '...'

Sans --admin-password, le mot de passe est demandé de façon masquée.
"""
import argparse
import getpass
import http.cookiejar
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
DONNEES_DEMO = os.path.join(ICI, "donnees_demo")

REQUETES_EXEMPLE = [
    "SELECT * FROM communes_exemple ORDER BY population DESC LIMIT 10",
    "SELECT region_exemple, COUNT(*) AS nb_communes, SUM(population) AS population_totale, "
    "ROUND(AVG(superficie_km2), 1) AS superficie_moyenne FROM communes_exemple "
    "GROUP BY region_exemple ORDER BY population_totale DESC",
    "SELECT nom_commune, population, ROUND(population / superficie_km2, 1) AS densite "
    "FROM communes_exemple ORDER BY densite DESC LIMIT 5",
]

SCRIPTS_EXEMPLE = ["exemple_stats.py", "exemple_graphique.R"]


class ErreurHTTP(Exception):
    def __init__(self, status, corps):
        super().__init__(f"HTTP {status} : {corps}")
        self.status = status
        self.corps = corps


class Client:
    """Client HTTP minimal (bibliothèque standard uniquement, cf. §12 -
    aucune dépendance supplémentaire à vendoriser pour ce seul script) qui
    conserve le cookie de session "sillon_token" entre les appels, comme le
    ferait un navigateur."""

    def __init__(self, url_base, contexte_ssl):
        self.url_base = url_base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=contexte_ssl),
        )

    def _ouvrir(self, requete):
        try:
            with self.opener.open(requete, timeout=60) as reponse:
                return reponse.status, reponse.read()
        except urllib.error.HTTPError as exc:
            raise ErreurHTTP(exc.code, exc.read().decode("utf-8", errors="replace")) from exc

    def get_json(self, chemin):
        requete = urllib.request.Request(self.url_base + chemin, method="GET")
        _statut, corps = self._ouvrir(requete)
        return json.loads(corps)

    def post_json(self, chemin, objet):
        donnees = json.dumps(objet).encode("utf-8")
        requete = urllib.request.Request(
            self.url_base + chemin, data=donnees, method="POST",
            headers={"Content-Type": "application/json"},
        )
        statut, corps = self._ouvrir(requete)
        return statut, (json.loads(corps) if corps else {})

    def post_multipart(self, chemin, champs, fichiers):
        """champs : dict[str, str] ; fichiers : dict[str, (nom, octets)]."""
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
        statut, reponse_corps = self._ouvrir(requete)
        return statut, (json.loads(reponse_corps) if reponse_corps else {})


def se_connecter(client, email, mot_de_passe):
    client.post_json("/api/rpc/login", {"email": email, "password": mot_de_passe})


def utilisateur_existe(client, email):
    resultat = client.get_json(f"/api/utilisateurs?email=eq.{urllib.parse.quote(email)}")
    return bool(resultat)


def creer_compte_demo(client, email, mot_de_passe, nom_complet):
    if utilisateur_existe(client, email):
        print(f"Compte {email} déjà présent - réutilisé tel quel.")
        return
    client.post_json("/api/rpc/creer_utilisateur", {
        "_email": email, "_password": mot_de_passe,
        "_nom_complet": nom_complet, "_profil": "agent",
    })
    print(f"Compte {email} créé (profil agent).")


def base_personnelle_demo(client):
    """Base dont le compte actuellement connecté est propriétaire, si elle
    existe déjà (script rejouable, cf. correctif d'idempotence de
    "creation_base" côté orchestrateur)."""
    bases = client.get_json("/api/vue_mes_bases?je_suis_proprietaire=eq.true")
    return bases[0] if bases else None


def importer_jeu_de_donnees(client):
    chemin_csv = os.path.join(DONNEES_DEMO, "communes_exemple.csv")
    with open(chemin_csv, "rb") as f:
        contenu_csv = f.read()

    apercu = client.post_multipart(
        "/orchestrateur/import/apercu",
        {"avec_entete": "true"},
        {"fichier": ("communes_exemple.csv", contenu_csv)},
    )[1]

    colonnes = [{"nom_normalise": c["nom_normalise"], "type": c["type_suggere"]} for c in apercu["colonnes"]]

    base_existante = base_personnelle_demo(client)
    corps = {
        "jeton": apercu["jeton"],
        "nom_table": "communes_exemple",
        "colonnes": colonnes,
        "encodage": apercu["encodage_detecte"],
        "delimiteur": apercu["delimiteur_detecte"],
        "avec_entete": True,
        # Rejouable sans collision (§5.1, étape 6) : un précédent passage
        # du script a déjà pu créer cette même table.
        "remplacer": True,
    }
    if base_existante:
        corps["base_id"] = base_existante["id"]
    statut, resultat = client.post_json("/orchestrateur/import/valider", corps)
    print(f"Import du jeu de données d'exemple : {resultat}")

    base = base_personnelle_demo(client)
    if not base:
        raise RuntimeError("Base personnelle du compte demo introuvable après import.")
    return base["id"]


def executer_requetes_exemple(client, base_id):
    for requete in REQUETES_EXEMPLE:
        client.post_json("/orchestrateur/sql", {"base_id": base_id, "requete": requete})
        print(f"Requête exécutée (historique alimenté) : {requete[:70]}...")


def attendre_job(client, id_job, delai_max_s=180):
    fin = time.monotonic() + delai_max_s
    while time.monotonic() < fin:
        jobs = client.get_json(f"/api/vue_mes_jobs?id=eq.{id_job}")
        if jobs and jobs[0]["statut"] in ("termine", "erreur"):
            return jobs[0]
        time.sleep(2)
    raise TimeoutError(
        f"Job {id_job} toujours en cours après {delai_max_s}s - "
        "sillon-worker/Podman sont-ils opérationnels ?"
    )


def deposer_et_attendre_scripts(client, base_id):
    for nom_fichier in SCRIPTS_EXEMPLE:
        chemin = os.path.join(DONNEES_DEMO, nom_fichier)
        with open(chemin, "rb") as f:
            contenu = f.read()
        _statut, resultat = client.post_multipart(
            "/orchestrateur/scripts/deposer",
            {"base_id": str(base_id)},
            {"fichier": (nom_fichier, contenu)},
        )
        id_job = resultat["id_job"]
        print(f"Script {nom_fichier} déposé (job n°{id_job}), attente de la fin d'exécution...")
        job = attendre_job(client, id_job)
        if job["statut"] == "termine":
            print(f"  -> terminé, résultat téléchargeable (job n°{id_job}).")
        else:
            print(f"  -> ATTENTION, en erreur : {job.get('message_erreur')}", file=sys.stderr)


def construire_contexte_ssl(cacert):
    if cacert:
        contexte = ssl.create_default_context(cafile=cacert)
        return contexte
    chemin_defaut = "/etc/ssl/sillon/sillon.crt"
    if os.path.isfile(chemin_defaut):
        return ssl.create_default_context(cafile=chemin_defaut)
    print(
        "AVERTISSEMENT : certificat SILLON introuvable, vérification TLS désactivée "
        "(normal en local avec le certificat auto-signé par défaut du postinst).",
        file=sys.stderr,
    )
    contexte = ssl._create_unverified_context()
    return contexte


def main():
    analyseur = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--url", default="https://localhost", help="URL de base de l'instance SILLON")
    analyseur.add_argument("--admin-email", default="admin@sillon.local")
    analyseur.add_argument("--admin-password", default=None, help="Demandé de façon masquée si omis")
    analyseur.add_argument("--demo-email", default="demo@sillon.local")
    analyseur.add_argument("--demo-password", default="demo",
                            help="Mot de passe fixe du compte demo (défaut : \"demo\" - "
                                 "à ne jamais laisser sur un déploiement exposé)")
    analyseur.add_argument("--demo-nom", default="Compte de démonstration")
    analyseur.add_argument("--cacert", default=None, help="Certificat TLS à utiliser (sinon auto-détecté)")
    args = analyseur.parse_args()

    mot_de_passe_admin = args.admin_password or getpass.getpass(f"Mot de passe de {args.admin_email} : ")

    contexte_ssl = construire_contexte_ssl(args.cacert)
    client = Client(args.url, contexte_ssl)

    print(f"Connexion en tant que {args.admin_email}...")
    se_connecter(client, args.admin_email, mot_de_passe_admin)

    creer_compte_demo(client, args.demo_email, args.demo_password, args.demo_nom)

    print(f"Connexion en tant que {args.demo_email}...")
    se_connecter(client, args.demo_email, args.demo_password)

    base_id = importer_jeu_de_donnees(client)
    executer_requetes_exemple(client, base_id)
    deposer_et_attendre_scripts(client, base_id)

    print(
        f"\nCompte de démonstration prêt : {args.demo_email} / {args.demo_password}\n"
        "Historique de requêtes et résultats de scripts déjà disponibles au premier login."
    )


if __name__ == "__main__":
    try:
        main()
    except ErreurHTTP as exc:
        print(f"Erreur HTTP lors du peuplement : {exc}", file=sys.stderr)
        sys.exit(1)
    except (TimeoutError, RuntimeError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)
