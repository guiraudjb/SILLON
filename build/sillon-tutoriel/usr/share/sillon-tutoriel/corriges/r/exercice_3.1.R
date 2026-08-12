# SILLON - Tutoriel, corrigé de l'exercice R 3.1.
#
# Nombre de communes et population totale par région, exportés en CSV.
suppressMessages({
  library(DBI)
  library(RPostgreSQL)
  library(dplyr)
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
communes <- dbGetQuery(connexion, "SELECT reg_nom, population FROM communes_france")
dbDisconnect(connexion)

tableau <- communes %>%
  group_by(reg_nom) %>%
  summarise(nb_communes = n(), population_totale = sum(population)) %>%
  arrange(desc(population_totale))

write.csv(tableau, file.path(resultats, "population_par_region.csv"), row.names = FALSE)
cat(sprintf("%d region(s) resumee(s).\n", nrow(tableau)))
