"""SILLON - Purge automatique (§8.9, §8.12).

Nettoie quotidiennement ce qui s'accumule sur le serveur au fil de
l'usage : résultats de jobs (exports SQL, archives de scripts, §5.3/§5.4),
dépôts temporaires orphelins (§5.1, jamais validés suite à un crash en
cours de route), et journal d'audit (§8.12). Exécuté en root par
/etc/cron.d/sillon_purge - les opérations sur le catalogue applicatif sont
déléguées à "sudo -u postgres psql" (rôle système "postgres", seul à
passer le trigger d'immuabilité de public.audit_logs), le reste
(suppression de fichiers sous /var/lib/sillon) directement, root étant de
toute façon nécessaire pour atteindre les fichiers de résultats
appartenant à l'UID remappé du conteneur d'exécution (§7.7).

Les durées de rétention sont lues dans public.parametres (modifiables à
chaud par un administrateur depuis le panneau Administration) plutôt que
codées en dur ici, contrairement aux anciens cron.d de sillon-server que
ce paquet remplace.
"""

import os
import shutil
import subprocess
import sys
import time

DB_NAME = "sillon_catalog"
STAGING_DIR = os.environ.get("SILLON_STAGING_DIR", "/var/lib/sillon/staging")
RESULTATS_DIR = os.environ.get("SILLON_RESULTATS_DIR", "/var/lib/sillon/resultats")

# Valeurs de repli si la base est injoignable (paquet installé avant
# sillon-server, service arrêté...) - identiques aux valeurs par défaut de
# schema.sql, pour que la purge des fichiers reste utile même sans base.
DEFAUTS = {
    "retention_resultats_jours": 90,
    "retention_audit_mois": 12,
    "retention_staging_heures": 48,
}


def lire_parametre(cle):
    """Lit un entier dans public.parametres via le rôle système "postgres".
    Retombe sur la valeur par défaut si la base est injoignable, la ligne
    absente, ou la valeur non entière - un paramètre mal renseigné par un
    administrateur ne doit jamais interrompre la purge des autres points."""
    try:
        resultat = subprocess.run(
            ["sudo", "-u", "postgres", "psql", "-tAc",
             f"SELECT valeur FROM public.parametres WHERE cle = '{cle}'",
             "-d", DB_NAME],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return int(resultat.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, OSError) as erreur:
        print(f"AVERTISSEMENT : lecture de '{cle}' impossible ({erreur}), "
              f"repli sur {DEFAUTS[cle]}.", file=sys.stderr)
        return DEFAUTS[cle]


def purger_repertoire(chemin, seuil_secondes, description):
    """Supprime chaque entrée directe de "chemin" (fichier ou répertoire)
    dont la dernière modification dépasse le seuil - équivalent du "find
    -mindepth 1 -maxdepth 1 -mtime +N -exec rm -rf" déjà éprouvé en
    production (anciens cron.d de sillon-server), sans shell externe."""
    if not os.path.isdir(chemin):
        return
    limite = time.time() - seuil_secondes
    nb = 0
    for nom in os.listdir(chemin):
        entree = os.path.join(chemin, nom)
        try:
            if os.lstat(entree).st_mtime >= limite:
                continue
            if os.path.isdir(entree) and not os.path.islink(entree):
                shutil.rmtree(entree, ignore_errors=True)
            else:
                os.remove(entree)
            nb += 1
        except OSError as erreur:
            print(f"AVERTISSEMENT : suppression de {entree} impossible ({erreur}).",
                  file=sys.stderr)
    print(f"{description} : {nb} élément(s) purgé(s) dans {chemin}.")


def purger_audit_logs(retention_mois):
    """DELETE exécuté par le rôle "postgres" (cf. docstring du module) -
    retention_mois provient de lire_parametre(), donc toujours un int à ce
    stade ; interpolé tel quel dans le DELETE (pas de contenu utilisateur)."""
    try:
        subprocess.run(
            ["sudo", "-u", "postgres", "psql", "-c",
             "DELETE FROM public.audit_logs WHERE date_action < "
             f"CURRENT_DATE - INTERVAL '{retention_mois} months'",
             "-d", DB_NAME],
            capture_output=True, text=True, timeout=60, check=True,
        )
        print(f"audit_logs : purge des entrées de plus de {retention_mois} mois effectuée.")
    except (subprocess.CalledProcessError, OSError) as erreur:
        print(f"AVERTISSEMENT : purge de audit_logs impossible ({erreur}).", file=sys.stderr)


def main():
    retention_resultats_jours = lire_parametre("retention_resultats_jours")
    retention_audit_mois = lire_parametre("retention_audit_mois")
    retention_staging_heures = lire_parametre("retention_staging_heures")

    purger_repertoire(RESULTATS_DIR, retention_resultats_jours * 86400,
                       "Résultats de jobs")
    purger_repertoire(STAGING_DIR, retention_staging_heures * 3600,
                       "Dépôts temporaires orphelins")
    purger_audit_logs(retention_audit_mois)


if __name__ == "__main__":
    main()
