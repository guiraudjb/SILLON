# SILLON - Tutoriel, corrigé de l'exercice R 3.2.
#
# Histogramme de la population des communes d'une région.
suppressMessages({
  library(DBI)
  library(RPostgreSQL)
  library(dplyr)
  library(ggplot2)
})

REGION <- "Bretagne"  # à adapter

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
communes <- dbGetQuery(connexion, "SELECT nom_standard, reg_nom, population FROM communes_france")
dbDisconnect(connexion)

sous_ensemble <- communes %>% filter(reg_nom == REGION)

graphique <- ggplot(sous_ensemble, aes(x = population)) +
  geom_histogram(bins = 30, fill = "#000091") +
  scale_x_log10() +
  labs(title = paste("Population des communes -", REGION),
       x = "Population (échelle log)", y = "Nombre de communes") +
  theme_minimal()

ggsave(file.path(resultats, "histogramme_population.png"), graphique, width = 8, height = 6)
cat(sprintf("%d commune(s) tracee(s) pour %s.\n", nrow(sous_ensemble), REGION))
