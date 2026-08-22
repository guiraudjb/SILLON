#!/bin/bash
# =====================================================================
# SCRIPT DE CONSTRUCTION DES PAQUETS DEBIAN - SILLON
# Voir cahier des charges §12.2 à 12.5.
# =====================================================================
set -e

cd "$(dirname "$0")"

PAQUETS=(sillon-server sillon-orchestrateur sillon-worker sillon-image-execution sillon-tutoriel sillon-demo-sirene sillon-purge sillon-backup-client sillon-backup-server sillon-backup-server-survey)

POSTGREST_VERSION="14.8"
POSTGREST_SHA256="172a55aebcee6d7be2c3ea16476fca69a215afcd68d3d1849b7555878909f0b0"
POSTGREST_URL="https://github.com/PostgREST/postgrest/releases/download/v${POSTGREST_VERSION}/postgrest-v${POSTGREST_VERSION}-linux-static-x86-64.tar.xz"

echo "=== Construction des paquets SILLON ==="

# Vendoring du binaire PostgREST officiel (§12.2) : /usr/lib/sillon/postgrest
# devait jusqu'ici être placé manuellement (cf. sillon-server/usr/lib/sillon/
# README.md) - un paquet ainsi construit s'installait mais son service API
# ne démarrait jamais (ExecStart introuvable), constaté lors du premier
# test de déploiement réel sur VM. Le binaire est statiquement lié : aucune
# dépendance supplémentaire à installer sur la cible.
CACHE_DIR="${SILLON_BUILD_CACHE:-/tmp/sillon-build-cache}"
mkdir -p "$CACHE_DIR"
archive="$CACHE_DIR/postgrest-v${POSTGREST_VERSION}-linux-static-x86-64.tar.xz"
if [ ! -f "$archive" ] || [ "$(sha256sum "$archive" | cut -d' ' -f1)" != "$POSTGREST_SHA256" ]; then
    echo "--- Téléchargement de PostgREST v${POSTGREST_VERSION} ---"
    curl -sL -o "$archive" "$POSTGREST_URL"
fi
somme_obtenue=$(sha256sum "$archive" | cut -d' ' -f1)
if [ "$somme_obtenue" != "$POSTGREST_SHA256" ]; then
    echo "ERREUR : somme SHA256 de PostgREST invalide (attendu $POSTGREST_SHA256, obtenu $somme_obtenue)." >&2
    exit 1
fi
tar -xf "$archive" -C "$CACHE_DIR" postgrest
# Pas de -o/-g ici : dpkg-deb --root-owner-group (plus bas) remappe déjà
# la propriété à root:root dans le .deb final, et ce script tourne sans
# privilèges root.
install -m 755 "$CACHE_DIR/postgrest" "sillon-server/usr/lib/sillon/postgrest"

# Construction et vendoring de l'image d'exécution des scripts (§8.7) : le
# serveur cible n'a accès qu'aux dépôts Debian via son proxy d'entreprise,
# jamais à un registre de conteneurs (Docker Hub) - "podman build" au
# postinst (essayé lors d'un premier test de déploiement réel) y échoue
# donc systématiquement. L'image est construite une fois ici, là où
# l'accès réseau est disponible, puis exportée en archive et embarquée
# dans le paquet ; le postinst se contente d'un "podman load" purement
# local, sans aucun accès réseau requis sur la cible.
OUTIL_CONTENEURS="podman"
OPTIONS_BUILD=()
if ! command -v podman >/dev/null 2>&1; then
    if command -v docker >/dev/null 2>&1; then
        echo "AVERTISSEMENT : podman introuvable sur cette machine de build, substitution par docker." >&2
        echo "(le format d'archive produit par \"docker save\" reste chargeable par \"podman load\" sur la cible.)" >&2
        OUTIL_CONTENEURS="docker"
        # BuildKit enveloppe par defaut l'image dans un index de
        # provenance/attestation (docker build > 23) : "podman load" ne sait
        # pas le deplier et charge une image vide/inutilisable sur la cible,
        # sans erreur au chargement - la panne ne se voit qu'au premier
        # "podman run" (constate en pratique, 2026-08-19, image d'apparence
        # correcte mais conteneur ne demarrant jamais, aucune sortie
        # capturee). Sans objet pour "podman build", qui ne produit pas ces
        # attestations.
        OPTIONS_BUILD=(--provenance=false --sbom=false)
    else
        echo "ERREUR : ni podman ni docker disponibles pour construire l'image d'exécution." >&2
        exit 1
    fi
fi

echo ""
echo "--- Construction de l'image d'exécution (sillon-image-execution) ---"
IMAGE_TAG="sillon-image-execution:latest"
"$OUTIL_CONTENEURS" build "${OPTIONS_BUILD[@]}" -t "$IMAGE_TAG" sillon-image-execution/opt/sillon-image-execution
mkdir -p "sillon-image-execution/usr/lib/sillon"
"$OUTIL_CONTENEURS" save -o "sillon-image-execution/usr/lib/sillon/image-execution.tar" "$IMAGE_TAG"
# "docker/podman save -o" écrit avec un umask restrictif (0600) : sans
# correction, lintian le signale (non-standard-file-perm) et le fichier
# resterait illisible pour quiconque hors du compte de build une fois
# décompressé manuellement pour inspection.
chmod 644 "sillon-image-execution/usr/lib/sillon/image-execution.tar"

for paquet in "${PAQUETS[@]}"; do
    if [ ! -d "$paquet/DEBIAN" ]; then
        echo "ERREUR : $paquet/DEBIAN introuvable." >&2
        exit 1
    fi

    # Les scripts de maintenance doivent être exécutables (§12.2) : un
    # "git clone" mal configuré ou une extraction d'archive peut perdre ce
    # bit - on le réaffirme systématiquement plutôt que de découvrir
    # l'échec seulement au moment de l'installation sur la cible.
    for script in preinst postinst prerm postrm; do
        if [ -f "$paquet/DEBIAN/$script" ]; then
            chmod 755 "$paquet/DEBIAN/$script"
        fi
    done

    # __pycache__ généré par une exécution/un test local de orchestrateur.py
    # ou worker.py ne doit jamais se retrouver embarqué dans le paquet
    # (constaté en pratique : lintian package-installs-python-pycache-dir).
    find "$paquet" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    # "dpkg-deb --field" lit un .deb déjà construit, pas un répertoire
    # source : on extrait la version directement du fichier control.
    version=$(sed -n 's/^Version:[[:space:]]*//p' "$paquet/DEBIAN/control")
    if [ -z "$version" ]; then
        echo "ERREUR : impossible de lire la version de $paquet (DEBIAN/control)." >&2
        exit 1
    fi
    architecture=$(sed -n 's/^Architecture:[[:space:]]*//p' "$paquet/DEBIAN/control")

    sortie="${paquet}_${version}_${architecture:-all}.deb"
    echo ""
    echo "--- $paquet ($version) ---"

    # --root-owner-group : les fichiers appartiennent à root:root dans le
    # paquet final, indépendamment de l'utilisateur qui construit (§12.2) -
    # sans ça, un paquet construit par un compte non-root embarquerait cet
    # UID/GID de construction, incohérent une fois installé sur la cible.
    dpkg-deb --build --root-owner-group "$paquet" "$sortie"

    if command -v lintian >/dev/null 2>&1; then
        lintian "$sortie" || true
    fi
done

echo ""
echo "=== Construction terminée : $(ls -1 -- *_all.deb *_amd64.deb 2>/dev/null | wc -l) paquet(s) produit(s) dans $(pwd) ==="
