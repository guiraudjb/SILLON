# SILLON - Script R d'exemple : panorama ggplot2 (sillon-demo-sirene).
#
# Trois graphiques ggplot2 (barres, courbe temporelle, nuage de points) sur
# des requêtes déjà agrégées côté PostgreSQL - jamais un SELECT * sur les
# ~43,9 millions de lignes de sirene_etablissements (même principe que les
# scripts Python de ce paquet).
#
# Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
# connexion et répertoire de sortie fournis exclusivement via variables
# d'environnement. RPostgreSQL n'accepte pas directement une chaîne DSN
# libpq : on l'analyse nous-mêmes en clé=valeur (même helper que
# analyse_densite.R, sillon-tutoriel).
suppressMessages({
  library(DBI)
  library(RPostgreSQL)
  library(ggplot2)
})

analyser_dsn <- function(dsn) {
  valeurs <- list()
  for (paire in strsplit(trimws(dsn), "\\s+")[[1]]) {
    cle_valeur <- strsplit(paire, "=", fixed = TRUE)[[1]]
    valeurs[[cle_valeur[1]]] <- cle_valeur[2]
  }
  valeurs
}

parametres <- analyser_dsn(Sys.getenv("SILLON_DSN"))
resultats <- Sys.getenv("SILLON_RESULTATS")

connexion <- dbConnect(
  PostgreSQL(),
  host = parametres$host, port = as.integer(parametres$port),
  dbname = parametres$dbname, user = parametres$user, password = parametres$password
)

par_tranche <- dbGetQuery(connexion, "
  SELECT COALESCE(NULLIF(tranche_effectifs, ''), 'NR') AS tranche, COUNT(*) AS nb
  FROM sirene_etablissements WHERE etat_administratif = 'A'
  GROUP BY tranche ORDER BY tranche
")

par_annee <- dbGetQuery(connexion, "
  SELECT EXTRACT(YEAR FROM date_creation)::int AS annee, COUNT(*) AS nb
  FROM sirene_etablissements WHERE date_creation >= '1990-01-01' GROUP BY annee ORDER BY annee
")

par_departement <- dbGetQuery(connexion, "
  SELECT dep_code, COUNT(*) AS nb FROM sirene_etablissements
  WHERE etat_administratif = 'A' AND dep_code != '' GROUP BY dep_code
")

dbDisconnect(connexion)

graphique_tranches <- ggplot(par_tranche, aes(x = tranche, y = nb)) +
  geom_col(fill = "#000091") +
  theme_minimal() + theme(axis.text.x = element_text(angle = 90, size = 7)) +
  labs(title = "Établissements actifs par tranche d'effectif", x = "Tranche", y = "Nombre")
ggsave(file.path(resultats, "ggplot_tranches.png"), graphique_tranches, width = 8, height = 6)

graphique_annees <- ggplot(par_annee, aes(x = annee, y = nb)) +
  geom_line(color = "#e1000f") +
  theme_minimal() +
  labs(title = "Créations d'établissements par année", x = "Année", y = "Créations")
ggsave(file.path(resultats, "ggplot_creations.png"), graphique_annees, width = 8, height = 6)

graphique_departements <- ggplot(par_departement, aes(x = nb)) +
  geom_histogram(bins = 30, fill = "#000091") +
  theme_minimal() +
  labs(title = "Distribution du nombre d'établissements actifs par département",
       x = "Établissements actifs (par département)", y = "Nombre de départements")
ggsave(file.path(resultats, "ggplot_distribution_departements.png"), graphique_departements, width = 8, height = 6)

cat(sprintf("3 graphiques ggplot2 produits (%d tranches, %d annees, %d departements).\n",
            nrow(par_tranche), nrow(par_annee), nrow(par_departement)))
