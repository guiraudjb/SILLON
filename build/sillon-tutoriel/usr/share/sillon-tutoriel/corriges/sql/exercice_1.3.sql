-- SILLON - Tutoriel, corrigé de l'exercice 1.3
-- Communes de moins de 100 habitants en Corse (code région 94).
SELECT nom_standard, dep_nom, population
FROM communes_france
WHERE reg_code = '94' AND population < 100;
