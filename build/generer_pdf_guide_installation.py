#!/usr/bin/env python3
"""Régénère le PDF du guide d'installation administrateur à partir de sa source Markdown.

Convention du projet (cf. mémo de suivi) : Markdown -> HTML -> PDF via
Chrome headless, jamais LibreOffice (son filtre HTML avale le premier
élément du <body>). Nécessite le module Python "markdown"
(python3-markdown) et google-chrome.

Usage : ./generer_pdf_guide_installation.py
"""
import subprocess
import sys
from pathlib import Path

import markdown

ICI = Path(__file__).parent
RACINE = ICI.parent
SOURCE_MD = RACINE / "GUIDE_INSTALLATION_ADMINISTRATEUR.md"
PDF_CIBLE = ICI / "sillon-server/var/www/html/SILLON/Documentation/Guide Administrateur SILLON.pdf"
HTML_TEMPORAIRE = ICI / ".guide-installation-generation.html"

STYLE = """
  @page { size: A4; margin: 20mm 18mm; }
  body { font-family: Marianne, Arial, sans-serif; color: #1e1e1e; line-height: 1.5; font-size: 10.5pt; }
  h1 { color: #000091; font-size: 20pt; margin-bottom: 4pt; }
  h2 { color: #000091; font-size: 15pt; border-bottom: 2px solid #000091; padding-bottom: 3pt; margin-top: 20pt; page-break-after: avoid; }
  h3 { color: #000091; font-size: 12.5pt; margin-top: 14pt; page-break-after: avoid; }
  h4 { color: #1e1e1e; font-size: 11pt; margin-top: 12pt; page-break-after: avoid; }
  hr { border: none; border-top: 1px solid #ddd; margin: 12pt 0; }
  code { background: #f0f0f0; padding: 1pt 3pt; border-radius: 2pt; font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; word-break: break-word; }
  pre { background: #f6f6f6; border-left: 3px solid #000091; padding: 8pt 10pt; page-break-inside: avoid;
        white-space: pre-wrap; word-break: break-word; font-size: 8.5pt; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9.5pt; }
  th, td { border: 1px solid #ccc; padding: 4pt 7pt; text-align: left; }
  th { background: #000091; color: white; }
  strong { color: #000091; }
  a { color: #000091; }
"""


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")
    corps_html = markdown.markdown(corps_md, extensions=["tables", "fenced_code"])

    page = f"""<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Guide d'installation administrateur SILLON</title><style>{STYLE}</style></head>
<body>
{corps_html}
</body>
</html>
"""
    HTML_TEMPORAIRE.write_text(page, encoding="utf-8")

    try:
        subprocess.run(
            [
                "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                f"--print-to-pdf={PDF_CIBLE}", "--no-pdf-header-footer",
                str(HTML_TEMPORAIRE),
            ],
            check=True, capture_output=True, text=True,
        )
    finally:
        HTML_TEMPORAIRE.unlink(missing_ok=True)

    print(f"PDF régénéré : {PDF_CIBLE} ({PDF_CIBLE.stat().st_size} octets)")


if __name__ == "__main__":
    main()
