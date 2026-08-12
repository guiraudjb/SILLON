#!/usr/bin/env python3
"""Régénère le PDF du cahier des charges à partir de sa source Markdown.

Convention du projet (cf. mémo de suivi) : Markdown -> HTML -> PDF via
Chrome headless, jamais LibreOffice (son filtre HTML avale le premier
élément du <body>). Les diagrammes Mermaid sont rendus en images via
mermaid-cli (npx @mermaid-js/mermaid-cli), jamais laissés en bloc de code
source brut dans le PDF publié - les sources .mmd restent archivées à
part (Documentation/archives/diagrammes-source/) pour régénération
future.

Usage : ./generer_pdf_cahier_des_charges.py
Prérequis : python3-markdown, google-chrome, npx (mermaid-cli récupéré à
la volée - accès réseau nécessaire sur la machine de build, jamais sur la
cible, cf. §12.1 du cahier des charges lui-même).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

ICI = Path(__file__).parent
RACINE = ICI.parent
SOURCE_MD = RACINE / "SILLON_cahier_des_charges.md"
DOC_DIR = ICI / "sillon-server/var/www/html/SILLON/Documentation"
DIAGRAMMES_ARCHIVE = DOC_DIR / "archives/diagrammes-source"
ANCIEN_PDF_GLOB = "Cahier des charges SILLON v*.pdf"

STYLE = """
  @page { size: A4; margin: 20mm 18mm; }
  body { font-family: Marianne, Arial, sans-serif; color: #1e1e1e; line-height: 1.5; font-size: 10.5pt; }
  h1 { color: #000091; font-size: 20pt; margin-bottom: 4pt; }
  h2 { color: #000091; font-size: 15pt; border-bottom: 2px solid #000091; padding-bottom: 3pt; margin-top: 20pt; page-break-after: avoid; }
  h3 { color: #000091; font-size: 12.5pt; margin-top: 14pt; page-break-after: avoid; }
  h3:first-of-type { color: #1e1e1e; font-weight: normal; font-size: 12pt; margin-top: 0; }
  hr { border: none; border-top: 1px solid #ddd; margin: 12pt 0; }
  code { background: #f0f0f0; padding: 1pt 3pt; border-radius: 2pt; font-family: "DejaVu Sans Mono", monospace; font-size: 9pt; word-break: break-word; }
  pre { background: #f6f6f6; border-left: 3px solid #000091; padding: 8pt 10pt; page-break-inside: avoid;
        white-space: pre-wrap; word-break: break-word; font-size: 8.5pt; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; width: 100%; margin: 8pt 0; font-size: 9.5pt; }
  th, td { border: 1px solid #ccc; padding: 4pt 7pt; text-align: left; }
  th { background: #000091; color: white; }
  img.diagramme { display: block; max-width: 100%; margin: 10pt auto; page-break-inside: avoid; }
  strong { color: #000091; }
  a { color: #000091; }
"""


def rendre_diagrammes_mermaid(corps_md, repertoire_images):
    """Remplace chaque bloc ```mermaid par une image PNG rendue (mermaid-cli),
    jamais laissée en bloc de code brut dans le PDF publié."""
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
        return f'\n\n<img class="diagramme" src="{chemin_png.as_uri()}" alt="Diagramme {compteur}">\n\n'

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
        corps_html = markdown.markdown(corps_md, extensions=["tables", "fenced_code"])

        page = f"""<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Cahier des charges SILLON</title><style>{STYLE}</style></head>
<body>
{corps_html}
</body>
</html>
"""
        html_temporaire = repertoire_images / "generation.html"
        html_temporaire.write_text(page, encoding="utf-8")

        # Anciennes versions retirées avant génération de la nouvelle,
        # pour ne jamais publier deux PDF "Cahier des charges" à des
        # numéros de version différents en même temps.
        for ancien in DOC_DIR.glob(ANCIEN_PDF_GLOB):
            ancien.unlink()

        subprocess.run(
            [
                "google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
                f"--print-to-pdf={pdf_cible}", "--print-to-pdf-no-header",
                str(html_temporaire),
            ],
            check=True, capture_output=True, text=True,
        )

    print(f"PDF régénéré : {pdf_cible} ({pdf_cible.stat().st_size} octets)")


if __name__ == "__main__":
    main()
