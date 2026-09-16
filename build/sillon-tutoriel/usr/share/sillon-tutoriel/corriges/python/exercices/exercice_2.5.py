"""SILLON - Tutoriel, corrigé de l'exercice Python 2.5.

Compare, pour chaque département métropolitain, l'aire calculée par
geopandas (géométrie réelle, reprojetée en Lambert-93) à la superficie
déclarée (somme des `superficie_km2` des communes du département) :
écart relatif en %, triés du plus grand écart absolu au plus petit.
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
communes = pd.read_sql("SELECT dep_code, superficie_km2 FROM communes_france", connexion)
contours = pd.read_sql(
    "SELECT dep_code, dep_nom, groupe, ordre, longitude, latitude "
    "FROM contours_departements ORDER BY dep_code, groupe, ordre",
    connexion,
)
connexion.close()

anneaux = defaultdict(list)
noms_dep = {}
for ligne in contours.itertuples():
    anneaux[(ligne.dep_code, ligne.groupe)].append((ligne.longitude, ligne.latitude))
    noms_dep[ligne.dep_code] = ligne.dep_nom

geometries_par_dep = defaultdict(list)
for (dep_code, _groupe), points in anneaux.items():
    geometries_par_dep[dep_code].append(Polygon(points))

departements = gpd.GeoDataFrame(
    {
        "dep_code": list(geometries_par_dep.keys()),
        "dep_nom": [noms_dep[c] for c in geometries_par_dep.keys()],
        "geometry": [
            polys[0] if len(polys) == 1 else MultiPolygon(polys)
            for polys in geometries_par_dep.values()
        ],
    },
    crs="EPSG:4326",
)

# Métropole uniquement : Lambert-93 (EPSG:2154) n'est pas valide pour
# calculer une aire en outre-mer, et communes_france ne porte de toute
# façon aucune superficie_km2 pour les DOM dans ce jeu de données
# (constaté en pratique) - la comparaison ne serait pas interprétable
# pour eux dans les deux cas.
departements = departements[departements["dep_code"].str.len() == 2].copy()
departements["aire_calculee_km2"] = (departements.to_crs("EPSG:2154").geometry.area / 1_000_000).round(1)

aire_declaree = communes.groupby("dep_code")["superficie_km2"].sum().round(1)
departements = departements.merge(aire_declaree.rename("aire_declaree_km2"), on="dep_code", how="left")
departements["ecart_pct"] = (
    (departements["aire_calculee_km2"] - departements["aire_declaree_km2"]) / departements["aire_declaree_km2"] * 100
).round(2)

resultat = (
    departements[["dep_code", "dep_nom", "aire_calculee_km2", "aire_declaree_km2", "ecart_pct"]]
    .sort_values("ecart_pct", key=lambda s: s.abs(), ascending=False)
)
resultat.to_csv(os.path.join(resultats, "ecarts_aires_departements.csv"), index=False)

print(f"{len(resultat)} départements comparés. Top 5 des écarts :")
print(resultat.head(5).to_string(index=False))
