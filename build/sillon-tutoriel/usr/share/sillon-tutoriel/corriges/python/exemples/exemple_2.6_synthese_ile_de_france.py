"""SILLON - Script de synthese : Ile-de-France, toutes les bibliotheques
Python disponibles dans l'image d'execution combinees sur un seul jeu de
donnees (communes_france, regions_france, contours_departements) :
psycopg2 (acces base), pandas (analyse), numpy (statistiques), matplotlib
(graphiques + PDF multi-pages), openpyxl (classeur Excel + graphique
natif), geopandas (cartographie SIG reelle).

Contrat d'execution (cahier des charges §5.4, worker.py) : chaine de
connexion et repertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'execution (§7.7)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import psycopg2
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]
REG_IDF = "11"

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT code_insee, nom_standard, dep_code, dep_nom, population, superficie_km2, "
    "densite, altitude_moyenne, latitude_centre, longitude_centre "
    "FROM communes_france WHERE reg_code = %(reg)s",
    connexion, params={"reg": REG_IDF},
)
contours = pd.read_sql(
    "SELECT dep_code, dep_nom, groupe, ordre, longitude, latitude FROM contours_departements "
    "WHERE dep_code IN %(deps)s ORDER BY dep_code, groupe, ordre",
    connexion, params={"deps": tuple(communes["dep_code"].unique())},
)
connexion.close()

print(f"Île-de-France : {len(communes)} communes sur {communes['dep_code'].nunique()} départements.")

# =====================================================================
# 1. NUMPY - statistiques descriptives et matrice de corrélation
# =====================================================================
colonnes_numeriques = ["population", "superficie_km2", "densite", "altitude_moyenne"]
donnees_np = communes[colonnes_numeriques].to_numpy(dtype=float)
moyennes = np.nanmean(donnees_np, axis=0)
medianes = np.nanmedian(donnees_np, axis=0)
ecarts_types = np.nanstd(donnees_np, axis=0)
correlations = communes[colonnes_numeriques].corr().to_numpy()

stats_np = pd.DataFrame(
    {"moyenne": moyennes, "médiane": medianes, "écart_type": ecarts_types}, index=colonnes_numeriques
).round(1)
print("\nStatistiques (numpy) :")
print(stats_np.to_string())

# =====================================================================
# 2. PANDAS - agrégation par département
# =====================================================================
par_dep = communes.groupby(["dep_code", "dep_nom"]).agg(
    nb_communes=("code_insee", "count"),
    population=("population", "sum"),
    densite_moyenne=("densite", "mean"),
).round(1).reset_index().sort_values("population", ascending=False)

top10_communes = communes.nlargest(10, "population")[["nom_standard", "dep_nom", "population", "densite"]]

# =====================================================================
# 3. MATPLOTLIB - tableau de bord (4 graphiques en une image)
# =====================================================================
figure_panorama, axes = plt.subplots(2, 2, figsize=(11, 9))

axes[0, 0].barh(par_dep["dep_nom"], par_dep["population"], color="#0055a4")
axes[0, 0].set_title("Population par département")
axes[0, 0].invert_yaxis()

axes[0, 1].hist(communes["densite"].dropna(), bins=40, color="#0055a4")
axes[0, 1].set_yscale("log")
axes[0, 1].set_title("Distribution de la densité (échelle log)")
axes[0, 1].set_xlabel("hab/km²")

axes[1, 0].scatter(communes["altitude_moyenne"], communes["densite"], s=8, alpha=0.4, color="#0055a4")
axes[1, 0].set_yscale("log")
axes[1, 0].set_title("Altitude vs densité")
axes[1, 0].set_xlabel("Altitude moyenne (m)")
axes[1, 0].set_ylabel("Densité (hab/km², log)")

image_correlation = axes[1, 1].imshow(correlations, cmap="coolwarm", vmin=-1, vmax=1)
axes[1, 1].set_xticks(range(len(colonnes_numeriques)), colonnes_numeriques, rotation=45, ha="right")
axes[1, 1].set_yticks(range(len(colonnes_numeriques)), colonnes_numeriques)
axes[1, 1].set_title("Corrélations (numpy)")
plt.colorbar(image_correlation, ax=axes[1, 1], shrink=0.8)

figure_panorama.suptitle("Île-de-France — panorama", fontsize=14)
figure_panorama.tight_layout()

# =====================================================================
# 4. GEOPANDAS - carte réelle des 8 départements (aire, reprojection)
# =====================================================================
anneaux = defaultdict(list)
noms_dep = {}
for ligne in contours.itertuples():
    anneaux[(ligne.dep_code, ligne.groupe)].append((ligne.longitude, ligne.latitude))
    noms_dep[ligne.dep_code] = ligne.dep_nom

geometries_par_dep = defaultdict(list)
for (dep_code, _groupe), points in anneaux.items():
    geometries_par_dep[dep_code].append(Polygon(points))

departements_geo = gpd.GeoDataFrame(
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
# Lambert-93 (EPSG:2154) : valide ici, l'Île-de-France est entièrement en
# métropole (contrairement à un usage national incluant les DOM, voir
# exemple_2.5_geopandas.py).
departements_geo["aire_km2"] = (departements_geo.to_crs("EPSG:2154").geometry.area / 1_000_000).round(1)
departements_geo = departements_geo.merge(par_dep[["dep_code", "population"]], on="dep_code")
departements_geo["densite_dep"] = (departements_geo["population"] / departements_geo["aire_km2"]).round(0)

# Jointure spatiale : les communes dont le point central tombe hors de son
# département déclaré (même vérification qu'exercice_2.6.py, restreinte
# ici à l'Île-de-France).
points_communes = gpd.GeoDataFrame(
    communes[["code_insee", "nom_standard", "dep_code"]],
    geometry=gpd.points_from_xy(communes["longitude_centre"], communes["latitude_centre"]),
    crs="EPSG:4326",
)
jointure = gpd.sjoin(
    points_communes, departements_geo[["dep_code", "geometry"]].rename(columns={"dep_code": "dep_code_geo"}),
    how="left", predicate="within",
).drop_duplicates(subset="code_insee", keep="first")
desaccords = jointure[jointure["dep_code"] != jointure["dep_code_geo"]]

figure_carte, axe_carte = plt.subplots(figsize=(7, 7))
departements_geo.plot(
    column="densite_dep", cmap="Blues", edgecolor="white", linewidth=0.8, legend=True, ax=axe_carte,
)
if len(desaccords):
    points_communes[points_communes["code_insee"].isin(desaccords["code_insee"])].plot(
        ax=axe_carte, color="red", markersize=12, label="désaccord dep_code/géométrie",
    )
    axe_carte.legend(loc="lower right")
axe_carte.set_aspect("equal")
axe_carte.axis("off")
figure_carte.suptitle("Île-de-France — densité par département (geopandas)")

# =====================================================================
# 5. RAPPORT PDF MULTI-PAGES (panorama + carte)
# =====================================================================
with PdfPages(os.path.join(resultats, "synthese_ile_de_france.pdf")) as pdf:
    pdf.savefig(figure_panorama)
    pdf.savefig(figure_carte, bbox_inches="tight")
figure_panorama.savefig(os.path.join(resultats, "panorama_idf.png"), dpi=110, bbox_inches="tight")
figure_carte.savefig(os.path.join(resultats, "carte_densite_idf.png"), dpi=110, bbox_inches="tight")

# =====================================================================
# 6. OPENPYXL - classeur Excel (synthèse + un onglet par département)
# =====================================================================
classeur = Workbook()

synthese = classeur.active
synthese.title = "Synthèse"
synthese.append(["Département", "Communes", "Population", "Densité moyenne", "Aire (km²)"])
for cellule in synthese[1]:
    cellule.font = Font(bold=True)
dep_avec_aire = par_dep.merge(departements_geo[["dep_code", "aire_km2"]], on="dep_code")
for ligne in dep_avec_aire.itertuples():
    synthese.append([ligne.dep_nom, ligne.nb_communes, int(ligne.population), ligne.densite_moyenne, ligne.aire_km2])

graphique = BarChart()
graphique.title = "Population par département"
donnees_graph = Reference(synthese, min_col=3, min_row=1, max_row=synthese.max_row)
categories_graph = Reference(synthese, min_col=1, min_row=2, max_row=synthese.max_row)
graphique.add_data(donnees_graph, titles_from_data=True)
graphique.set_categories(categories_graph)
synthese.add_chart(graphique, "G2")

for dep_code, groupe in communes.sort_values("population", ascending=False).groupby("dep_code"):
    feuille = classeur.create_sheet(noms_dep[dep_code][:31])
    feuille.append(["Commune", "Population", "Densité", "Altitude moyenne"])
    for cellule in feuille[1]:
        cellule.font = Font(bold=True)
    for ligne in groupe.itertuples():
        feuille.append([ligne.nom_standard, int(ligne.population), ligne.densite, ligne.altitude_moyenne])

classeur.save(os.path.join(resultats, "synthese_ile_de_france.xlsx"))

# =====================================================================
# 7. Résumé
# =====================================================================
print(f"\nTop 10 communes par population :\n{top10_communes.to_string(index=False)}")
print(f"\n{len(desaccords)} désaccord(s) commune/département sur {len(communes)} communes (jointure spatiale).")
print(f"\nFichiers produits : synthese_ile_de_france.pdf, panorama_idf.png, "
      f"carte_densite_idf.png, synthese_ile_de_france.xlsx")
