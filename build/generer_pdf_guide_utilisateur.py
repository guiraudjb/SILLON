#!/usr/bin/env python3
"""Régénère le PDF du guide utilisateur à partir de sa source Markdown.

Convention du projet : Markdown -> document LibreOffice Writer (.odt,
intermédiaire jetable) -> PDF, via pandoc puis "soffice --headless"
(voir _pdf_via_odt.py). La source Markdown reste l'unique source de
vérité : jamais éditée dans LibreOffice directement.

Nécessite les paquets système "pandoc" et "libreoffice".

Usage : ./generer_pdf_guide_utilisateur.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _pdf_via_odt import markdown_vers_pdf

ICI = Path(__file__).parent
RACINE = ICI.parent
SOURCE_MD = RACINE / "GUIDE_UTILISATEUR_SILLON.md"
IMAGES_DIR = ICI / "sillon-server/var/www/html/SILLON/Documentation/archives/images-guide"
PDF_CIBLE = ICI / "sillon-server/var/www/html/SILLON/Documentation/Guide Utilisateur SILLON.pdf"


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")
    if not IMAGES_DIR.is_dir():
        sys.exit(f"Répertoire des captures introuvable : {IMAGES_DIR}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")
    markdown_vers_pdf(corps_md, PDF_CIBLE, repertoire_ressources=IMAGES_DIR, titre="Guide Utilisateur SILLON")

    print(f"PDF régénéré : {PDF_CIBLE} ({PDF_CIBLE.stat().st_size} octets)")


if __name__ == "__main__":
    main()
