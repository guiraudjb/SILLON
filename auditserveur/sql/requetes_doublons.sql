-- Audit serveur - detection de doublons de fichiers
-- A executer dans SILLON, onglet Travaux, sur la base ou a ete importe
-- le CSV d'inventaire (colonnes nom_fichier / hash / taille_ko / chemin_complet).
-- Remplacer <table> par le nom reel de la table creee a l'import (visible
-- dans l'onglet Bases > Tables).

-- 1. Resume : groupes de fichiers identiques (meme hash) et espace gaspille
SELECT
    hash,
    count(*)                         AS nb_copies,
    max(taille_ko)                   AS taille_ko,
    (count(*) - 1) * max(taille_ko)  AS ko_gaspilles,
    array_agg(nom_fichier)           AS fichiers,
    array_agg(chemin_complet)        AS chemins
FROM <table>
GROUP BY hash
HAVING count(*) > 1
ORDER BY ko_gaspilles DESC;

-- 2. Detail ligne par ligne, avec un "original" designe (le premier par
-- chemin) et le reste marque "doublon", pour preparer un nettoyage
SELECT
    hash,
    nom_fichier,
    chemin_complet,
    taille_ko,
    row_number() OVER (PARTITION BY hash ORDER BY chemin_complet) AS rang,
    CASE WHEN row_number() OVER (PARTITION BY hash ORDER BY chemin_complet) = 1
         THEN 'original' ELSE 'doublon' END AS statut
FROM <table>
WHERE hash IN (
    SELECT hash FROM <table> GROUP BY hash HAVING count(*) > 1
)
ORDER BY hash, rang;
