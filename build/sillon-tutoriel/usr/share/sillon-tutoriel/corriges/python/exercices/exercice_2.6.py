"""SILLON - Tutoriel, corrigé de l'exercice Python 2.6.

Jointure spatiale (`geopandas.sjoin`) : pour chaque commune, le point
(longitude_centre, latitude_centre) tombe-t-il géométriquement dans le
polygone du département qu'elle déclare (`dep_code`) ? Recense les
désaccords et les communes sans correspondance géométrique.
"""
import os
from collections import defaultdict

import pandas as pd
import psycopg2
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT code_insee, nom_standard, dep_code, longitude_centre, latitude_centre FROM communes_france",
    connexion,
)
contours = pd.read_sql(
    "SELECT dep_code, groupe, ordre, longitude, latitude "
    "FROM contours_departements ORDER BY dep_code, groupe, ordre",
    connexion,
)
connexion.close()

anneaux = defaultdict(list)
for ligne in contours.itertuples():
    anneaux[(ligne.dep_code, ligne.groupe)].append((ligne.longitude, ligne.latitude))

geometries_par_dep = defaultdict(list)
for (dep_code, _groupe), points in anneaux.items():
    geometries_par_dep[dep_code].append(Polygon(points))

departements = gpd.GeoDataFrame(
    {
        "dep_code_geo": list(geometries_par_dep.keys()),
        "geometry": [
            polys[0] if len(polys) == 1 else MultiPolygon(polys)
            for polys in geometries_par_dep.values()
        ],
    },
    crs="EPSG:4326",
)

points_communes = gpd.GeoDataFrame(
    communes[["code_insee", "nom_standard", "dep_code"]],
    geometry=gpd.points_from_xy(communes["longitude_centre"], communes["latitude_centre"]),
    crs="EPSG:4326",
)

# "within" plutôt que "intersects" : un point exactement sur une
# frontière compterait deux fois avec "intersects".
jointure = gpd.sjoin(points_communes, departements, how="left", predicate="within")
# Un point exactement sur une frontière partagée par deux polygones peut,
# par tolérance flottante, matcher les deux (constaté en pratique, sur
# une poignée de communes) - on ne garde que la première correspondance.
jointure = jointure.drop_duplicates(subset="code_insee", keep="first")

desaccords = jointure[jointure["dep_code"] != jointure["dep_code_geo"]]
desaccords[["code_insee", "nom_standard", "dep_code", "dep_code_geo"]].rename(
    columns={"dep_code": "dep_code_declare", "dep_code_geo": "dep_code_geometrique"}
).to_csv(os.path.join(resultats, "desaccords_communes_departements.csv"), index=False)

sans_correspondance = int(jointure["dep_code_geo"].isna().sum())
print(
    f"{len(jointure)} communes, {len(desaccords)} désaccord(s) commune/département, "
    f"{sans_correspondance} commune(s) hors de tout polygone (contour manquant ou "
    "point de centre en mer/frontière — communes littorales et communes nouvelles "
    "au centroïde recalculé, essentiellement)."
)
