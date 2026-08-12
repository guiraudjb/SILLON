-- SILLON - Tutoriel, corrigé de l'exercice 3.3
-- Densité moyenne par région, arrondie à une décimale.
SELECT reg_nom, ROUND(AVG(densite)::numeric, 1) AS densite_moyenne
FROM communes_france
GROUP BY reg_nom
ORDER BY densite_moyenne DESC;
