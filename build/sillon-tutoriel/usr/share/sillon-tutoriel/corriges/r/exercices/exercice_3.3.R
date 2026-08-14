# SILLON - Tutoriel, corrigé de l'exercice R 3.3.
#
# Part de la population régionale que représente le chef-lieu (jointure
# entre communes_france et regions_france) - équivalent R de l'exercice
# SQL 6.2.
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
communes <- dbGetQuery(connexion, "SELECT code_insee, nom_standard, reg_nom, population FROM communes_france")
regions <- dbGetQuery(connexion, "SELECT reg_nom, chef_lieu_code_insee FROM regions_france")
dbDisconnect(connexion)

population_regions <- communes %>%
  group_by(reg_nom) %>%
  summarise(population_totale = sum(population))

# Sous-ensemble sans reg_nom pour éviter la collision de nom de colonne
# avec celui déjà porté par "regions" lors de la jointure suivante.
chefs_lieux <- regions %>%
  inner_join(
    communes %>% select(code_insee, chef_lieu = nom_standard, population_chef_lieu = population),
    by = c("chef_lieu_code_insee" = "code_insee")
  )

resultat <- chefs_lieux %>%
  inner_join(population_regions, by = "reg_nom") %>%
  mutate(part_pourcent = round(100 * population_chef_lieu / population_totale, 1)) %>%
  select(chef_lieu, reg_nom, population_chef_lieu, population_totale, part_pourcent) %>%
  arrange(desc(part_pourcent))

write.csv(resultat, file.path(resultats, "part_chef_lieu.csv"), row.names = FALSE)
cat(sprintf("%d region(s) analysee(s).\n", nrow(resultat)))
