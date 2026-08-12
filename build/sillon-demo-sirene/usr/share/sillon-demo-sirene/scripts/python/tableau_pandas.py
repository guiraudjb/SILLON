"""SILLON - Script Python d'exemple : tableau croisé pandas (sillon-demo-sirene).

Construit un tableau croisé (nombre d'établissements actifs par
département x tranche d'effectif) avec pandas.pivot_table, à partir d'une
requête déjà agrégée côté PostgreSQL (jamais un SELECT * sur les ~43,9
millions de lignes de sirene_etablissements, cf. graphiques_couverture.py).
Exporté à la fois en CSV et en image (rendu de tableau via matplotlib,
utile quand le résultat doit être consulté sans tableur).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
brut = pd.read_sql("""
    SELECT dep_code, COALESCE(NULLIF(tranche_effectifs, ''), 'NR') AS tranche, COUNT(*) AS nb
    FROM sirene_etablissements
    WHERE etat_administratif = 'A' AND dep_code IN (
        SELECT dep_code FROM (
            SELECT dep_code, COUNT(*) AS total FROM sirene_etablissements
            WHERE etat_administratif = 'A' GROUP BY dep_code ORDER BY total DESC LIMIT 12
        ) plus_peuples
    )
    GROUP BY dep_code, tranche
""", connexion)
connexion.close()

tableau = pd.pivot_table(brut, index="dep_code", columns="tranche", values="nb", aggfunc="sum", fill_value=0)
tableau["total"] = tableau.sum(axis=1)
tableau = tableau.sort_values("total", ascending=False)

tableau.to_csv(os.path.join(resultats, "tableau_croise_departements.csv"))

figure, axe = plt.subplots(figsize=(12, 0.5 * len(tableau) + 1.5))
axe.axis("off")
rendu = axe.table(
    cellText=tableau.reset_index().values,
    colLabels=["Département"] + list(tableau.columns),
    cellLoc="center", loc="center",
)
rendu.auto_set_font_size(False)
rendu.set_fontsize(8)
rendu.scale(1, 1.4)
axe.set_title("12 départements les plus dotés en établissements actifs, par tranche d'effectif", pad=20)
figure.tight_layout()
figure.savefig(os.path.join(resultats, "tableau_croise_departements.png"), dpi=120, bbox_inches="tight")

print(f"Tableau croisé : {tableau.shape[0]} départements x {tableau.shape[1] - 1} tranches d'effectif.")
