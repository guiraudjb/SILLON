# SILLON - Script R d'exemple (formation avancée, tutoriel).
#
# Analyse de la densité de population par département sur le jeu de
# données réel "communes_france" (INSEE/IGN, via data.gouv.fr) : les 15
# départements les plus densément peuplés en moyenne, et la relation entre
# altitude et densité (les communes de montagne sont-elles moins denses ?).
#
# Contrat d'exécution (cahier des charges §5.4, worker.py) : chaîne de
# connexion et répertoire de sortie fournis exclusivement via variables
# d'environnement, jamais en dur. RPostgreSQL n'accepte pas directement une
# chaîne DSN libpq : on l'analyse nous-mêmes en clé=valeur.
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
communes <- dbGetQuery(connexion, "SELECT * FROM communes_france")
dbDisconnect(connexion)

# 1. Densité moyenne par département (15 plus denses)
par_departement <- communes %>%
  filter(!is.na(densite), densite > 0) %>%
  group_by(dep_nom) %>%
  summarise(densite_moyenne = mean(densite), nb_communes = n(), .groups = "drop") %>%
  arrange(desc(densite_moyenne)) %>%
  head(15)

graphique_densite <- ggplot(par_departement, aes(x = reorder(dep_nom, densite_moyenne), y = densite_moyenne)) +
  geom_col(fill = "#000091") +
  coord_flip() +
  labs(title = "15 départements les plus densément peuplés (moyenne)",
       x = "Département", y = "Densité moyenne (hab/km²)") +
  theme_minimal()
ggsave(file.path(resultats, "densite_par_departement.png"), graphique_densite, width = 8, height = 6)

# 2. Altitude vs densité (échantillon pour lisibilité du nuage de points)
echantillon <- communes %>%
  filter(!is.na(altitude_moyenne), !is.na(densite), densite > 0) %>%
  slice_sample(n = min(3000, nrow(.)))

graphique_altitude <- ggplot(echantillon, aes(x = altitude_moyenne, y = densite)) +
  geom_point(alpha = 0.2, color = "#000091") +
  scale_y_log10() +
  labs(title = "Altitude et densité de population par commune",
       x = "Altitude moyenne (m)", y = "Densité (hab/km², échelle log)") +
  theme_minimal()
ggsave(file.path(resultats, "altitude_vs_densite.png"), graphique_altitude, width = 8, height = 6)

write.csv(par_departement, file.path(resultats, "densite_par_departement.csv"), row.names = FALSE)

cat(sprintf(
  "%d commune(s) analysee(s) sur %d departement(s).\n",
  nrow(communes), n_distinct(communes$dep_nom)
))
cat("Fichiers produits : densite_par_departement.png/csv, altitude_vs_densite.png\n")
