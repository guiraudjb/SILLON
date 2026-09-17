"""SILLON - Script Python d'exemple : typologie des communes par apprentissage
non supervise avec scikit-learn (formation avancee, tutoriel).

Regroupe les 34 868 communes en quatre profils (clusters) a partir de trois
caracteristiques physiques - densite, altitude moyenne, superficie - sans
aucune etiquette de depart (apprentissage NON supervise, a la difference
d'une regression comme exemple_2.8_regression_statsmodels_seaborn.py, qui
apprend a partir d'une valeur cible connue). Utile pour une segmentation
exploratoire (typologie de territoires) plutot qu'une prediction.

Contrat d'execution (cahier des charges §5.4, worker.py) : chaine de
connexion et repertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'execution (§7.7)
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT code_insee, nom_standard, dep_code, reg_nom, population, "
    "superficie_km2, densite, altitude_moyenne FROM communes_france",
    connexion,
)
connexion.close()
communes = communes.dropna(subset=["densite", "altitude_moyenne", "superficie_km2"])

# StandardScaler est indispensable ici : sans lui, la densite (jusqu'a
# ~25 000 hab/km2) ecraserait completement l'altitude (jusqu'a ~2 500 m)
# et la superficie (quelques km2 a plusieurs centaines) dans le calcul de
# distance de KMeans - trois echelles trop differentes pour etre comparees
# telles quelles.
CARACTERISTIQUES = ["densite", "altitude_moyenne", "superficie_km2"]
echelle = StandardScaler()
X = echelle.fit_transform(communes[CARACTERISTIQUES])

# k=4 choisi par la methode du coude (cf. exercice 2.7, qui la met en
# oeuvre et confirme ce choix sur ce meme jeu de donnees) plutot que pose
# arbitrairement ici.
K = 4
modele = KMeans(n_clusters=K, random_state=0, n_init=10)
communes["cluster"] = modele.fit_predict(X)

profil = (
    communes.groupby("cluster")[CARACTERISTIQUES + ["population"]]
    .mean()
    .round(1)
    .assign(nb_communes=communes["cluster"].value_counts())
    .sort_values("densite", ascending=False)
)
print(profil)

# Nuage densite/altitude colore par cluster, sur un echantillon (34 868
# points superposes rendraient le nuage illisible). La superficie (3e
# caracteristique du clustering) n'apparait pas dans ce plan 2D : deux
# clusters proches en densite/altitude mais separes surtout par la
# superficie (communes "standards" vs "grandes communes rurales", cf.
# tutoriel.md) s'y chevauchent visuellement - un vrai angle mort de toute
# projection 2D d'un clustering fait sur plus de deux dimensions, pas un
# defaut du clustering lui-meme.
echantillon = communes.sample(n=min(6000, len(communes)), random_state=0)
figure, axe = plt.subplots(figsize=(8, 6))
nuage = axe.scatter(
    echantillon["densite"], echantillon["altitude_moyenne"], c=echantillon["cluster"],
    cmap="tab10", s=6, alpha=0.6,
)
axe.set_xscale("log")
axe.set_xlabel("Densite (hab/km2, echelle log)")
axe.set_ylabel("Altitude moyenne (m)")
axe.set_title(f"Typologie des communes par KMeans (k={K})")
figure.colorbar(nuage, ax=axe, label="Cluster")
figure.savefig(os.path.join(resultats, "typologie_communes.png"), dpi=120, bbox_inches="tight")

figure_effectifs, axe2 = plt.subplots(figsize=(6, 4))
communes["cluster"].value_counts().sort_index().plot(kind="bar", ax=axe2, color="#0055a4")
axe2.set_xlabel("Cluster")
axe2.set_ylabel("Nombre de communes")
axe2.set_title("Effectif par cluster")
figure_effectifs.savefig(os.path.join(resultats, "effectifs_clusters.png"), dpi=120, bbox_inches="tight")

communes[["code_insee", "nom_standard", "dep_code", "reg_nom"] + CARACTERISTIQUES + ["cluster"]].sort_values(
    ["cluster", "code_insee"]
).to_csv(os.path.join(resultats, "typologie_communes.csv"), index=False)
profil.to_csv(os.path.join(resultats, "profil_clusters.csv"))

print(f"\n{len(communes)} communes reparties en {K} clusters (inertie intra-cluster : {modele.inertia_:.1f}).")
