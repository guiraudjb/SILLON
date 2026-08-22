#!/bin/bash
# ==============================================================================
# SCRIPT DE SAUVEGARDE PHYSIQUE - SILLON (pgBackRest)
# ==============================================================================
# Politique : sauvegarde complete ("full") le 1er de chaque mois,
# incrementale ("incr") les autres jours. La volumetrie du cluster SILLON
# (catalogue + une base physique par agent, alimentees par import CSV,
# potentiellement plusieurs centaines de Mo chacune) rend un dump complet
# quotidien (a la pg_dump) intenable ; pgBackRest ne recopie que les
# blocs modifies depuis la derniere sauvegarde pour un "incr", quel que
# soit le nombre ou la taille des bases individuelles.
#
# Retention geree nativement par pgBackRest (repo1-retention-full-type=time,
# repo1-retention-full=90 - voir /etc/pgbackrest.conf, pose par le postinst
# de ce paquet) : un "full" et tous les "incr" qui en dependent expirent
# ensemble 90 jours apres la prise du full, jamais avant qu'un full plus
# recent existe deja - pas de purge manuelle a coder ici.
#
# Si aucun "full" n'existe encore dans le depot (premiere installation en
# cours de mois, ou depot NFS injoignable lors du 1er precedent),
# pgBackRest bascule automatiquement une demande d'"incr" en "full" - rien
# a gerer explicitement ici pour ce cas.
set -e

STANZA="sillon"

if [ "$(date +%d)" = "01" ]; then
    TYPE="full"
else
    TYPE="incr"
fi

echo "Sauvegarde SILLON ($TYPE) : $(date '+%Y-%m-%d %H:%M:%S')"

if pgbackrest --stanza="$STANZA" --type="$TYPE" backup; then
    echo "Succes : sauvegarde $TYPE terminee."
else
    echo "Erreur : echec de la sauvegarde $TYPE." >&2
    exit 1
fi

exit 0
