#!/bin/bash
# ==============================================================================
# OUTIL DE RESTAURATION - SILLON (pgBackRest)
# ==============================================================================
# Restauration physique de tout le cluster PostgreSQL (catalogue SILLON
# et l'ensemble des bases de travail des agents) a une sauvegarde choisie
# dans une liste numerotee (la plus recente en tete). pgBackRest resout
# lui-meme la chaine necessaire (le dernier "full" dont depend la
# sauvegarde choisie, puis chaque "incr"/"diff" intermediaire jusqu'a
# elle) - rien a choisir manuellement au-dela du numero de ligne,
# contrairement a une restauration pg_dump classique ou l'administrateur
# doit designer lui-meme le fichier exact a rejouer.
#
# Duree : aucune limite n'est imposee par ce script, a aucune etape (copie
# des fichiers, rejeu des journaux). Une restauration peut legitimement
# prendre plusieurs heures selon la volumetrie du cluster (plusieurs
# centaines de Mo par base agent, potentiellement de nombreux agents) - un
# abandon premature laisserait le cluster dans un etat intermediaire sans
# raison de l'interrompre alors qu'il progresse reellement.
set -e

STANZA="sillon"
SECRETS_FILE="/etc/sillon/secrets.env"
API_CONF="/etc/sillon-api.conf"
DB_NAME="sillon_catalog"

PG_VERSION=$(pg_lsclusters -h 2>/dev/null | awk 'NR==1{print $1}')
PG_VERSION="${PG_VERSION:-17}"

if [ "$EUID" -ne 0 ]; then
    echo -e "\e[31mErreur : ce script doit etre execute en root (arret/demarrage du cluster PostgreSQL).\e[0m"
    exit 1
fi

echo -e "\n\e[1;34m=== OUTIL DE RESTAURATION DE LA BASE SILLON ===\e[0m\n"

INFO_JSON=$(mktemp)
trap 'rm -f "$INFO_JSON"' EXIT
if ! pgbackrest --stanza="$STANZA" --output=json info > "$INFO_JSON" 2>/dev/null; then
    echo -e "\e[31mErreur : impossible d'interroger pgBackRest (stanza \"$STANZA\").\e[0m" >&2
    exit 1
fi

