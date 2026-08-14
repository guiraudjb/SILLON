"""SILLON - Travailleur de la file d'attente.

Consomme les jobs de type script_python / script_r (§5.4, §9) : lance un
conteneur éphémère par job, applique les quotas de temps/CPU/RAM (§7.7,
§11), collecte le journal et les fichiers produits, met à jour le statut
du job et déclenche la notification de fin de traitement.

Les jobs creation_base / suppression_base / import_csv restent du ressort
exclusif de l'orchestrateur (orchestrateur.py) : aucun recoupement, chaque
consommateur filtre strictement sur ses propres types de jobs, ce qui rend
sûre la coexistence des deux processus sur le même canal LISTEN/NOTIFY
(§9). Certaines fonctions (connexion au catalogue, lecture des paramètres)
sont dupliquées plutôt que partagées avec orchestrateur.py : les deux
services sont des paquets Debian installables indépendamment (§12.2), et
une poignée de fonctions dupliquées est un compromis raisonnable face à un
paquet de bibliothèque partagée supplémentaire pour si peu de code.
"""

import os
import shutil
import signal
import smtplib
import subprocess
import sys
import tempfile
import time
import zipfile
from email.message import EmailMessage

import psycopg2

# =============================================================================
# CONFIGURATION (partagée avec orchestrateur.py - §4.3, §12.2)
# =============================================================================
DB_HOST = os.environ.get("SILLON_DB_HOST", "localhost")
DB_PORT = os.environ.get("SILLON_DB_PORT", "5432")
DB_NAME = os.environ.get("SILLON_DB_NAME", "sillon_catalog")
DB_USER = "sillon_orchestrateur"
DB_PASSWORD = os.environ["SILLON_ORCHESTRATEUR_PASS"]
SMTP_HOTE = os.environ.get("SILLON_SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SILLON_SMTP_PORT", "25"))
SMTP_EXPEDITEUR = os.environ.get("SILLON_SMTP_FROM", "sillon@sillon.local")
URL_APPLICATION = os.environ.get("SILLON_URL", "https://localhost")

# Nom d'image partagé avec le paquet sillon-image-execution (§8.7,§12.2) et
# label partagé avec le postrm de ce paquet (§8.7) : les trois doivent
# rester alignés sur ces deux mêmes constantes.
IMAGE_EXECUTION = os.environ.get("SILLON_IMAGE_EXECUTION", "sillon-image-execution:latest")
LABEL_CONTENEUR = "sillon.managed-by=sillon-worker"

# Pas de réseau bridge --internal dédié : en rootless (www-data, §7.7), un
# tel bridge personnalisé n'existe que dans l'espace réseau privé de
# www-data, jamais sur la pile réseau réelle de l'hôte - confirmé par un
# déploiement réel (PostgreSQL n'a jamais pu être atteint via ce mécanisme,
# quelle que soit sa configuration). Le réseau pasta par défaut de Podman,
# lui, route nativement "host.containers.internal" vers l'hôte réel.
# L'isolation réseau reste une défense en profondeur : la portée réelle
# des données accessibles est bornée par le rôle PostgreSQL éphémère du
# script (§7.7, §8.8), qui demeure la limite dimensionnante.
HOTE_DB_DEPUIS_CONTENEUR = os.environ.get("SILLON_HOTE_DB_DEPUIS_CONTENEUR", "host.containers.internal")

RESULTATS_DIR = os.environ.get("SILLON_RESULTATS_DIR", "/var/lib/sillon/resultats")
try:
    os.makedirs(RESULTATS_DIR, exist_ok=True)
except OSError:
    RESULTATS_DIR = os.path.join(tempfile.gettempdir(), "sillon-resultats")
    os.makedirs(RESULTATS_DIR, exist_ok=True)

TYPES_GERES = ("script_python", "script_r")

arret_demande = False


def _gerer_signal(signum, frame):
    global arret_demande
    arret_demande = True


signal.signal(signal.SIGTERM, _gerer_signal)
signal.signal(signal.SIGINT, _gerer_signal)


class DepassementDelai(Exception):
    pass


class InterruptionService(Exception):
    pass


class AnnulationDemandee(Exception):
    pass


# =============================================================================
# ACCES A LA BASE DE DONNEES (§4.3, §4.4)
# =============================================================================
def connexion_catalogue():
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)


def lire_parametre(cle, defaut=None):
    with connexion_catalogue() as conn, conn.cursor() as cur:
        cur.execute("SELECT valeur FROM public.parametres WHERE cle = %s", (cle,))
        ligne = cur.fetchone()
    return ligne[0] if ligne else defaut


