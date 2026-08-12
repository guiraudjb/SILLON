# SILLON - Script R d'exemple pour le compte de démonstration (§5.4).
#
# Trace la population totale par région sur la table "communes_exemple"
# (données fictives, cf. communes_exemple.csv) et dépose le graphique dans
# le répertoire de sortie mis à disposition par SILLON.
#
# Contrat d'exécution (cahier des charges §5.4, worker.py) : ce script
# reçoit sa chaîne de connexion et son répertoire de sortie exclusivement
# via les variables d'environnement posées par sillon-worker, jamais en
# dur. RPostgreSQL n'accepte pas directement une chaîne DSN libpq : on
# l'analyse nous-mêmes en clé=valeur.
suppressMessages({
  library(DBI)
  library(RPostgreSQL)
  library(dplyr)
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

communes <- dbGetQuery(connexion, "SELECT * FROM communes_exemple")
dbDisconnect(connexion)

par_region <- communes %>%
  group_by(region_exemple) %>%
  summarise(population_totale = sum(population), .groups = "drop")

graphique <- ggplot(par_region, aes(x = reorder(region_exemple, -population_totale), y = population_totale)) +
  geom_col(fill = "#000091") + # bleu France (DSFR)
  labs(title = "Population totale par région (exemple)", x = "Région", y = "Population") +
  theme_minimal()

ggsave(file.path(resultats, "population_par_region.png"), graphique, width = 7, height = 5)

cat(sprintf("%d commune(s) analysée(s) - graphique écrit dans population_par_region.png\n", nrow(communes)))
