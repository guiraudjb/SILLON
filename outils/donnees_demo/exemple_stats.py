"""SILLON - Script Python d'exemple pour le compte de démonstration (§5.4).

Calcule quelques statistiques descriptives sur la table "communes_exemple"
(données fictives, cf. communes_exemple.csv) et dépose les résultats dans
le répertoire de sortie mis à disposition par SILLON.

Contrat d'exécution (cahier des charges §5.4, worker.py) : ce script reçoit
sa chaîne de connexion et son répertoire de sortie exclusivement via les
variables d'environnement posées par sillon-worker, jamais en dur.
"""
import os

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'exécution (§7.7)
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

dsn = os.environ["SILLON_DSN"]
repertoire_resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql("SELECT * FROM communes_exemple", connexion)
connexion.close()

resume = (
    communes.groupby("region_exemple")
    .agg(
        nb_communes=("identifiant", "count"),
        population_totale=("population", "sum"),
        superficie_moyenne_km2=("superficie_km2", "mean"),
    )
    .round(1)
    .sort_values("population_totale", ascending=False)
)
resume.to_csv(os.path.join(repertoire_resultats, "resume_par_region.csv"))

top5 = communes.sort_values("population", ascending=False).head(5)
figure, axe = plt.subplots(figsize=(8, 5))
axe.bar(top5["nom_commune"], top5["population"], color="#000091")  # bleu France (DSFR)
axe.set_ylabel("Population")
axe.set_title("Communes exemple les plus peuplées")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
figure.savefig(os.path.join(repertoire_resultats, "top5_population.png"))

print(f"{len(communes)} commune(s) analysée(s) - résumé écrit dans resume_par_region.csv")
