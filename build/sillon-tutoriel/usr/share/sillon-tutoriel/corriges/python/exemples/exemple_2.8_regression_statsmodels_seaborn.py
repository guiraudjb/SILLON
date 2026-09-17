"""SILLON - Script Python d'exemple : regression statistique avec statsmodels,
visualisation avec seaborn (formation avancee, tutoriel).

A la difference de exemple_2.7_typologie_scikit_learn.py (apprentissage NON
supervise, aucune valeur cible), ce script apprend une relation entre une
valeur cible connue (la population, en log) et trois variables explicatives
(densite, altitude moyenne, superficie). statsmodels, contrairement a
scikit-learn, fournit directement les tests statistiques (p-values,
intervalles de confiance) sur chaque coefficient - plus adapte a une
question d'inference ("cette variable a-t-elle un effet significatif ?")
qu'a la seule prediction.

Contrat d'execution (cahier des charges §5.4, worker.py) : chaine de
connexion et repertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'execution (§7.7)
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
    "SELECT nom_standard, dep_code, dep_nom, population, superficie_km2, densite, altitude_moyenne "
    "FROM communes_france",
    connexion,
)
connexion.close()
communes = communes.dropna(subset=["population", "superficie_km2", "densite", "altitude_moyenne"])

# Population en log : la population brute est tres asymetrique (de
# quelques habitants a plus de deux millions pour Paris) - une regression
# lineaire directe sur la population serait dominee par une poignee de
# grandes villes. Le log ramene la variable a une echelle ou la majorite
# des 34 868 communes pese effectivement dans l'ajustement.
communes = communes[communes["population"] > 0].copy()
communes["log_population"] = np.log(communes["population"])

# smf.ols() (API "formule", a la R) plutot que sm.OLS() bas niveau : plus
# lisible, et evite de construire soi-meme la matrice de conception avec
# la colonne de 1 pour l'ordonnee a l'origine.
modele = smf.ols("log_population ~ densite + altitude_moyenne + superficie_km2", data=communes).fit()

with open(os.path.join(resultats, "regression_population.txt"), "w") as f:
    f.write(str(modele.summary()))
print(modele.summary())

# --- Visualisations seaborn ---
figure_correlation, axe = plt.subplots(figsize=(6, 5))
correlation = communes[["log_population", "densite", "altitude_moyenne", "superficie_km2"]].corr()
sns.heatmap(correlation, annot=True, fmt=".2f", cmap="vlag", center=0, ax=axe)
axe.set_title("Correlations (population, densite, altitude, superficie)")
figure_correlation.savefig(os.path.join(resultats, "correlations.png"), dpi=120, bbox_inches="tight")

# Piege reel rencontre en ecrivant ce script : un premier essai tracait le
# nuage/ajustement de regplot() en echelle lineaire puis appliquait
# set_xscale("log") apres coup sur l'axe - la droite de regression
# ajustee en espace lineaire se retrouvait deformee en courbe apparemment
# exponentielle une fois l'axe reetire en log, un artefact purement
# visuel qui n'a rien a voir avec le modele statsmodels ci-dessus.
# logx=True corrige cela en ajustant directement sur log(densite), ce qui
# correspond a ce que l'echelle log de l'axe donne a voir.
echantillon = communes.sample(n=min(5000, len(communes)), random_state=0)
figure_regression, axe2 = plt.subplots(figsize=(7, 5))
sns.regplot(
    data=echantillon, x="densite", y="log_population", ax=axe2, logx=True,
    scatter_kws={"s": 6, "alpha": 0.4}, line_kws={"color": "#c9191e"},
)
axe2.set_xscale("log")
axe2.set_xlabel("Densite (hab/km2, echelle log)")
axe2.set_ylabel("log(population)")
axe2.set_title("Population (log) en fonction de la densite")
figure_regression.savefig(os.path.join(resultats, "regression_densite.png"), dpi=120, bbox_inches="tight")

# Residu moyen par departement : ou le modele (fonde uniquement sur la
# geographie physique) sous- ou sur-estime le plus la population reelle.
communes["residu"] = modele.resid
residu_par_dep = (
    communes.groupby(["dep_code", "dep_nom"])["residu"].mean().reset_index().sort_values("residu")
)
residu_par_dep.to_csv(os.path.join(resultats, "residus_par_departement.csv"), index=False)

print(f"\nR2 = {modele.rsquared:.3f} sur {len(communes)} communes.")
print("Departements les plus sous-estimes par le modele :")
print(residu_par_dep.head(5).to_string(index=False))
print("Departements les plus sur-estimes par le modele :")
print(residu_par_dep.tail(5).to_string(index=False))
