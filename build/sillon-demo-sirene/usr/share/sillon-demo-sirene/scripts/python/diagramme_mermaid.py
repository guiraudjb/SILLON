"""SILLON - Script Python d'exemple : diagramme Mermaid (sillon-demo-sirene).

Le bac à sable d'exécution n'a ni Node.js ni Chromium (§7.7/§8.7 du cahier
des charges : seuls des paquets Debian officiels, image volontairement
légère) - impossible d'y faire tourner mermaid-cli pour produire une image.
Un script y écrit donc seulement le texte Mermaid (aucune bibliothèque
requise, une simple chaîne de caractères formatée), rendu ensuite côté
navigateur par SILLON lui-même (mermaid.min.js vendorisé, bouton
"Diagrammes" dans l'onglet Suivi - cf. orchestrateur.py /jobs/<id>/apercus
et app.js Suivi.afficherApercus).

Toujours une agrégation SQL, jamais un SELECT * sur les ~43,9 millions de
lignes de sirene_etablissements.
"""
import os

import psycopg2

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)
curseur = connexion.cursor()
curseur.execute("""
    SELECT COALESCE(NULLIF(tranche_effectifs, ''), 'Non renseigné') AS tranche, COUNT(*) AS nb
    FROM sirene_etablissements WHERE etat_administratif = 'A'
    GROUP BY tranche ORDER BY nb DESC LIMIT 10
""")
par_tranche = curseur.fetchall()
connexion.close()

lignes = ['pie showData title Établissements actifs par tranche d\'effectif (10 principales)']
for tranche, nb in par_tranche:
    tranche_echappee = tranche.replace('"', "'")
    lignes.append(f'    "{tranche_echappee}" : {nb}')

with open(os.path.join(resultats, "repartition_tranches.mmd"), "w", encoding="utf-8") as f:
    f.write("\n".join(lignes) + "\n")

print(f"Diagramme Mermaid produit pour {len(par_tranche)} tranches d'effectif.")
