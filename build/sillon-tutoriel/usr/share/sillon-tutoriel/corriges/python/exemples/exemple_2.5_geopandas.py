"""SILLON - Script Python d'exemple : cartographie SIG avec geopandas (formation avancée, tutoriel).

Reconstruit les polygones départementaux en géométries `shapely` réelles
(plutôt qu'en simples listes de points dessinées à la main, comme dans
`exemple_2.4_cartographie.py`), les reprojette en Lambert-93 (EPSG:2154,
projection officielle de la France métropolitaine) pour calculer une
aire réelle en km², puis fusionne les départements en régions avec
`GeoDataFrame.dissolve()` - une agrégation géométrique impossible avec
l'approche `matplotlib.patches.Polygon` de l'exemple 2.4.

Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
connexion et répertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'exécution (§7.7)
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT dep_code, reg_code, reg_nom, population, superficie_km2 FROM communes_france",
    connexion,
)
contours = pd.read_sql(
    "SELECT dep_code, dep_nom, groupe, ordre, longitude, latitude "
    "FROM contours_departements ORDER BY dep_code, groupe, ordre",
    connexion,
)
connexion.close()

# Reconstitution des polygones : chaque (dep_code, groupe) est un anneau
# fermé de points ordonnés (un département peut compter plusieurs anneaux
# - îles, exclaves).
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

# Métropole uniquement (dep_code sur 2 caractères) : Lambert-93 n'est
# valide qu'en métropole - une aire calculée après reprojection dans ce
# CRS serait fortement faussée pour les départements d'outre-mer (chacun
# à des milliers de km de la zone de validité de la projection). Chaque
# DOM nécessiterait sa propre projection locale (UTM 20N Antilles, UTM
# 22N Guyane, UTM 40S/38S Réunion/Mayotte) - hors périmètre de cet
# exemple. Ce filtre élimine aussi "977"/"978" (Saint-Barthélemy,
# Saint-Martin), présents dans contours_departements mais absents de
# communes_france (ce ne sont pas des départements) - sans lien avec le
# filtre ci-dessus, mais avec le même effet.
departements = departements[departements["dep_code"].str.len() == 2].copy()
departements["aire_km2"] = (departements.to_crs("EPSG:2154").geometry.area / 1_000_000).round(1)

dep_vers_region = communes.drop_duplicates("dep_code").set_index("dep_code")[["reg_code", "reg_nom"]]
departements = departements.merge(dep_vers_region, on="dep_code", how="inner")
population_par_dep = communes.groupby("dep_code")["population"].sum()
departements = departements.merge(population_par_dep.rename("population"), on="dep_code", how="left")

# dissolve() fusionne les polygones départementaux en polygones
# régionaux - une vraie agrégation de géométrie, impossible avec
# l'approche matplotlib.patches.Polygon de exemple_2.4_cartographie.py.
regions = departements.dissolve(by="reg_code", aggfunc={"population": "sum", "reg_nom": "first"})

figure, axe = plt.subplots(figsize=(8, 8))
regions.plot(column="population", cmap="Blues", edgecolor="white", linewidth=0.5, legend=True, ax=axe)
axe.set_aspect("equal")
axe.axis("off")
figure.suptitle("Population par région (limites régionales fusionnées par dissolve())")
figure.savefig(os.path.join(resultats, "carte_regions_geopandas.png"), dpi=120, bbox_inches="tight")

departements.drop(columns="geometry").sort_values("dep_code").to_csv(
    os.path.join(resultats, "aires_departements.csv"), index=False
)

print(f"{len(departements)} départements, {len(regions)} régions (après dissolve).")
