# SILLON - Script R d'exemple : cartographie (formation avancée, tutoriel).
#
# Trace une carte choroplèthe (population par département) à partir des
# contours réels des départements français, déjà importés dans la table
# "contours_departements" (source IGN ADMIN EXPRESS, Licence Ouverte 2.0).
#
# Sans librairie géospatiale (pas de sf/maps dans l'image d'exécution,
# §7.7) : geom_polygon() de ggplot2 sait tracer directement un polygone à
# partir d'un data frame de points ordonnés (x, y, group) - le style
# "fortifié" classique de ggplot2, sans dépendance géospatiale.
#
# Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
# connexion et répertoire de sortie fournis exclusivement via variables
# d'environnement, jamais en dur.
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
population_par_dep <- dbGetQuery(
  connexion,
  "SELECT dep_code, SUM(population) AS population_totale FROM communes_france GROUP BY dep_code"
)
contours <- dbGetQuery(
  connexion,
  "SELECT dep_code, groupe, ordre, longitude, latitude FROM contours_departements ORDER BY dep_code, groupe, ordre"
)
dbDisconnect(connexion)

contours <- contours %>%
  mutate(id_polygone = paste(dep_code, groupe, sep = "_")) %>%
  left_join(population_par_dep, by = "dep_code")

carte <- ggplot(contours, aes(x = longitude, y = latitude, group = id_polygone, fill = population_totale)) +
  geom_polygon(color = "white", linewidth = 0.1) +
  coord_fixed() +
  scale_fill_gradient(low = "#e8edfb", high = "#000091", name = "Population") +
  theme_void() +
  labs(title = "Population par département")

ggsave(file.path(resultats, "carte_population_departements.png"), carte, width = 8, height = 8)

cat(sprintf("Carte tracee pour %d departements.\n", n_distinct(contours$dep_code)))
