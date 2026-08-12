"""SILLON - Tutoriel, corrigé de l'exercice Python 2.1.

Calcule la superficie totale de la France métropolitaine (hors
départements d'outre-mer, codes 971 à 976) et écrit le résultat dans un
fichier texte.
"""
import os

import psycopg2

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
with connexion.cursor() as cur:
    cur.execute("""
        SELECT SUM(superficie_km2)
        FROM communes_france
        WHERE dep_code NOT IN ('971', '972', '973', '974', '975', '976')
    """)
    superficie_totale = cur.fetchone()[0]
connexion.close()

with open(os.path.join(resultats, "superficie_metropole.txt"), "w") as f:
    f.write(f"Superficie totale de la France métropolitaine : {superficie_totale:.0f} km²\n")

print(f"Superficie métropolitaine : {superficie_totale:.0f} km²")
