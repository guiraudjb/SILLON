"""Aide partagée : Markdown -> document LibreOffice Writer (.odt) -> PDF.

Utilisée par les 4 scripts generer_pdf_*.py du projet. Remplace l'ancienne
convention (Markdown -> HTML -> Chrome headless) sur demande explicite :
la source Markdown reste l'unique source de vérité (jamais éditée dans
LibreOffice directement, qui ne produit ici qu'un fichier intermédiaire
jetable, régénéré à chaque build), mais l'export PDF passe désormais par
un vrai document LibreOffice Writer (.odt).

Nécessite les paquets système "pandoc" et "libreoffice" (commande
"soffice"), disponibles uniquement sur la machine de build - jamais sur
la cible de déploiement (cahier des charges §12.1).

Deux limites de pandoc 2.17 (Debian 13), contournées ici :
- Les images Markdown sans largeur explicite ({width=...}) sont
  intégrées à leur taille en pixels interprétée telle quelle en points,
  bien plus large qu'une page A4 - une largeur est donc injectée sur
  chaque référence d'image avant conversion (`preparer_images_markdown`).
  Les pourcentages ({width=90%}) n'ont aucun effet pour l'export .odt,
  seule une unité absolue (cm) fonctionne.
- Les cellules de tableau générées par le writer ODT de pandoc n'ont
  jamais de bordure ni de fond, quel que soit le document de référence
  utilisé (ce sont des styles automatiques par-document dans content.xml,
  pas hérités du modèle) - corrigé par une retouche du .odt déjà généré,
  avant son export en PDF (`corriger_bordures_tableaux`).
"""
import re
import subprocess
import zipfile
from pathlib import Path

MODELE_ODT = Path(__file__).parent / "modele-document-sillon.odt"

BLEU_DSFR = "#000091"

# Largeur d'image par défaut : légèrement en retrait de la largeur utile
# de la page (21cm - 2*1.8cm de marge = 17,4cm, cf. modele-document-sillon.odt)
# plutôt que pile dessus, pour laisser un léger espace visuel comme le
# faisait auparavant "max-width:100%" dans un conteneur déjà marginé.
LARGEUR_IMAGE_CM = 17


def preparer_images_markdown(corps_md, largeur_cm=LARGEUR_IMAGE_CM):
    """Ajoute {width=...cm} à chaque image Markdown qui n'a pas déjà
    d'attributs, pour contourner l'absence de mise à l'échelle
    automatique du writer ODT de pandoc (cf. docstring du module)."""
    return re.sub(
        r"(!\[[^\]]*\]\([^)]+\))(?!\{)",
        rf"\1{{width={largeur_cm}cm}}",
        corps_md,
    )


def corriger_bordures_tableaux(chemin_odt):
    """Injecte bordures + fond bleu DSFR sur l'en-tête, dans les styles de
    cellule automatiques que pandoc régénère à l'identique dans chaque
    document (TableHeaderRowCell / TableRowCell, cf. docstring du module).
    Ces deux noms sont réutilisés par pandoc pour toutes les tables d'un
    même document (vérifié empiriquement, pas juste la première)."""
    with zipfile.ZipFile(chemin_odt, "r") as zin:
        infos = zin.infolist()
        donnees = {info.filename: zin.read(info.filename) for info in infos}

    contenu = donnees["content.xml"].decode("utf-8")
    contenu = re.sub(
        r'(<style:style style:name="TableHeaderRowCell"[^>]*>\s*'
        r'<style:table-cell-properties )fo:border="none"( */>)',
        rf'\1fo:border="0.5pt solid {BLEU_DSFR}" fo:background-color="{BLEU_DSFR}"\2',
        contenu,
    )
    contenu = re.sub(
        r'(<style:style style:name="TableRowCell"[^>]*>\s*'
        r'<style:table-cell-properties )fo:border="none"( */>)',
        r'\1fo:border="0.5pt solid #cccccc"\2',
        contenu,
    )
    donnees["content.xml"] = contenu.encode("utf-8")

    with zipfile.ZipFile(chemin_odt, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in infos:
            # mimetype doit rester STORED (non compressé) en 1er membre,
            # exigence du format ODF (sinon document jugé invalide par
            # certains lecteurs, cf. même contrainte déjà rencontrée en
            # construisant modele-document-sillon.odt).
            compression = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            zout.writestr(info, donnees[info.filename], compress_type=compression)


def markdown_vers_pdf(corps_md, pdf_cible, repertoire_ressources=None, titre=None):
    """Convertit une chaîne Markdown en PDF, via un .odt intermédiaire.

    Le .odt est conservé à côté du PDF (même nom, extension différente) -
    document LibreOffice Writer réellement consultable/modifiable, pas un
    fichier de travail jetable comme l'était le HTML de l'ancienne
    convention. La source Markdown reste néanmoins l'unique source de
    vérité : ce .odt est entièrement régénéré (écrasé) à chaque exécution
    de ce script, jamais lu ni fusionné - toute modification faite
    directement dedans serait perdue au prochain "generer_pdf_*.py"."""
    corps_md = preparer_images_markdown(corps_md)

    pdf_cible = Path(pdf_cible)
    chemin_odt = pdf_cible.with_suffix(".odt")

    commande_pandoc = [
        "pandoc", "-f", "markdown", "-t", "odt",
        f"--reference-doc={MODELE_ODT}",
        "-o", str(chemin_odt),
    ]
    if repertoire_ressources:
        commande_pandoc.append(f"--resource-path={repertoire_ressources}")
    if titre:
        commande_pandoc += ["--metadata", f"title={titre}"]

    subprocess.run(commande_pandoc, input=corps_md, check=True, capture_output=True, text=True)
    corriger_bordures_tableaux(chemin_odt)
    subprocess.run(
        [
            "soffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(pdf_cible.parent), str(chemin_odt),
        ],
        check=True, capture_output=True, text=True,
    )
    chemin_odt.with_suffix(".pdf").rename(pdf_cible)
