"""SILLON - Tutoriel, corrigé de l'exercice Python 2.3.

Corrélation entre altitude moyenne et densité, calculée pour chaque
région : les régions de montagne sont-elles significativement moins
denses ?
"""
import os

import pandas as pd
import psycopg2

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql("SELECT reg_nom, altitude_moyenne, densite FROM communes_france", connexion)
connexion.close()

correlations = (
    communes.dropna(subset=["altitude_moyenne", "densite"])
    .groupby("reg_nom")
    .apply(lambda g: g["altitude_moyenne"].corr(g["densite"]))
    .sort_values()
)
correlations.to_csv(os.path.join(resultats, "correlation_altitude_densite.csv"), header=["correlation"])

print("Corrélation altitude/densité par région (valeurs négatives = montagne moins dense) :")
print(correlations)
