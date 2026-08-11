Le binaire officiel PostgREST est vendorisé ici par build.sh (téléchargé
depuis la release GitHub officielle, vérifié par somme SHA256). Voir
cahier des charges §12.2.

Placé sous /usr/lib/sillon/ plutôt que /usr/local/bin/ : la Debian Policy
(§9.1.2) réserve /usr/local/ à l'administrateur système local, jamais à un
fichier livré par un paquet .deb (détecté par lintian : dir-in-usr-local).