# La liste (label/type/date de fin/etat), une sauvegarde par ligne, la plus
# recente en tete - pgBackRest ne trie pas forcement dans cet ordre en JSON,
# d'ou le tri explicite ici plutot que de se fier a l'ordre du tableau.
LIGNES=$(python3 - "$STANZA" "$INFO_JSON" <<'PYEOF'
import json
import sys
from datetime import datetime, timezone

stanza = sys.argv[1]
with open(sys.argv[2], encoding="utf-8") as fichier:
    donnees = json.load(fichier)
correspondantes = [s for s in donnees if s.get("name") == stanza]
sauvegardes = correspondantes[0].get("backup", []) if correspondantes else []
sauvegardes.sort(key=lambda b: b["timestamp"]["stop"], reverse=True)
for b in sauvegardes:
    fin = datetime.fromtimestamp(b["timestamp"]["stop"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    etat = "ERREUR" if b.get("error") else "ok"
    print(f"{b['label']}\t{b['type']}\t{fin}\t{etat}")
PYEOF
)

if [ -z "$LIGNES" ]; then
    echo -e "\e[31mAucune sauvegarde disponible pour la stanza \"$STANZA\".\e[0m" >&2
    exit 1
fi

echo "Sauvegardes disponibles (de la plus recente a la plus ancienne) :"
echo "-----------------------------------------------------------------"
printf "  %-4s %-11s %-21s %s\n" "N°" "Type" "Terminee le (UTC)" "Etat"
declare -a ETIQUETTES
i=1
while IFS=$'\t' read -r etiquette type fin etat; do
    ETIQUETTES[i]="$etiquette"
    if [ "$etat" = "ERREUR" ]; then
        printf "  \e[1;31m%-4s %-11s %-21s %s\e[0m\n" "$i" "$type" "$fin" "$etat"
    else
        printf "  %-4s %-11s %-21s %s\n" "$i" "$type" "$fin" "$etat"
    fi
    i=$((i+1))
done <<< "$LIGNES"
echo "-----------------------------------------------------------------"

read -rp $'\nNumero de la sauvegarde a restaurer : ' CHOIX
if ! [[ "$CHOIX" =~ ^[0-9]+$ ]] || [ -z "${ETIQUETTES[$CHOIX]:-}" ]; then
    echo "Annule : selection invalide."
    exit 0
fi
CIBLE="${ETIQUETTES[$CHOIX]}"

echo -e "\n\e[1;31m/!\\ ATTENTION /!\\\e[0m Restauration de l'ensemble du cluster SILLON"
echo -e "(catalogue et toutes les bases agents) a l'etat de la sauvegarde n°${CHOIX} : \e[1m${CIBLE}\e[0m"
echo "pgBackRest rejouera automatiquement la sauvegarde complete et toutes les"
echo "sauvegardes incrementales dont elle depend."
echo "Toute modification posterieure a cette sauvegarde sera definitivement perdue."
read -rp "Confirmer ? (Tapez OUI) : " CONFIRM
if [ "$CONFIRM" != "OUI" ]; then echo "Annule."; exit 0; fi

echo -e "\nArret des services applicatifs..."
systemctl stop sillon-worker sillon-orchestrateur sillon-api 2>/dev/null || true

echo "Arret du cluster PostgreSQL..."
pg_ctlcluster "$PG_VERSION" main stop

echo "Restauration en cours - la duree depend de la volumetrie du cluster,"
echo "cela peut prendre de quelques minutes a plusieurs heures. Progression :"
# --delta : ne recopie que les fichiers dont le contenu differe de la
# sauvegarde restauree, plutot que d'exiger un PGDATA prealablement vide -
# adapte a une restauration en place par-dessus un cluster deja existant.
# --set : restaure precisement la sauvegarde choisie (pgBackRest resout
# seul la chaine full/incr necessaire), plutot qu'une cible temporelle -
# correspond au choix par numero de ligne ci-dessus, pas par date/heure.
# --type=immediate : s'arrete au premier point coherent de CETTE
# sauvegarde (ne rejoue pas de journaux au-dela) - l'administrateur a
# choisi une ligne precise dans la liste, la restauration doit s'arreter
# exactement la, ni avant ni apres.
# --target-action=promote : le comportement par defaut ("pause") laisserait
# l'instance indefiniment en lecture seule en attente d'une commande
# manuelle - ici la restauration doit aboutir a un service reellement
# redemarre, pas a une instance figee en recuperation.
# --log-level-console=detail : affiche la progression fichier par fichier
# de la phase de copie (silencieuse par defaut au niveau "info") - seule
# indication de progression disponible pendant cette phase, potentiellement
# la plus longue pour un cluster volumineux.
if ! pgbackrest --stanza="$STANZA" --set="$CIBLE" --type=immediate --target-action=promote \
        --log-level-console=detail --delta restore; then
    echo -e "\n\e[1;31m=== ECHEC DE LA RESTAURATION ===\e[0m"
    echo "Le cluster PostgreSQL n'a pas ete redemarre - verifier l'etat de PGDATA avant toute nouvelle tentative."
    exit 1
fi

echo "Redemarrage du cluster PostgreSQL (rejeu des journaux jusqu'au point coherent choisi)..."
pg_ctlcluster "$PG_VERSION" main start

# Attente sans limite de duree (voir l'entete de ce script) : le seul
# critere d'arret est la fin reelle de la recuperation, jamais un delai
# ecoule. Indication de progression a chaque tour : dernier LSN rejoue
# (change tant que la recuperation avance reellement, meme sans que
# "pg_is_in_recovery()" ait encore bascule) et duree ecoulee.
echo "Attente de la fin du rejeu des journaux (aucune limite de duree)..."
DEBUT=$(date +%s)
DERNIER_LSN=""
ETAT=""
while true; do
    ETAT=$(sudo -u postgres psql -tAc "SELECT pg_is_in_recovery();" -d "$DB_NAME" 2>/dev/null || true)
    if [ "$ETAT" = "f" ]; then
        break
    fi
    LSN=$(sudo -u postgres psql -tAc "SELECT pg_last_wal_replay_lsn();" -d "$DB_NAME" 2>/dev/null || true)
    ECOULE=$(( $(date +%s) - DEBUT ))
    if [ -n "$LSN" ] && [ "$LSN" != "$DERNIER_LSN" ]; then
        echo "  [${ECOULE}s] rejeu en cours - dernier journal rejoue : $LSN"
        DERNIER_LSN="$LSN"
    else
        echo "  [${ECOULE}s] rejeu en cours..."
    fi
    sleep 5
done
echo -e "\e[1;32m=== RESTAURATION TERMINEE ===\e[0m"

# Resynchronisation des secrets applicatifs entre la base restauree et ce
# serveur. Necessaire aussi bien pour une restauration en place que pour
# une restauration sur une installation neuve (reconstruction apres
# sinistre) : sillon-server genere a l'installation un JWT_SECRET et des
# mots de passe de role (SILLON_SERVICE_PASS, SILLON_ORCHESTRATEUR_PASS)
# aleatoires et propres a CETTE installation (postinst, "Aucune
# installation existante") - une restauration physique par-dessus ecrase
# entierement PGDATA, y compris pg_authid (les mots de passe reels des
# roles PostgreSQL), avec les valeurs de la sauvegarde d'ORIGINE.
#
# Deux directions differentes selon le secret :
# - JWT : login() (schema.sql) signe avec la valeur stockee dans
#   auth.secrets (DB restauree) -> il faut faire suivre cette valeur DANS
#   les fichiers locaux (secrets.env, api.conf), sans quoi PostgREST
#   verifierait les jetons avec l'ancien secret local et rejetterait toute
#   connexion (signature invalide).
# - Mots de passe de connexion (sillon_service pour PostgREST,
#   sillon_orchestrateur pour l'orchestrateur ET sillon-worker) : ce sont
#   de vrais mots de passe de role PostgreSQL, jamais stockes en clair
#   dans la base (hashes dans pg_authid, non exploitables). Sens inverse
#   du JWT : c'est le mot de passe LOCAL (secrets.env, deja correct pour
#   les fichiers de conf de CETTE machine) qui doit etre reimpose au role
#   fraichement restaure, via ALTER ROLE. Sans cette etape, une
#   restauration sur une installation neuve laisse PostgREST et
#   l'orchestrateur avec un mot de passe qui ne correspond plus au role
#   reellement present apres restauration - authentification refusee,
#   interface web inaccessible, sans rapport avec le rejeu des journaux
#   ci-dessus.
if [ ! -f "$SECRETS_FILE" ]; then
    echo -e "\e[1;31mATTENTION : ${SECRETS_FILE} introuvable - impossible de resynchroniser les"
    echo -e "secrets. Verifier manuellement avant de redemarrer les services.\e[0m"
else
    # shellcheck disable=SC1090
    source "$SECRETS_FILE"

    echo "Synchronisation du secret JWT (base restauree -> fichiers locaux)..."
    JWT_FROM_DB=$(sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT valeur FROM auth.secrets WHERE cle = 'jwt_secret';" 2>/dev/null || true)
    if [ -n "$JWT_FROM_DB" ]; then
        sed -i "s|^SILLON_JWT_SECRET=.*|SILLON_JWT_SECRET=${JWT_FROM_DB}|" "$SECRETS_FILE"
        if [ -f "$API_CONF" ]; then
            sed -i "s|^jwt-secret = .*|jwt-secret = \"${JWT_FROM_DB}\"|" "$API_CONF"
        fi
        echo -e "\e[1;32mSecret JWT synchronise.\e[0m"
    else
        echo -e "\e[1;31mATTENTION : impossible de lire le secret JWT depuis la base restauree - verifier"
        echo -e "manuellement ${SECRETS_FILE} et ${API_CONF}.\e[0m"
    fi

    echo "Synchronisation des mots de passe de connexion (fichiers locaux -> roles restaures)..."
    if [ -n "${SILLON_SERVICE_PASS:-}" ]; then
        sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 \
            -c "ALTER ROLE sillon_service WITH PASSWORD '${SILLON_SERVICE_PASS}';" >/dev/null
    else
        echo -e "\e[1;31mATTENTION : SILLON_SERVICE_PASS absent de ${SECRETS_FILE}.\e[0m"
    fi
    if [ -n "${SILLON_ORCHESTRATEUR_PASS:-}" ]; then
        sudo -u postgres psql -d "$DB_NAME" -v ON_ERROR_STOP=1 \
            -c "ALTER ROLE sillon_orchestrateur WITH PASSWORD '${SILLON_ORCHESTRATEUR_PASS}';" >/dev/null
    else
        echo -e "\e[1;31mATTENTION : SILLON_ORCHESTRATEUR_PASS absent de ${SECRETS_FILE}.\e[0m"
    fi
    echo -e "\e[1;32mMots de passe de connexion resynchronises.\e[0m"
fi

echo "Redemarrage des services applicatifs..."
systemctl start sillon-api sillon-orchestrateur sillon-worker 2>/dev/null || true

echo -e "\e[1;32m=== SILLON restaure et services redemarres ===\e[0m"
exit 0
