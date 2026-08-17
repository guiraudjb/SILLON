#!/bin/sh
# SILLON - Attend que l'hôte ait une route de sortie IPv4 utilisable avant
# de laisser PostgreSQL démarrer (ExecStartPre de postgresql@.service, cf.
# le drop-in systemd installé par le postinst de ce paquet).
#
# Pourquoi : le postinst de sillon-worker configure listen_addresses avec
# l'adresse LAN de l'hôte (§7.7, nécessaire aux conteneurs de script) - un
# réglage à contexte "postmaster" qui n'a d'effet qu'au démarrage de
# PostgreSQL. Sur une interface "allow-hotplug" en DHCP (cas courant d'une
# VM), le service PostgreSQL peut démarrer avant que l'adresse ne soit
# effectivement configurée : constaté en pratique, network-online.target
# est atteint dès la fin de "networking.service" (ifup -a des interfaces
# "auto"), sans attendre le bail DHCP d'une interface hotplug distincte -
# PostgreSQL se lie alors seulement à "localhost", plus du tout à l'IP
# LAN, sans erreur bloquante (juste un avertissement dans son journal) :
# tous les scripts Python/R échouent alors à joindre leur base jusqu'au
# prochain redémarrage manuel de PostgreSQL.
#
# Ne fait jamais échouer le démarrage de PostgreSQL : au pire (délai
# dépassé), il démarre comme avant ce correctif - dégradé mais pas bloqué,
# cohérent avec le reste du projet (un problème de configuration réseau ne
# doit jamais empêcher le service applicatif de démarrer).
i=0
while [ "$i" -lt 30 ]; do
    if ip -4 route get 1.1.1.1 2>/dev/null | grep -q 'src '; then
        exit 0
    fi
    i=$((i + 1))
    sleep 1
done
exit 0
