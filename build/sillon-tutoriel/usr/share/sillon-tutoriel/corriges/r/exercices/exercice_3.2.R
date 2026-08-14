# SILLON - Tutoriel, corrigé de l'exercice R 3.2.
#
# Avec facet_wrap, histogramme de la population des communes, un panneau
# par région.
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
communes <- dbGetQuery(connexion, "SELECT reg_nom, population FROM communes_france")
dbDisconnect(connexion)

graphique <- ggplot(communes, aes(x = population)) +
  geom_histogram(bins = 30, fill = "#000091") +
  scale_x_log10() +
  facet_wrap(~ reg_nom) +
  labs(title = "Population des communes par région", x = "Population (échelle log)", y = "Nombre de communes") +
  theme_minimal()

ggsave(file.path(resultats, "histogramme_population_facette.png"), graphique, width = 12, height = 9)
cat(sprintf("Histogramme facette pour %d region(s).\n", length(unique(communes$reg_nom))))
