"""SILLON - Script Python d'exemple : rapport PDF multi-pages (sillon-demo-sirene).

matplotlib.backends.backend_pdf.PdfPages assemble plusieurs figures dans
un seul fichier PDF (page de garde texte, puis une figure par page) - les
requêtes restent agrégées côté PostgreSQL comme dans les autres scripts de
ce paquet, jamais un SELECT * sur les ~43,9 millions de lignes.
"""
import os
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from matplotlib.backends.backend_pdf import PdfPages

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)

curseur = connexion.cursor()
curseur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE etat_administratif = 'A') FROM sirene_etablissements")
total, actifs = curseur.fetchone()

par_annee = pd.read_sql("""
    SELECT EXTRACT(YEAR FROM date_creation)::int AS annee, COUNT(*) AS nb
    FROM sirene_etablissements WHERE date_creation >= '2000-01-01' GROUP BY annee ORDER BY annee
""", connexion)

top_departements = pd.read_sql("""
    SELECT dep_code, COUNT(*) AS nb FROM sirene_etablissements
    WHERE etat_administratif = 'A' AND dep_code != '' GROUP BY dep_code ORDER BY nb DESC LIMIT 10
""", connexion)
connexion.close()

chemin_pdf = os.path.join(resultats, "rapport_sirene.pdf")
with PdfPages(chemin_pdf) as pdf:
    figure_garde = plt.figure(figsize=(8.27, 11.69))  # A4 portrait
    figure_garde.text(0.5, 0.6, "Rapport Sirene", ha="center", fontsize=28, weight="bold")
    figure_garde.text(0.5, 0.52, f"Généré le {date.today().isoformat()}", ha="center", fontsize=12)
    figure_garde.text(
        0.5, 0.4,
        f"{total:,} établissements au total\n{actifs:,} établissements actifs".replace(",", " "),
        ha="center", fontsize=14,
    )
    pdf.savefig(figure_garde)
    plt.close(figure_garde)

    figure1, axe1 = plt.subplots(figsize=(8.27, 5))
    axe1.plot(par_annee["annee"], par_annee["nb"], color="#000091")
    axe1.set_title("Créations d'établissements par année (depuis 2000)")
    axe1.set_xlabel("Année")
    axe1.set_ylabel("Créations")
    pdf.savefig(figure1)
    plt.close(figure1)

    figure2, axe2 = plt.subplots(figsize=(8.27, 5))
    axe2.barh(top_departements["dep_code"][::-1], top_departements["nb"][::-1], color="#e1000f")
    axe2.set_title("10 départements les plus dotés en établissements actifs")
    pdf.savefig(figure2)
    plt.close(figure2)

print(f"Rapport PDF produit ({chemin_pdf}) : 3 pages, {total:,} établissements analysés.".replace(",", " "))
