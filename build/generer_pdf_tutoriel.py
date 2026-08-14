#!/usr/bin/env python3
"""Régénère le PDF du tutoriel sillon-tutoriel à partir de sa source Markdown.

Convention du projet : Markdown -> document LibreOffice Writer (.odt,
intermédiaire jetable) -> PDF, via pandoc puis "soffice --headless"
(voir _pdf_via_odt.py). La source Markdown reste l'unique source de
vérité : jamais éditée dans LibreOffice directement.

Nécessite les paquets système "pandoc" et "libreoffice".

Usage : ./generer_pdf_tutoriel.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _pdf_via_odt import markdown_vers_pdf

ICI = Path(__file__).parent
SOURCE_MD = ICI / "sillon-tutoriel/usr/share/doc/sillon-tutoriel/archives/tutoriel.md"
# Racine de résolution des chemins relatifs ("images/xxx.png") tels
# qu'écrits dans le Markdown - le dossier des images lui-même, un niveau
# plus bas, sinon pandoc chercherait "images/images/xxx.png".
RACINE_RESSOURCES = ICI / "sillon-tutoriel/usr/share/doc/sillon-tutoriel/archives"
PDF_CIBLE = ICI / "sillon-tutoriel/usr/share/doc/sillon-tutoriel/Tutoriel SILLON.pdf"


def preparer_html_brut(corps_md):
    """Le writer ODT de pandoc ignore le HTML brut (contrairement à HTML,
    cible d'origine de ce document) : les <details>/<summary> utilisés
    pour les corrigés repliables deviendraient invisibles, pas seulement
    dépliés comme c'était déjà le cas pour le PDF via Chrome. Convertis en
    un simple intitulé en gras. La seule balise <img> brute du document
    (légende + largeur réduite pour une capture déjà rognée) est convertie
    en syntaxe Markdown avant l'ajout générique de largeur (_pdf_via_odt),
    qui ne touche jamais une image ayant déjà des attributs."""
    corps_md = re.sub(r"<details open><summary>([^<]+)</summary>", r"**\1**\n", corps_md)
    corps_md = corps_md.replace("</details>", "")
    corps_md = re.sub(
        r'<img src="([^"]+)" alt="([^"]+)" style="max-width:220px">',
        r"![\2](\1){width=6cm}",
        corps_md,
    )
    return corps_md


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")
    corps_md = preparer_html_brut(corps_md)
    markdown_vers_pdf(corps_md, PDF_CIBLE, repertoire_ressources=RACINE_RESSOURCES, titre="Tutoriel SILLON")

    print(f"PDF régénéré : {PDF_CIBLE} ({PDF_CIBLE.stat().st_size} octets)")


if __name__ == "__main__":
    main()
