-- SILLON - Tutoriel, corrigé de l'exercice 4.2
-- Départements comptant plus de 500 communes.
SELECT dep_nom, COUNT(*) AS nb_communes
FROM communes_france
GROUP BY dep_nom
HAVING COUNT(*) > 500
ORDER BY nb_communes DESC;
