#!/bin/bash
# ==============================================================================
# OUTIL DE RESTAURATION - SILLON (pgBackRest)
# ==============================================================================
# Restauration physique de tout le cluster PostgreSQL (catalogue SILLON
# et l'ensemble des bases de travail des agents) a un instant choisi.
# pgBackRest determine lui-meme la chaine necessaire (le dernier "full"
# a la date visee, puis chaque "incr" intermediaire, puis rejeu des
# journaux archives jusqu'a la seconde demandee) - rien a choisir
# manuellement au-dela de la date/heure cible, contrairement a une
# restauration pg_dump classique ou l'administrateur doit designer
# lui-meme le fichier exact a rejouer.
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
echo "Sauvegardes disponibles (pgBackRest) :"
echo "--------------------------------------------------------"
pgbackrest --stanza="$STANZA" info
echo "--------------------------------------------------------"

read -rp $'\nDate/heure cible de restauration (format "AAAA-MM-JJ HH:MM:SS") : ' CIBLE
if [ -z "$CIBLE" ]; then
    echo "Annule : aucune date saisie."
    exit 0
fi

echo -e "\n\e[1;31m/!\\ ATTENTION /!\\\e[0m Restauration de l'ensemble du cluster SILLON"
echo -e "(catalogue et toutes les bases agents) a l'etat du : \e[1m$CIBLE\e[0m"
echo "Toute modification posterieure a cette date sera definitivement perdue."
read -rp "Confirmer ? (Tapez OUI) : " CONFIRM
if [ "$CONFIRM" != "OUI" ]; then echo "Annule."; exit 0; fi

echo -e "\nArret des services applicatifs..."
systemctl stop sillon-worker sillon-orchestrateur sillon-api 2>/dev/null || true

echo "Arret du cluster PostgreSQL..."
pg_ctlcluster "$PG_VERSION" main stop

echo "Restauration en cours (peut prendre plusieurs minutes selon le volume de journaux a rejouer)..."
# --delta : ne recopie que les fichiers dont le contenu differe de la
# sauvegarde restauree, plutot que d'exiger un PGDATA prealablement vide -
# adapte a une restauration en place par-dessus un cluster deja existant.
# --target-action=promote : le comportement par defaut ("pause") laisserait
# l'instance indefiniment en lecture seule en attente d'une commande
# manuelle - ici la restauration doit aboutir a un service reellement
# redemarre, pas a une instance figee en recuperation.
if ! pgbackrest --stanza="$STANZA" --type=time --target="$CIBLE" --target-action=promote --delta restore; then
    echo -e "\n\e[1;31m=== ECHEC DE LA RESTAURATION ===\e[0m"
    echo "Le cluster PostgreSQL n'a pas ete redemarre - verifier l'etat de PGDATA avant toute nouvelle tentative."
    exit 1
fi

echo "Redemarrage du cluster PostgreSQL (rejeu des journaux jusqu'a la cible)..."
pg_ctlcluster "$PG_VERSION" main start

echo -n "Attente de la fin du rejeu des journaux"
ETAT=""
for _ in $(seq 1 60); do
    ETAT=$(sudo -u postgres psql -tAc "SELECT pg_is_in_recovery();" -d "$DB_NAME" 2>/dev/null || true)
    if [ "$ETAT" = "f" ]; then
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

if [ "$ETAT" != "f" ]; then
    echo -e "\e[1;31mLe cluster est toujours en recuperation apres 2 minutes d'attente - verifier"
    echo -e "/var/log/postgresql/postgresql-${PG_VERSION}-main.log avant de continuer.\e[0m"
    exit 1
fi

echo -e "\e[1;32m=== RESTAURATION TERMINEE ===\e[0m"

# Resynchronisation du secret JWT entre la base restauree et les services
# applicatifs (meme necessite que pour TRACE) : sans cette etape, login()
# (schema.sql) signe les jetons avec le secret contenu dans la sauvegarde
# restauree, alors que PostgREST et les services Python continuent de
# verifier avec l'ancien secret lu dans /etc/sillon/secrets.env - toute
# authentification echouerait silencieusement (signature invalide) des
# lors que la restauration ramene le cluster a un instant ou le secret
# differait de l'actuel.
echo "Synchronisation du secret JWT..."
JWT_FROM_DB=$(sudo -u postgres psql -d "$DB_NAME" -tAc "SELECT valeur FROM auth.secrets WHERE cle = 'jwt_secret';" 2>/dev/null || true)
if [ -n "$JWT_FROM_DB" ]; then
    if [ -f "$SECRETS_FILE" ]; then
        sed -i "s|^SILLON_JWT_SECRET=.*|SILLON_JWT_SECRET=${JWT_FROM_DB}|" "$SECRETS_FILE"
    fi
    if [ -f "$API_CONF" ]; then
        sed -i "s|^jwt-secret = .*|jwt-secret = \"${JWT_FROM_DB}\"|" "$API_CONF"
    fi
    echo -e "\e[1;32mSecret JWT synchronise.\e[0m"
else
    echo -e "\e[1;31mATTENTION : impossible de lire le secret JWT depuis la base restauree - verifier"
    echo -e "manuellement ${SECRETS_FILE} et ${API_CONF}.\e[0m"
fi

echo "Redemarrage des services applicatifs..."
systemctl start sillon-api sillon-orchestrateur sillon-worker 2>/dev/null || true

echo -e "\e[1;32m=== SILLON restaure et services redemarres ===\e[0m"
exit 0
