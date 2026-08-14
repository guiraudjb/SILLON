"""SILLON - Tutoriel, corrigé de l'exercice Python 2.3.

Assemble trois graphiques du panorama (2.1 : barres, camembert,
histogramme) dans un seul rapport PDF avec PdfPages.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from matplotlib.backends.backend_pdf import PdfPages

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql("SELECT reg_nom, population, densite FROM communes_france", connexion)
connexion.close()

par_region = communes.groupby("reg_nom")["population"].sum().sort_values(ascending=False)
top5_regions = par_region.head(5)

with PdfPages(os.path.join(resultats, "panorama_trois_graphiques.pdf")) as pdf:
    figure1, axe1 = plt.subplots(figsize=(8, 6))
    axe1.barh(par_region.index[::-1], par_region.values[::-1], color="#000091")
    axe1.set_title("Population totale par région")
    pdf.savefig(figure1, bbox_inches="tight")
    plt.close(figure1)

    figure2, axe2 = plt.subplots(figsize=(6, 6))
    axe2.pie(top5_regions.values, labels=top5_regions.index, autopct="%1.1f%%")
    axe2.set_title("Part des 5 régions les plus peuplées")
    pdf.savefig(figure2, bbox_inches="tight")
    plt.close(figure2)

    figure3, axe3 = plt.subplots(figsize=(8, 6))
    axe3.hist(communes["densite"].dropna(), bins=50, color="#e1000f")
    axe3.set_title("Distribution de la densité des communes")
    axe3.set_xlabel("Densité (hab/km²)")
    pdf.savefig(figure3, bbox_inches="tight")
    plt.close(figure3)

print("Rapport PDF produit : 3 pages (barres, camembert, histogramme).")
