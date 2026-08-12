"""SILLON - Script Python d'exemple : carte choroplèthe Sirene (sillon-demo-sirene).

Densité d'établissements actifs par département, sur les contours réels
importés par sillon-tutoriel (table "contours_departements", IGN ADMIN
EXPRESS - même base personnelle que sirene_etablissements, les deux
paquets partageant le compte de démonstration). Reprend le principe déjà
établi par carte_departements.py (sillon-tutoriel) : pas de bibliothèque
géospatiale dans l'image d'exécution (§7.7), un polygone est reconstitué
à la main à partir d'une liste de points ordonnés.

Le comptage par département est agrégé côté PostgreSQL (GROUP BY) : jamais
un SELECT * sur les ~43,9 millions de lignes de sirene_etablissements.
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
etablissements_par_dep = (
    pd.read_sql("""
        SELECT dep_code, COUNT(*) AS nb FROM sirene_etablissements
        WHERE etat_administratif = 'A' AND dep_code != '' GROUP BY dep_code
    """, connexion)
    .set_index("dep_code")["nb"]
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
couleurs = [etablissements_par_dep.get(dep_code, 0) for (dep_code, _groupe) in polygones]

figure, axe = plt.subplots(figsize=(8, 8))
collection = PatchCollection(
    patches, array=couleurs, cmap=cm.get_cmap("Reds"),
    norm=mcolors.Normalize(vmin=min(couleurs), vmax=max(couleurs)),
    edgecolor="white", linewidth=0.3,
)
axe.add_collection(collection)
axe.autoscale_view()
axe.set_aspect("equal")
axe.axis("off")
plt.colorbar(collection, ax=axe, shrink=0.6, label="Établissements actifs")
axe.set_title("Établissements Sirene actifs par département")
figure.savefig(os.path.join(resultats, "carte_sirene_departements.png"), dpi=120, bbox_inches="tight")

print(f"Carte tracée pour {len(etablissements_par_dep)} départements ({sum(etablissements_par_dep.values()):,} établissements).".replace(",", " "))
