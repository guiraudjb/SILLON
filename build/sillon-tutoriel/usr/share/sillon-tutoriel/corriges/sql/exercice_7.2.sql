-- SILLON - Tutoriel, corrigé de l'exercice 7.2
-- La commune la plus peuplée de chaque département (fonction de fenêtrage).
SELECT * FROM (
    SELECT
        nom_standard, dep_nom, population,
        RANK() OVER (PARTITION BY dep_code ORDER BY population DESC) AS rang_departemental
    FROM communes_france
) classement
WHERE rang_departemental = 1
ORDER BY population DESC;
