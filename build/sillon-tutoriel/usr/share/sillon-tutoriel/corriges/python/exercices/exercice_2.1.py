"""SILLON - Tutoriel, corrigé de l'exercice Python 2.1.

Reproduit la carte de l'exemple `exemple_2.4_cartographie.py`, mais
coloriée par densité moyenne du département plutôt que par population
totale.
"""
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import pandas as pd
import psycopg2
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
densite_par_dep = (
    pd.read_sql(
        "SELECT dep_code, ROUND(AVG(densite)::numeric, 1) AS densite_moyenne FROM communes_france GROUP BY dep_code",
        connexion,
    )
    .set_index("dep_code")["densite_moyenne"]
    .to_dict()
)
contours = pd.read_sql(
    "SELECT dep_code, groupe, ordre, longitude, latitude FROM contours_departements ORDER BY dep_code, groupe, ordre",
    connexion,
)
connexion.close()

polygones = defaultdict(list)
for ligne in contours.itertuples():
    polygones[(ligne.dep_code, ligne.groupe)].append((ligne.longitude, ligne.latitude))

patches = [Polygon(points, closed=True) for (_dep_code, _groupe), points in polygones.items()]
couleurs = [densite_par_dep.get(dep_code, 0) for (dep_code, _groupe) in polygones]

figure, axe = plt.subplots(figsize=(8, 8))
# LogNorm plutôt que Normalize (linéaire) : la densité, contrairement à la
# population brute, est extrêmement asymétrique d'un département à l'autre
# (~20 000 hab/km² à Paris contre 15-30 dans un département rural, un
# facteur 1000) - une échelle linéaire écrase alors tous les départements
# sauf Paris dans le premier centième de la palette de couleurs, qui
# paraissent tous blancs (constaté en pratique). L'échelle logarithmique
# donne un contraste réel sur toute la gamme de valeurs.
collection = PatchCollection(
    patches, array=couleurs, cmap=cm.get_cmap("Blues"),
    norm=mcolors.LogNorm(vmin=max(min(couleurs), 0.1), vmax=max(couleurs)),
    edgecolor="white", linewidth=0.3,
)
axe.add_collection(collection)
axe.autoscale_view()
axe.set_aspect("equal")
axe.axis("off")
plt.colorbar(collection, ax=axe, shrink=0.6, label="Densité moyenne (hab/km²)")
axe.set_title("Densité moyenne par département")
figure.savefig(os.path.join(resultats, "carte_densite_departements.png"), dpi=120, bbox_inches="tight")

print(f"Carte tracée pour {len(densite_par_dep)} départements.")
