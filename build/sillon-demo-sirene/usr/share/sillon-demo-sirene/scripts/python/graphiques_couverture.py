"""SILLON - Script Python d'exemple : panorama des types de graphiques (sillon-demo-sirene).

Quatre graphiques matplotlib usuels (barres, camembert, courbe temporelle,
barres horizontales) sur la table "sirene_etablissements" (~43,9 millions
de lignes). Chaque requête agrège côté PostgreSQL (GROUP BY) : jamais un
SELECT * de la table entière, qui dépasserait très largement le quota
mémoire du conteneur d'exécution (ram_max_conteneur_mo, §11 du cahier des
charges) - seul le résultat déjà réduit (quelques dizaines de lignes au
plus) transite vers pandas/matplotlib.

Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
connexion et répertoire de sortie fournis exclusivement par variables
d'environnement, jamais en dur.
"""
import os

import matplotlib
matplotlib.use("Agg")  # aucun affichage interactif possible dans le conteneur d'exécution (§7.7)
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)

par_tranche = pd.read_sql("""
    SELECT COALESCE(NULLIF(tranche_effectifs, ''), 'Non renseigné') AS tranche, COUNT(*) AS nb
    FROM sirene_etablissements WHERE etat_administratif = 'A'
    GROUP BY tranche ORDER BY tranche
""", connexion)

par_caractere_employeur = pd.read_sql("""
    SELECT CASE caractere_employeur WHEN 'O' THEN 'Employeur' WHEN 'N' THEN 'Non employeur' ELSE 'Non renseigné' END AS categorie,
           COUNT(*) AS nb
    FROM sirene_etablissements WHERE etat_administratif = 'A'
    GROUP BY categorie ORDER BY nb DESC
""", connexion)

creations_par_annee = pd.read_sql("""
    SELECT EXTRACT(YEAR FROM date_creation)::int AS annee, COUNT(*) AS nb
    FROM sirene_etablissements
    WHERE date_creation IS NOT NULL AND date_creation >= '1990-01-01'
    GROUP BY annee ORDER BY annee
""", connexion)

top_secteurs = pd.read_sql("""
    SELECT LEFT(activite_principale, 2) AS division_naf, COUNT(*) AS nb
    FROM sirene_etablissements
    WHERE etat_administratif = 'A' AND activite_principale IS NOT NULL AND activite_principale != ''
    GROUP BY division_naf ORDER BY nb DESC LIMIT 15
""", connexion)

connexion.close()

figure, axes = plt.subplots(2, 2, figsize=(13, 10))

axes[0, 0].bar(par_tranche["tranche"], par_tranche["nb"], color="#000091")
axes[0, 0].set_title("Établissements actifs par tranche d'effectif")
axes[0, 0].tick_params(axis="x", rotation=90, labelsize=7)

axes[0, 1].pie(par_caractere_employeur["nb"], labels=par_caractere_employeur["categorie"], autopct="%1.1f%%",
               colors=["#000091", "#e1000f", "#b7b7b7"])
axes[0, 1].set_title("Part des établissements employeurs")

axes[1, 0].plot(creations_par_annee["annee"], creations_par_annee["nb"], color="#e1000f", marker=".")
axes[1, 0].set_title("Créations d'établissements par année")
axes[1, 0].set_xlabel("Année")

axes[1, 1].barh(top_secteurs["division_naf"][::-1], top_secteurs["nb"][::-1], color="#000091")
axes[1, 1].set_title("15 divisions NAF les plus représentées (actifs)")

figure.suptitle(f"Panorama Sirene ({len(par_tranche)} tranches, {creations_par_annee['nb'].sum():,} créations analysées)".replace(",", " "))
figure.tight_layout()
figure.savefig(os.path.join(resultats, "panorama_graphiques.png"), dpi=120)

print(f"4 graphiques produits à partir de {len(par_tranche) + len(par_caractere_employeur) + len(creations_par_annee) + len(top_secteurs)} lignes agrégées (jamais la table complète).")
