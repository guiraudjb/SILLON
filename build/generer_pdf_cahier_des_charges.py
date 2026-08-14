#!/usr/bin/env python3
"""Régénère le PDF du cahier des charges à partir de sa source Markdown.

Convention du projet : Markdown -> document LibreOffice Writer (.odt,
intermédiaire jetable) -> PDF, via pandoc puis "soffice --headless"
(voir _pdf_via_odt.py). La source Markdown reste l'unique source de
vérité : jamais éditée dans LibreOffice directement. Les diagrammes
Mermaid sont rendus en images via mermaid-cli (npx @mermaid-js/mermaid-cli),
jamais laissés en bloc de code source brut dans le PDF publié (le writer
ODT de pandoc les aurait de toute façon ignorés, tout code brut Mermaid
non rendu) - les sources .mmd restent archivées à part
(Documentation/archives/diagrammes-source/) pour régénération future.

Usage : ./generer_pdf_cahier_des_charges.py
Prérequis : pandoc, libreoffice, npx (mermaid-cli récupéré à la volée -
accès réseau nécessaire sur la machine de build, jamais sur la cible,
cf. §12.1 du cahier des charges lui-même).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _pdf_via_odt import markdown_vers_pdf

ICI = Path(__file__).parent
RACINE = ICI.parent
SOURCE_MD = RACINE / "SILLON_cahier_des_charges.md"
DOC_DIR = ICI / "sillon-server/var/www/html/SILLON/Documentation"
ANCIEN_PDF_GLOB = "Cahier des charges SILLON v*.pdf"
ANCIEN_ODT_GLOB = "Cahier des charges SILLON v*.odt"


def rendre_diagrammes_mermaid(corps_md, repertoire_images):
    """Remplace chaque bloc ```mermaid par une image PNG rendue (mermaid-cli),
    en syntaxe Markdown (chemin absolu, largeur explicite) plutôt qu'en
    <img> HTML brut - le writer ODT de pandoc ignore tout HTML brut."""
    compteur = 0

    def remplacer(correspondance):
        nonlocal compteur
        compteur += 1
        source_mermaid = correspondance.group(1)
        chemin_mmd = repertoire_images / f"diagramme_{compteur}.mmd"
        chemin_png = repertoire_images / f"diagramme_{compteur}.png"
        chemin_mmd.write_text(source_mermaid, encoding="utf-8")

        print(f"Rendu du diagramme {compteur}...")
        subprocess.run(
            [
                "npx", "--yes", "-p", "@mermaid-js/mermaid-cli", "mmdc",
                "-i", str(chemin_mmd), "-o", str(chemin_png),
                "-b", "white", "-s", "3",
            ],
            check=True, capture_output=True, text=True,
        )
        return f"\n\n![Diagramme {compteur}]({chemin_png}){{width=16cm}}\n\n"

    return re.sub(r"```mermaid\n(.*?)```", remplacer, corps_md, flags=re.DOTALL)


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")

    # Version publiée : lue directement dans le tableau d'en-tête du
    # document plutôt que dupliquée en dur ici (une seule source de
    # vérité, cf. cahier des charges §1 - même principe que les secrets
    # jamais dupliqués §12.3).
    correspondance_version = re.search(r"\|\s*Version\s*\|\s*([\d.]+)\s*\|", corps_md)
    if not correspondance_version:
        sys.exit("Version introuvable dans l'en-tête du document.")
    version = correspondance_version.group(1)
    nom_pdf = f"Cahier des charges SILLON v{version}.pdf"
    pdf_cible = DOC_DIR / nom_pdf

    with tempfile.TemporaryDirectory() as repertoire_temp:
        repertoire_images = Path(repertoire_temp)
        corps_md = rendre_diagrammes_mermaid(corps_md, repertoire_images)

        # Anciennes versions retirées avant génération de la nouvelle,
        # pour ne jamais publier deux PDF "Cahier des charges" à des
        # numéros de version différents en même temps (.odt inclus, sinon
        # laissé orphelin - constaté en pratique après un premier passage
        # de ce script qui ne purgeait que le PDF).
        for ancien in list(DOC_DIR.glob(ANCIEN_PDF_GLOB)) + list(DOC_DIR.glob(ANCIEN_ODT_GLOB)):
            ancien.unlink()

        markdown_vers_pdf(corps_md, pdf_cible, titre="Cahier des charges SILLON")

    print(f"PDF régénéré : {pdf_cible} ({pdf_cible.stat().st_size} octets)")


if __name__ == "__main__":
    main()
