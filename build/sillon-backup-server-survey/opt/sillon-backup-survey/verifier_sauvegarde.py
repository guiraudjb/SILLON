"""SILLON - Sonde de surveillance des sauvegardes (sillon-backup-server-survey).

Verifie quotidiennement, via "pgbackrest info --output=json" execute
directement sur ce serveur de sauvegarde (le repertoire NFS exporte est
le depot pgBackRest lui-meme : pas besoin de contacter le serveur SILLON
pour connaitre l'etat des sauvegardes), que la derniere sauvegarde n'est
pas trop ancienne et qu'aucune sauvegarde n'est marquee en erreur - puis
envoie un bilan ou une alerte par e-mail via Postfix (relais interne
configure a l'installation, cf. postinst).

ADMIN_EMAIL est relu depuis /etc/sillon-backup/survey.env a chaque
execution (pas fige au moment de l'installation), pour qu'un changement
de destinataire soit pris en compte sans reinstaller le paquet.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

STANZA = "sillon"
CONF_ENV = "/etc/sillon-backup/survey.env"
# Sauvegarde quotidienne attendue : tolerance au-dela de 24h pour
# absorber un leger retard d'execution du cron sans fausse alerte.
SEUIL_RETARD_HEURES = 30


def lire_admin_email():
    """Lit ADMIN_EMAIL dans survey.env - format "CLE=valeur" simple,
    pas de dependance a un shell pour parser ce fichier."""
    try:
        with open(CONF_ENV, encoding="utf-8") as fichier:
            for ligne in fichier:
                ligne = ligne.strip()
                if ligne.startswith("ADMIN_EMAIL="):
                    return ligne.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "equipe.support@example.gouv.fr"


def lire_info():
    resultat = subprocess.run(
        ["pgbackrest", f"--stanza={STANZA}", "--output=json", "info"],
        capture_output=True, text=True, timeout=60, check=False,
    )
    return resultat.stdout


def construire_rapport():
    sortie = lire_info()
    try:
        donnees = json.loads(sortie)
    except ValueError:
        return ("[ALERTE CRITIQUE] Sonde de sauvegarde SILLON en erreur",
                "Impossible d'interroger pgBackRest (\"pgbackrest info\" n'a "
                "pas renvoye de JSON exploitable). Sortie brute :\n\n" + sortie)

    stanzas = [s for s in donnees if s.get("name") == STANZA]
    if not stanzas or not stanzas[0].get("backup"):
        return ("[ALERTE CRITIQUE] Aucune sauvegarde SILLON disponible",
                f"Aucune sauvegarde n'a ete trouvee pour la stanza \"{STANZA}\" "
                "dans le depot pgBackRest. L'integrite des donnees SILLON "
                "n'est plus garantie en cas de sinistre - verifier "
                "sillon-backup-client sur le serveur SILLON et les journaux "
                "cron (\"journalctl -t sillon-backup\").")

    sauvegardes = stanzas[0]["backup"]
    en_erreur = [b["label"] for b in sauvegardes if b.get("error")]
    # La derniere sauvegarde VALIDE n'est pas forcement le dernier element
    # de la liste : une sauvegarde recente peut elle-meme etre celle en
    # erreur (constate en test) - il faut l'exclure avant de prendre [-1],
    # sans quoi le message presenterait une sauvegarde en erreur comme
    # "valide".
    valides = [b for b in sauvegardes if not b.get("error")]

    lignes_historique = "\n".join(
        "{:<25} {:<10} {} UTC{}".format(
            b["label"], b["type"],
            datetime.fromtimestamp(b["timestamp"]["stop"], tz=timezone.utc)
            .strftime("%Y-%m-%d %H:%M"),
            "  [ERREUR]" if b.get("error") else "",
        )
        for b in sauvegardes
    )

    if en_erreur:
        sujet = "[ALERTE CRITIQUE] Sauvegarde(s) SILLON en erreur"
        if valides:
            derniere = valides[-1]
            fin = datetime.fromtimestamp(derniere["timestamp"]["stop"], tz=timezone.utc)
            age = datetime.now(tz=timezone.utc) - fin
            details_derniere = (
                f"Derniere sauvegarde valide : {derniere['label']} ({derniere['type']}), "
                f"terminee le {fin:%Y-%m-%d %H:%M} UTC (il y a {age}).\n"
            )
        else:
            details_derniere = "Aucune sauvegarde valide disponible dans le depot.\n"
        corps = (
            "Sauvegarde(s) marquee(s) en erreur par pgBackRest : "
            f"{', '.join(en_erreur)}.\n\n{details_derniere}"
        )
    else:
        # Sans sauvegarde en erreur, "valides" est forcement identique a
        # "sauvegardes" (non vide - le cas vide a deja ete traite plus haut).
        derniere = valides[-1]
        fin = datetime.fromtimestamp(derniere["timestamp"]["stop"], tz=timezone.utc)
        age = datetime.now(tz=timezone.utc) - fin
        if age > timedelta(hours=SEUIL_RETARD_HEURES):
            sujet = "[AVERTISSEMENT] Sauvegarde SILLON en retard"
            corps = (
                f"La derniere sauvegarde ({derniere['label']}, type {derniere['type']}) "
                f"remonte a {age} (seuil : {SEUIL_RETARD_HEURES} h).\n"
                "Verifier que la tache planifiee de sillon-backup-client s'execute "
                "bien sur le serveur SILLON et que le partage NFS est accessible.\n"
            )
        else:
            sujet = "[OK] Rapport de sauvegarde SILLON"
            corps = (
                f"Derniere sauvegarde : {derniere['label']} ({derniere['type']}), "
                f"terminee le {fin:%Y-%m-%d %H:%M} UTC (il y a {age}).\n"
            )

    corps += (
        "\n==========================================\n"
        "Historique des sauvegardes disponibles :\n"
        "==========================================\n"
        f"{lignes_historique}\n"
    )
    return sujet, corps


def envoyer_mail(destinataire, sujet, corps):
    subprocess.run(["mail", "-s", sujet, destinataire], input=corps, text=True, check=True)


def main():
    sujet, corps = construire_rapport()
    destinataire = lire_admin_email()
    try:
        envoyer_mail(destinataire, sujet, corps)
    except (subprocess.CalledProcessError, OSError) as erreur:
        print(f"ERREUR : envoi du mail impossible ({erreur}).", file=sys.stderr)
        print(f"{sujet}\n\n{corps}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
