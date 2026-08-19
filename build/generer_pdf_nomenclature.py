#!/usr/bin/env python3
"""Régénère le PDF de la nomenclature logicielle (SBOM) à partir de sa
source Markdown.

Convention du projet : Markdown -> document LibreOffice Writer (.odt,
intermédiaire jetable) -> PDF, via pandoc puis "soffice --headless"
(voir _pdf_via_odt.py). La source Markdown reste l'unique source de
vérité : jamais éditée dans LibreOffice directement.

Document d'audit/conformité (nomenclature NIS2), pas une documentation
produit : le PDF est régénéré à la racine du dépôt, jamais embarqué dans
un paquet .deb (même logique que AUDIT_ACCESSIBILITE_RGAA.md, qui reste
en Markdown seul).

Nécessite les paquets système "pandoc" et "libreoffice".

Usage : ./generer_pdf_nomenclature.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _pdf_via_odt import markdown_vers_pdf

ICI = Path(__file__).parent
RACINE = ICI.parent
SOURCE_MD = RACINE / "NOMENCLATURE_LOGICIELLE_SILLON.md"
IMAGES_DIR = ICI / "nomenclature-ressources"
PDF_CIBLE = RACINE / "NOMENCLATURE_LOGICIELLE_SILLON.pdf"


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")
    if not IMAGES_DIR.is_dir():
        sys.exit(f"Répertoire des ressources introuvable : {IMAGES_DIR}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")
    markdown_vers_pdf(corps_md, PDF_CIBLE, repertoire_ressources=IMAGES_DIR, titre="Nomenclature logicielle SILLON (SBOM)")

    print(f"PDF régénéré : {PDF_CIBLE} ({PDF_CIBLE.stat().st_size} octets)")


if __name__ == "__main__":
    main()
