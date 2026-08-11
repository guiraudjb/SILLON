L'image d'exécution (image-execution.tar) est construite par build.sh à
partir du Dockerfile voisin (../../opt/sillon-image-execution/Dockerfile)
et vendorisée ici avant l'empaquetage. Voir cahier des charges §8.7 et
§12.2.

Jamais construite sur la cible ("podman build" au postinst) : le serveur
de production n'a accès qu'aux dépôts Debian via son proxy d'entreprise,
jamais à un registre de conteneurs (Docker Hub) dont dépend le
"FROM debian:13-slim" du Dockerfile. Le postinst se limite à un
"podman load" purement local.