def marquer_statut(conn, id_job, statut, chemin_resultat=None, message_erreur=None, message_utilisateur=None):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT public.maj_statut_job(%s, %s, %s, %s, %s)",
            (id_job, statut, chemin_resultat, message_erreur, message_utilisateur),
        )
    conn.commit()


def _job_annule(conn, id_job):
    """Annulation demandée depuis l'onglet Suivi (§5.5) pendant que ce job
    est déjà "en_cours" : contrairement à un job encore "en_attente" (jamais
    repris par _prochain_job, cf. son WHERE statut = 'en_attente'), rien
    n'arrête ici de lui-même un conteneur déjà lancé - il faut le
    surveiller explicitement pendant son exécution (executer_conteneur)."""
    with conn.cursor() as cur:
        cur.execute("SELECT statut FROM public.jobs WHERE id = %s", (id_job,))
        statut = cur.fetchone()[0]
    conn.rollback()  # lecture seule : referme l'implicite plutôt que de la laisser "idle in transaction"
    return statut == "annule"


# =============================================================================
# EXECUTION DU CONTENEUR (§7.7, §8.7)
# =============================================================================
def executer_conteneur(conn, id_job, type_job, payload, mot_de_passe, repertoire_resultats, chemin_journal):
    delai_minutes = int(lire_parametre("duree_max_job_minutes", "30"))
    cpu_max = lire_parametre("cpu_max_conteneur_vcpu", "2")
    ram_max_mo = lire_parametre("ram_max_conteneur_mo", "4096")
    nom_conteneur = f"sillon-job-{id_job}"

    extension = ".py" if type_job == "script_python" else ".R"
    nom_script_conteneur = f"/travail/script{extension}"
    # Sans ceci, le journal en direct (§5.4, /jobs/<id>/journal) reste vide
    # pendant toute la durée d'un script cout (constaté en pratique) : la
    # sortie standard d'un interprète non attaché à un terminal est mise en
    # tampon par blocs (~4 Ko) plutôt que ligne à ligne, jamais vidée avant
    # la fin du process pour un script qui affiche seulement quelques
    # lignes - "python3 -u" désactive ce tampon ; Rscript n'a pas
    # d'équivalent intégré, d'où "stdbuf" (coreutils, déjà présent sur
    # toute image Debian de base, aucune dépendance supplémentaire).
    commande_interprete = (
        ["python3", "-u", nom_script_conteneur] if type_job == "script_python"
        else ["stdbuf", "-oL", "-eL", "Rscript", nom_script_conteneur]
    )

    dsn = (
        f"host={HOTE_DB_DEPUIS_CONTENEUR} port={DB_PORT} dbname={payload['nom_pg']} "
        f"user={payload['role_pg']} password={mot_de_passe} sslmode=prefer"
    )

    commande = [
        "podman", "run", "--rm",
        "--name", nom_conteneur,
        "--label", LABEL_CONTENEUR,
        # Pas de réseau bridge --internal partagé (§7.7) : en rootless, un
        # tel bridge personnalisé n'existe que dans l'espace réseau privé
        # de www-data, jamais sur la pile réseau réelle de l'hôte - aucune
        # adresse de ce bridge n'est donc joignable par PostgreSQL, quelle
        # que soit sa configuration (constaté lors d'un déploiement réel :
        # "Network is unreachable" puis, après correction erronée vers la
        # passerelle du bridge, "Connection refused" - l'hôte ne possède
        # tout simplement pas cette interface). Le réseau pasta par défaut
        # de Podman route nativement "host.containers.internal" vers
        # l'hôte réel (confirmé en pratique) ; "--dns none" retire la
        # résolution DNS comme première limite d'accès sortant, en
        # attendant une restriction réseau plus fine (§15.2 - l'isolation
        # réseau reste une défense en profondeur : la portée réelle des
        # données accessibles est bornée par le rôle PostgreSQL éphémère
        # du script, §7.7/§8.8, qui demeure la limite dimensionnante).
        "--dns", "none",
        "--read-only",
        "--tmpfs", "/tmp",
        "--user", "1000:1000",
        "--cpus", str(cpu_max),
        "--memory", f"{ram_max_mo}m",
        "--pids-limit", "256",
        "-v", f"{payload['chemin_script']}:{nom_script_conteneur}:ro",
        "-v", f"{repertoire_resultats}:/travail/resultats:rw",
        "-e", f"SILLON_DSN={dsn}",
        "-e", "SILLON_RESULTATS=/travail/resultats",
        IMAGE_EXECUTION,
        *commande_interprete,
    ]

    date_limite = time.monotonic() + delai_minutes * 60
    with open(chemin_journal, "wb") as journal:
        processus = subprocess.Popen(commande, stdout=journal, stderr=subprocess.STDOUT)
        while processus.poll() is None:
            if arret_demande:
                _arreter_conteneur(nom_conteneur, processus)
                raise InterruptionService()
            if time.monotonic() > date_limite:
                _arreter_conteneur(nom_conteneur, processus)
                raise DepassementDelai()
            # §5.5 : "annulation possible tant que le job est en attente ou
            # en cours" - un job "en_attente" n'est simplement jamais repris
            # (_prochain_job filtre sur ce statut), mais un job déjà lancé
            # ici doit être activement surveillé et son conteneur tué, sans
            # quoi l'annulation ne serait qu'un affichage trompeur pendant
            # que le traitement continuerait réellement en arrière-plan.
            if _job_annule(conn, id_job):
                _arreter_conteneur(nom_conteneur, processus)
                raise AnnulationDemandee()
            time.sleep(1)
        return processus.returncode


