-- SILLON - Tutoriel, corrigé de l'exercice 5.2
-- Pour chaque région, la commune la plus peuplée (sous-requête corrélée).
SELECT c.nom_standard, c.reg_nom, c.population
FROM communes_france c
WHERE c.population = (
    SELECT MAX(c2.population) FROM communes_france c2 WHERE c2.reg_nom = c.reg_nom
)
ORDER BY c.population DESC;
