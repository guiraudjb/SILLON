"""SILLON - Tutoriel, corrigé de l'exercice Python 2.4.

Export Excel avec un onglet par région, chacun listant les communes de la
région triées par population.
"""
import os

import pandas as pd
import psycopg2
from openpyxl import Workbook
from openpyxl.styles import Font

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
communes = pd.read_sql(
    "SELECT reg_nom, nom_standard, population FROM communes_france ORDER BY reg_nom, population DESC",
    connexion,
)
connexion.close()

classeur = Workbook()
classeur.remove(classeur.active)  # feuille par défaut vide, retirée

for region, groupe in communes.groupby("reg_nom"):
    nom_feuille = region[:31]  # limite Excel : 31 caractères par nom d'onglet
    feuille = classeur.create_sheet(nom_feuille)
    feuille.append(["Commune", "Population"])
    feuille["A1"].font = feuille["B1"].font = Font(bold=True)
    for _, ligne in groupe.iterrows():
        feuille.append([ligne["nom_standard"], int(ligne["population"])])

classeur.save(os.path.join(resultats, "communes_par_region.xlsx"))
print(f"{communes['reg_nom'].nunique()} onglet(s) créé(s).")
