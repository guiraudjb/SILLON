-- SILLON - Tutoriel, corrigé de l'exercice 2.2
-- Les 5 communes les plus hautes en altitude de France.
SELECT nom_standard, dep_nom, altitude_moyenne
FROM communes_france
WHERE altitude_moyenne IS NOT NULL
ORDER BY altitude_moyenne DESC
LIMIT 5;
