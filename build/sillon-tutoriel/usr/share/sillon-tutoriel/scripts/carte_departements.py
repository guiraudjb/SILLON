"""SILLON - Script Python d'exemple : cartographie (formation avancée, tutoriel).

Trace une carte choroplèthe (population par département) à partir des
contours réels des départements français, déjà importés dans la table
"contours_departements" (source IGN ADMIN EXPRESS, Licence Ouverte 2.0).

Sans librairie géospatiale (pas de geopandas/shapely dans l'image
d'exécution, §7.7) : la table aplatit volontairement chaque polygone en
une liste de points ordonnés (colonnes dep_code, groupe, ordre, longitude,
latitude), reconstituée ici à la main - matplotlib sait dessiner un
polygone à partir d'une simple liste de coordonnées.

Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
connexion et répertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'exécution (§7.7)
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
population_par_dep = (
    pd.read_sql(
        "SELECT dep_code, SUM(population) AS population_totale FROM communes_france GROUP BY dep_code",
        connexion,
    )
    .set_index("dep_code")["population_totale"]
    .to_dict()
)
contours = pd.read_sql(
    "SELECT dep_code, groupe, ordre, longitude, latitude FROM contours_departements ORDER BY dep_code, groupe, ordre",
    connexion,
)
connexion.close()

# Reconstitution des polygones : chaque (dep_code, groupe) est un anneau
# fermé de points ordonnés (un département peut compter plusieurs anneaux
# - îles, exclaves).
polygones = defaultdict(list)
for ligne in contours.itertuples():
    polygones[(ligne.dep_code, ligne.groupe)].append((ligne.longitude, ligne.latitude))

patches = [Polygon(points, closed=True) for (_dep_code, _groupe), points in polygones.items()]
couleurs = [population_par_dep.get(dep_code, 0) for (dep_code, _groupe) in polygones]

figure, axe = plt.subplots(figsize=(8, 8))
collection = PatchCollection(
    patches, array=couleurs, cmap=cm.get_cmap("Blues"),
    norm=mcolors.Normalize(vmin=min(couleurs), vmax=max(couleurs)),
    edgecolor="white", linewidth=0.3,
)
axe.add_collection(collection)
axe.autoscale_view()
axe.set_aspect("equal")
axe.axis("off")
plt.colorbar(collection, ax=axe, shrink=0.6, label="Population")
axe.set_title("Population par département")
figure.savefig(os.path.join(resultats, "carte_population_departements.png"), dpi=120, bbox_inches="tight")

print(f"Carte tracée pour {len(population_par_dep)} départements.")
