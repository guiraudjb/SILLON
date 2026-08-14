#!/usr/bin/env python3
"""Régénère le PDF du tutoriel sillon-tutoriel à partir de sa source Markdown.

Convention du projet (cf. mémo de suivi) : Markdown -> HTML -> PDF via
Chrome headless, jamais LibreOffice (son filtre HTML avale le premier
élément du <body>). Nécessite le module Python "markdown"
(python3-markdown) et google-chrome.

Usage : ./generer_pdf_tutoriel.py
"""
import subprocess
import sys
from pathlib import Path

import markdown

ICI = Path(__file__).parent
SOURCE_MD = ICI / "sillon-tutoriel/usr/share/doc/sillon-tutoriel/archives/tutoriel.md"
PDF_CIBLE = ICI / "sillon-tutoriel/usr/share/doc/sillon-tutoriel/Tutoriel SILLON.pdf"
HTML_TEMPORAIRE = ICI / "sillon-tutoriel/usr/share/doc/sillon-tutoriel/archives/.tutoriel-generation.html"

STYLE = """
  @page { size: A4; margin: 20mm 18mm; }
  body { font-family: Marianne, Arial, sans-serif; color: #1e1e1e; line-height: 1.5; font-size: 11pt; }
  h1 { color: #000091; font-size: 22pt; margin-bottom: 4pt; }
  h2 { color: #000091; font-size: 15pt; border-bottom: 2px solid #000091; padding-bottom: 3pt; margin-top: 22pt; page-break-after: avoid; }
  h3 { color: #1e1e1e; font-weight: normal; font-size: 12pt; margin-top: 0; }
  h3:not(:first-of-type) { color: #000091; font-size: 12.5pt; margin-top: 14pt; page-break-after: avoid; }
  hr { border: none; border-top: 1px solid #ddd; margin: 14pt 0; }
  code { background: #f0f0f0; padding: 1pt 3pt; border-radius: 2pt; font-family: "DejaVu Sans Mono", monospace; font-size: 9.5pt; word-break: break-word; }
  /* white-space: pre-wrap (pas overflow-x) : un PDF imprimé n'a pas de défilement possible,
     une ligne trop longue serait sinon coupée hors de la page, invisible et perdue. */
  pre { background: #f6f6f6; border-left: 3px solid #000091; padding: 8pt 10pt; page-break-inside: avoid;
        white-space: pre-wrap; word-break: break-word; font-size: 9pt; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 10pt; }
  th, td { border: 1px solid #ccc; padding: 4pt 8pt; text-align: left; }
  th { background: #000091; color: white; }
  /* <details open> (pas fermé) : un <details> fermé n'affiche rien à l'impression,
     un PDF statique ne peut pas être cliqué pour le déplier. */
  details { background: #f0f0fe; border: 1px solid #c9c9fb; border-radius: 3pt; padding: 6pt 10pt; margin: 6pt 0; page-break-inside: avoid; }
  summary { cursor: pointer; font-weight: bold; color: #000091; }
  blockquote { border-left: 3px solid #b34000; background: #fef4e5; margin: 8pt 0; padding: 6pt 10pt; }
  strong { color: #000091; }
  a { color: #000091; }
  /* Sans borne explicite, une image insérée à sa taille native (ex. une
     figure matplotlib sauvegardée à dpi=120) déborde largement la largeur
     utile de la page ou s'étire sur presque une page entière - constaté en
     pratique une fois les captures d'écran intégrées. max-height laisse de
     la place pour la légende/le texte qui suit sur la même page plutôt que
     de forcer un saut de page pour une seule image. */
  img { display: block; max-width: 100%; max-height: 200mm; height: auto; margin: 10pt auto; page-break-inside: avoid; }
"""


def main():
    if not SOURCE_MD.is_file():
        sys.exit(f"Source introuvable : {SOURCE_MD}")

    corps_md = SOURCE_MD.read_text(encoding="utf-8")
    corps_html = markdown.markdown(corps_md, extensions=["tables", "fenced_code"])

    page = f"""<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Tutoriel SILLON</title><style>{STYLE}</style></head>
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
                f"--print-to-pdf={PDF_CIBLE}", "--print-to-pdf-no-header",
                str(HTML_TEMPORAIRE),
            ],
            check=True, capture_output=True, text=True,
        )
    finally:
        HTML_TEMPORAIRE.unlink(missing_ok=True)

    print(f"PDF régénéré : {PDF_CIBLE} ({PDF_CIBLE.stat().st_size} octets)")


if __name__ == "__main__":
    main()
