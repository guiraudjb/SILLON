"""SILLON - Tutoriel, corrige de l'exercice Python 2.8.

Reprend le modele de exemple_2.8_regression_statsmodels_seaborn.py, mais
au niveau de la commune plutot que du departement (moyenne) : identifie
les 5 communes les plus sous-estimees et les 5 plus sur-estimees par le
modele, et trace la distribution complete des residus avec seaborn.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2
import seaborn as sns
import statsmodels.formula.api as smf

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT nom_standard, dep_nom, population, superficie_km2, densite, altitude_moyenne "
    "FROM communes_france",
    connexion,
)
connexion.close()
communes = communes.dropna(subset=["population", "superficie_km2", "densite", "altitude_moyenne"])
communes = communes[communes["population"] > 0].copy()
communes["log_population"] = np.log(communes["population"])

modele = smf.ols("log_population ~ densite + altitude_moyenne + superficie_km2", data=communes).fit()
communes["residu"] = modele.resid

extremes = pd.concat([
    communes.nsmallest(5, "residu")[["nom_standard", "dep_nom", "population", "densite", "superficie_km2", "residu"]],
    communes.nlargest(5, "residu")[["nom_standard", "dep_nom", "population", "densite", "superficie_km2", "residu"]],
])
extremes.to_csv(os.path.join(resultats, "communes_extremes.csv"), index=False)
print(extremes.to_string(index=False))

figure, axe = plt.subplots(figsize=(7, 5))
sns.histplot(communes["residu"], bins=80, ax=axe, color="#0055a4")
axe.axvline(0, color="#c9191e", linestyle="--")
axe.set_xlabel("Residu (log population reelle - log population predite)")
axe.set_title("Distribution des residus du modele")
figure.savefig(os.path.join(resultats, "distribution_residus.png"), dpi=120, bbox_inches="tight")

# Piege reel rencontre en ecrivant cet exercice : exponentiel un residu de
# -18 (Arles, superficie 758 km2 - la plus grande commune de France
# metropolitaine, tres loin de la superficie typique de quelques km2 sur
# laquelle le modele a surtout appris) donnerait une "population predite"
# de plusieurs milliers de milliards d'habitants - un nombre absurde, pas
# une erreur de calcul. Un coefficient lineaire (superficie_km2 ou
# densite) extrapole sans limite en dehors de la plage de valeurs sur
# laquelle il a ete estime : le residu en log (ci-dessus) reste
# interpretable, mais population_predite = exp(valeur_ajustee) ne l'est
# plus pour les communes les plus atypiques. D'ou l'absence volontaire
# d'une colonne "population predite" en unites reelles dans ce corrige.
print(
    f"\nEcart-type des residus : {communes['residu'].std():.2f} "
    "(a comparer aux valeurs extremes ci-dessus, bien au-dela de quelques ecarts-types)."
)
