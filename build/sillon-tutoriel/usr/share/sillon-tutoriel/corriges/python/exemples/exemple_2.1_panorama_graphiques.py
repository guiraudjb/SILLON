"""SILLON - Script Python d'exemple (formation avancée, tutoriel).

Analyse démographique du jeu de données réel "communes_france" (INSEE/IGN,
via data.gouv.fr) : les 15 communes les plus peuplées, la population totale
par région, et la distribution de la densité de population.

Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
connexion et répertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'exécution (§7.7)
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql("SELECT * FROM communes_france", connexion)
connexion.close()

# 1. Top 15 des communes les plus peuplées
top15 = communes.nlargest(15, "population")
figure, axe = plt.subplots(figsize=(9, 6))
axe.barh(top15["nom_standard"][::-1], top15["population"][::-1], color="#000091")  # bleu France (DSFR)
axe.set_xlabel("Population")
axe.set_title("15 communes les plus peuplées de France")
plt.tight_layout()
figure.savefig(os.path.join(resultats, "top15_population.png"))
plt.close(figure)

# 2. Population totale par région
par_region = (
    communes.groupby("reg_nom")["population"].sum().sort_values(ascending=False)
)
figure, axe = plt.subplots(figsize=(10, 6))
axe.bar(par_region.index, par_region.values, color="#000091")
axe.set_ylabel("Population totale")
axe.set_title("Population par région")
plt.xticks(rotation=60, ha="right")
plt.tight_layout()
figure.savefig(os.path.join(resultats, "population_par_region.png"))
plt.close(figure)
par_region.to_csv(os.path.join(resultats, "population_par_region.csv"), header=["population_totale"])

# 3. Distribution de la densité (échelle logarithmique : très étalée, de
# quelques habitants/km2 en zone rurale à plusieurs milliers en ville dense)
densites = communes["densite"].dropna()
densites = densites[densites > 0]
figure, axe = plt.subplots(figsize=(8, 5))
# set_xscale("log") seul ne change que l'affichage de l'axe, pas le calcul
# des tranches de l'histogramme : avec des tranches par défaut (linéaires),
# la quasi-totalité des communes tombe dans une seule tranche qui, une fois
# affichée sur un axe log, semble occuper presque toute la largeur du
# graphique - constaté en pratique. Des tranches elles-mêmes espacées en
# log (np.logspace) donnent une répartition réellement lisible.
tranches_log = np.logspace(np.log10(densites.min()), np.log10(densites.max()), 50)
axe.hist(densites, bins=tranches_log, color="#000091")
axe.set_xscale("log")
axe.set_xlabel("Densité (hab/km², échelle logarithmique)")
axe.set_ylabel("Nombre de communes")
axe.set_title("Distribution de la densité de population")
plt.tight_layout()
figure.savefig(os.path.join(resultats, "distribution_densite.png"))
plt.close(figure)

print(f"{len(communes)} commune(s) analysée(s) sur {communes['reg_nom'].nunique()} région(s).")
print("Fichiers produits : top15_population.png, population_par_region.png/csv, distribution_densite.png")
