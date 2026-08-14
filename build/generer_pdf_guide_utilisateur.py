#!/usr/bin/env python3
"""Régénère le PDF du guide utilisateur à partir de sa source Markdown.

Convention du projet (cf. mémo de suivi) : Markdown -> HTML -> PDF via
Chrome headless, jamais LibreOffice (son filtre HTML avale le premier
élément du <body>). Nécessite le module Python "markdown"
(python3-markdown) et google-chrome.

Les captures d'écran référencées par la source Markdown (noms de fichier
nus, ex. "01_connexion.jpg") vivent dans Documentation/archives/images-guide/
- le HTML intermédiaire est généré dans ce même répertoire pour que ces
chemins relatifs se résolvent correctement au moment de l'impression.

Usage : ./generer_pdf_guide_utilisateur.py
"""
import subprocess
import sys
from pathlib import Path

import markdown

ICI = Path(__file__).parent
RACINE = ICI.parent
SOURCE_MD = RACINE / "GUIDE_UTILISATEUR_SILLON.md"
IMAGES_DIR = ICI / "sillon-server/var/www/html/SILLON/Documentation/archives/images-guide"
PDF_CIBLE = ICI / "sillon-server/var/www/html/SILLON/Documentation/Guide Utilisateur SILLON.pdf"
HTML_TEMPORAIRE = IMAGES_DIR / ".guide-utilisateur-generation.html"

STYLE = """
  @page { size: A4; margin: 20mm 18mm; }
  body { font-family: Marianne, Arial, sans-serif; color: #1e1e1e; line-height: 1.5; font-size: 10.5pt; }
  h1 { color: #000091; font-size: 20pt; margin-bottom: 4pt; }
  h2 { color: #000091; font-size: 15pt; border-bottom: 2px solid #000091; padding-bottom: 3pt; margin-top: 20pt; page-break-after: avoid; }
  h3 { color: #1e1e1e; font-weight: normal; font-size: 12pt; margin-top: 0; }
  h3:not(:first-of-type) { color: #000091; font-size: 12.5pt; margin-top: 14pt; page-break-after: avoid; }
  hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }
  code { background: #f0f0f0; padding: 1pt 3pt; border-radius: 2pt; font-family: "DejaVu Sans Mono", monospace; font-size: 9.5pt; word-break: break-word; }
  pre { background: #f6f6f6; border-left: 3px solid #000091; padding: 8pt 10pt; page-break-inside: avoid;
        white-space: pre-wrap; word-break: break-word; font-size: 9pt; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 10pt; }
  th, td { border: 1px solid #ccc; padding: 4pt 8pt; text-align: left; }
  th { background: #000091; color: white; }
  blockquote { border-left: 3px solid #b34000; background: #fef4e5; margin: 8pt 0; padding: 6pt 10pt; }
  strong { color: #000091; }
  a { color: #000091; }
  /* Captures d'écran réelles : bordure légère pour les distinguer du texte
     courant, et un plafond de hauteur pour ne jamais forcer un saut de
     page pour une seule image (cf. tutoriel, même piège déjà rencontré). */
  img { display: block; max-width: 100%; max-height: 170mm; height: auto; margin: 10pt auto;
        border: 1px solid #ccc; border-radius: 3pt; page-break-inside: avoid; }
"""


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")
    if not IMAGES_DIR.is_dir():
        sys.exit(f"Répertoire des captures introuvable : {IMAGES_DIR}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")
    corps_html = markdown.markdown(corps_md, extensions=["tables", "fenced_code"])

    page = f"""<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Guide Utilisateur SILLON</title><style>{STYLE}</style></head>
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