def _arreter_conteneur(nom_conteneur, processus):
    """Arrêt gracieux puis, si podman ne répond pas dans le délai imparti,
    repli forcé (§7.7) : le processus qui a lancé le conteneur (`podman
    run --rm`) ne doit jamais rester orphelin en attente indéfiniment,
    quelle que soit la raison de l'arrêt (dépassement de délai ou
    interruption du service)."""
    subprocess.run(["podman", "stop", "--time", "10", nom_conteneur],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        processus.wait(timeout=15)
    except subprocess.TimeoutExpired:
        subprocess.run(["podman", "kill", nom_conteneur],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processus.kill()
        processus.wait(timeout=10)


def empaqueter_resultats(id_job, repertoire_resultats):
    """Journal + fichiers produits par le script, réunis en une seule
    archive téléchargeable (§5.4)."""
    chemin_archive = f"{repertoire_resultats}.zip"
    with zipfile.ZipFile(chemin_archive, "w", zipfile.ZIP_DEFLATED) as archive:
        for racine, _dirs, fichiers in os.walk(repertoire_resultats):
            for nom in fichiers:
                chemin_complet = os.path.join(racine, nom)
                archive.write(chemin_complet, os.path.relpath(chemin_complet, repertoire_resultats))
    shutil.rmtree(repertoire_resultats, ignore_errors=True)
    return chemin_archive


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
        print(f"Échec d'envoi de la notification à {email_destinataire} : {exc}", file=sys.stderr)


# =============================================================================
# TRAITEMENT D'UN JOB (§5.4, §7.7, §8.7)
# =============================================================================
def traiter_job(conn, id_job, type_job, utilisateur_id, base_id, payload):
    marquer_statut(conn, id_job, "en_cours")

    with conn.cursor() as cur:
        cur.execute("SELECT email FROM public.utilisateurs WHERE id = %s", (utilisateur_id,))
        ligne = cur.fetchone()
    email_utilisateur = ligne[0] if ligne else None

    role_pg = payload["role_pg"]
    repertoire_resultats = os.path.join(RESULTATS_DIR, str(id_job))
    os.makedirs(repertoire_resultats, exist_ok=True)
    # 0o777 : ce répertoire est monté en écriture dans le conteneur pour
    # que le script y dépose son résultat (/travail/resultats), avec
    # l'UID 1000 imposé par --user (§7.7). En rootless, cet UID est
    # remappé côté hôte via la plage subuid de www-data (ex. 100999, pas
    # www-data lui-même) : un mode restrictif (0o755, propriétaire
    # www-data) rend le répertoire créé ici illisible en écriture pour ce
    # script, quel que soit le sous-répertoire par job - constaté en
    # pratique ("Permission denied" à l'écriture du résultat). Sans
    # information sensible ici (seulement la sortie propre du script,
    # isolée par job), un répertoire ouvert en écriture est un compromis
    # acceptable plutôt que de calculer l'UID hôte remappé exact.
    os.chmod(repertoire_resultats, 0o777)
    chemin_journal = os.path.join(repertoire_resultats, "journal.log")

    mot_de_passe = None
    statut_final = "erreur"
    message_erreur = None
    message_utilisateur = None
    chemin_archive = None

    try:
        # Fenêtre de connexion directe ouverte pour la durée du conteneur
        # uniquement (§7.7) : le rôle personnel redevient NOLOGIN dès le
        # bloc "finally", succès ou échec confondus.
        with conn.cursor() as cur:
            cur.execute("SELECT public.preparer_execution_script(%s)", (role_pg,))
            mot_de_passe = cur.fetchone()[0]
        conn.commit()

        code_retour = executer_conteneur(conn, id_job, type_job, payload, mot_de_passe, repertoire_resultats, chemin_journal)
        chemin_archive = empaqueter_resultats(id_job, repertoire_resultats)

        if code_retour == 0:
            statut_final = "termine"
        else:
            message_erreur = f"Le script s'est terminé en erreur (code {code_retour}). Voir le journal joint."
            message_utilisateur = message_erreur  # déjà compréhensible tel quel (§5.5)

    except DepassementDelai:
        chemin_archive = empaqueter_resultats(id_job, repertoire_resultats)
        delai = lire_parametre("duree_max_job_minutes", "30")
        message_erreur = f"Délai maximal dépassé ({delai} min) : le script a été interrompu."
        message_utilisateur = message_erreur  # déjà compréhensible tel quel (§5.5)

    except InterruptionService:
        # Arrêt du service en cours (prerm) : le job repasse en attente
        # plutôt qu'en erreur, un futur worker le reprendra depuis le
        # début - il n'a pas produit de résultat partiel exploitable.
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("UPDATE public.jobs SET statut = 'en_attente' WHERE id = %s", (id_job,))
        conn.commit()
        shutil.rmtree(repertoire_resultats, ignore_errors=True)
        return

    except AnnulationDemandee:
        # Le statut est déjà "annule" en base (posé par annuler_job() côté
        # utilisateur, §5.5) et le garde-fou de maj_statut_job() empêche de
        # toute façon tout écrasement ultérieur - rien à mettre à jour ici,
        # seulement nettoyer les résultats partiels et ne pas notifier.
        shutil.rmtree(repertoire_resultats, ignore_errors=True)
        return

    except Exception as exc:  # noqa: BLE001 - un job en erreur ne doit jamais faire tomber le consommateur
        # Chemin générique (échec de Podman lui-même, erreur disque...) :
        # str(exc) reste un message technique brut, contrairement aux deux
        # cas ci-dessus déjà rédigés pour un lecteur non technicien (§5.5).
        message_erreur = str(exc)
        message_utilisateur = "Une erreur inattendue est survenue pendant l'exécution du script ; voir le journal joint pour le détail."

    finally:
        if mot_de_passe is not None:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT public.cloturer_execution_script(%s)", (role_pg,))
                conn.commit()
            except psycopg2.Error as exc:
                print(f"AVERTISSEMENT : échec de clôture des identifiants éphémères du job {id_job} : {exc}", file=sys.stderr)
        if os.path.exists(payload["chemin_script"]):
            os.remove(payload["chemin_script"])

    marquer_statut(conn, id_job, statut_final, chemin_resultat=chemin_archive,
                    message_erreur=message_erreur, message_utilisateur=message_utilisateur)

    if email_utilisateur:
        if statut_final == "termine":
            envoyer_notification(
                email_utilisateur, "[SILLON] Script terminé",
                f"Votre script ({type_job}) est terminé.\nConsultez le résultat : {URL_APPLICATION}/#/suivi\n",
            )
        else:
            envoyer_notification(
                email_utilisateur, "[SILLON] Échec du script",
                f"Votre script ({type_job}) a échoué : {message_erreur}\n",
            )


# =============================================================================
# CONSOMMATEUR ASYNCHRONE DE LA FILE D'ATTENTE (§9)
# =============================================================================
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


def ecouter_jobs():
    while not arret_demande:
        try:
            conn = connexion_catalogue()
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("LISTEN sillon_jobs;")

            while not arret_demande:
                conn.poll()
                while conn.notifies:
                    conn.notifies.pop()

                conn.autocommit = False
                job = _prochain_job(conn)
                if job:
                    traiter_job(conn, *job)
                else:
                    conn.rollback()
                conn.autocommit = True

                time.sleep(2)  # sondage de repli, cf. orchestrateur.py
        except psycopg2.Error as exc:
            print(f"Connexion à la file d'attente perdue, nouvelle tentative : {exc}", file=sys.stderr)
            time.sleep(5)

    print("Arrêt demandé, fin de la boucle de consommation.", file=sys.stderr)


if __name__ == "__main__":
    ecouter_jobs()
