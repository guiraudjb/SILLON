"""SILLON - Tutoriel, corrigé de l'exercice Python 2.2.

Nuage de points population/superficie des communes d'un département,
avec une échelle logarithmique sur les deux axes.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

DEPARTEMENT = "75"  # à adapter : code du département étudié

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT nom_standard, population, superficie_km2 FROM communes_france WHERE dep_code = %(dep)s",
    connexion, params={"dep": DEPARTEMENT},
)
connexion.close()

figure, axe = plt.subplots(figsize=(7, 6))
axe.scatter(communes["superficie_km2"], communes["population"], alpha=0.6, color="#000091")
axe.set_xscale("log")
axe.set_yscale("log")
axe.set_xlabel("Superficie (km², échelle log)")
axe.set_ylabel("Population (échelle log)")
axe.set_title(f"Population / superficie — département {DEPARTEMENT}")
figure.savefig(os.path.join(resultats, "population_vs_superficie.png"), bbox_inches="tight")

print(f"{len(communes)} commune(s) tracée(s) pour le département {DEPARTEMENT}.")
