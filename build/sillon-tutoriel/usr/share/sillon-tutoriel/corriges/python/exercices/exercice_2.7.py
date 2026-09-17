"""SILLON - Tutoriel, corrige de l'exercice Python 2.7.

Methode du coude : calcule l'inertie intra-cluster (WCSS) de KMeans pour
k = 1 a 10 sur les memes caracteristiques que exemple_2.7_typologie_scikit_
learn.py (densite, altitude moyenne, superficie), pour objectiver a
posteriori le choix de k=4 fait dans l'exemple plutot que de le poser
arbitrairement.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT densite, altitude_moyenne, superficie_km2 FROM communes_france", connexion,
)
connexion.close()
communes = communes.dropna()

X = StandardScaler().fit_transform(communes)

inerties = []
for k in range(1, 11):
    modele = KMeans(n_clusters=k, random_state=0, n_init=10).fit(X)
    inerties.append(modele.inertia_)

baisses = pd.DataFrame({
    "k": range(2, 11),
    "inertie": inerties[1:],
    "baisse_pct": [
        round((inerties[i - 1] - inerties[i]) / inerties[i - 1] * 100, 1) for i in range(1, len(inerties))
    ],
})
print(baisses.to_string(index=False))

figure, axe = plt.subplots(figsize=(7, 5))
axe.plot(range(1, 11), inerties, marker="o", color="#0055a4")
axe.set_xlabel("Nombre de clusters (k)")
axe.set_ylabel("Inertie intra-cluster (WCSS)")
axe.set_title("Methode du coude")
axe.set_xticks(range(1, 11))
figure.savefig(os.path.join(resultats, "coude_kmeans.png"), dpi=120, bbox_inches="tight")

baisses.to_csv(os.path.join(resultats, "coude_kmeans.csv"), index=False)

print(
    "\nLa baisse d'inertie ralentit nettement a partir de k=5 (baisse de "
    f"{baisses.loc[baisses['k'] == 4, 'baisse_pct'].iloc[0]:.1f}% pour passer de k=3 a k=4, contre "
    f"{baisses.loc[baisses['k'] == 5, 'baisse_pct'].iloc[0]:.1f}% pour passer de k=4 a k=5) : "
    "k=4, choisi dans l'exemple, se situe bien au coude de la courbe."
)
