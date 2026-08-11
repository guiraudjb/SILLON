# SILLON - Image d'execution des scripts Python/R
# Isolation de l'execution de code depose par les utilisateurs (§7.7, §8.7).
# Utilisee exclusivement par sillon-worker, qui impose a chaque lancement
# --read-only, --tmpfs /tmp, --user 1000:1000, --network (interne),
# --cpus/--memory/--pids-limit (worker.py, executer_conteneur). Cette image
# ne fait qu'honorer ce contrat, elle ne le recree pas.

FROM debian:13-slim

# Liste de librairies validees (§15.2, point de vigilance resolu ici avec
# un jeu de depart raisonnable, a confirmer/etendre selon les usages
# reels) : exclusivement des paquets Debian officiels, jamais de
# pip/CRAN a la volee dans le conteneur (§7.7) - toute evolution de cette
# liste passe par une reconstruction de l'image, pas par une installation
# utilisateur.
#
# Cette liste est aussi affichee cote utilisateur avant le depot d'un
# script (§5.4) via build/sillon-server/var/www/html/SILLON/
# librairies-scripts.json, tenu a jour manuellement en miroir de celle-ci
# (pas d'extraction automatique au build : deux listes courtes et stables,
# une dependance de build supplementaire pour si peu de valeur).
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        python3 \
        python3-pandas \
        python3-numpy \
        python3-matplotlib \
        python3-psycopg2 \
        python3-openpyxl \
        r-base-core \
        r-cran-tidyverse \
        r-cran-dbi \
        r-cran-rpostgresql \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur non privilegie (§7.7). Le worker impose deja --user 1000:1000
# a l'execution ; un compte nomme correspondant evite les avertissements de
# certains outils (R notamment) face a un UID sans entree /etc/passwd.
RUN groupadd --gid 1000 sillon \
    && useradd --uid 1000 --gid 1000 --home-dir /travail --no-create-home \
        --shell /usr/sbin/nologin sillon

# Points de montage attendus par worker.py : /travail/resultats (lecture-
# ecriture, fichiers produits par le script) et /travail/script.{py,R}
# (lecture seule, depose par worker.py juste avant le lancement).
# Pre-crees pour que le montage reussisse proprement sous --read-only.
RUN mkdir -p /travail/resultats \
    && touch /travail/script.py /travail/script.R \
    && chown -R sillon:sillon /travail

# Repertoires d'ecriture habituels de l'ecosysteme Python/R redetournes
# vers /tmp, seul point inscriptible du systeme de fichiers racine en
# dehors de /travail/resultats (--tmpfs /tmp, §7.7) : sans ca, des
# bibliotheques comme matplotlib echouent ou avertissent au premier usage
# faute de pouvoir ecrire leur cache habituel sous $HOME.
ENV HOME=/tmp \
    TMPDIR=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONDONTWRITEBYTECODE=1 \
    R_LIBS_USER=/tmp/R

WORKDIR /travail/resultats
USER sillon

# Pas d'ENTRYPOINT/CMD : worker.py fournit explicitement la commande a
# chaque lancement ("python3 /travail/script.py" ou "Rscript
# /travail/script.R", §9) ; l'absence de shell intermediaire permet aux
# signaux (arret gracieux, §7.7) d'atteindre directement l'interprete.
