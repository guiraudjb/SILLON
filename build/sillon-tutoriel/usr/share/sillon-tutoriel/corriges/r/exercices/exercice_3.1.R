# SILLON - Tutoriel, corrigé de l'exercice R 3.1.
#
# Reproduit la carte de l'exemple `exemple_3.4_cartographie.R`, mais
# coloriée par densité moyenne plutôt que par population totale.
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
contours <- dbGetQuery(
  connexion,
  "SELECT dep_code, groupe, ordre, longitude, latitude FROM contours_departements ORDER BY dep_code, groupe, ordre"
)
densite_par_dep <- dbGetQuery(
  connexion, "SELECT dep_code, ROUND(AVG(densite)::numeric, 1) AS densite_moyenne FROM communes_france GROUP BY dep_code"
)
dbDisconnect(connexion)

contours <- contours %>%
  mutate(id_polygone = paste(dep_code, groupe, sep = "_")) %>%
  left_join(densite_par_dep, by = "dep_code")

# trans = "log10" plutôt qu'une échelle linéaire : la densité, contrairement
# à la population brute, est extrêmement asymétrique d'un département à
# l'autre (~20 000 hab/km² à Paris contre 15-30 dans un département rural,
# un facteur 1000) - une échelle linéaire écrase alors tous les départements
# sauf Paris dans la teinte la plus claire, qui paraissent tous blancs
# (constaté en pratique). L'échelle logarithmique donne un contraste réel
# sur toute la gamme de valeurs.
carte <- ggplot(contours, aes(x = longitude, y = latitude, group = id_polygone, fill = densite_moyenne)) +
  geom_polygon(color = "white", linewidth = 0.1) +
  coord_fixed() +
  scale_fill_gradient(low = "#e8edfb", high = "#000091", name = "Densité (hab/km²)", trans = "log10") +
  theme_void()
ggsave(file.path(resultats, "carte_densite.png"), carte, width = 8, height = 8)

cat("Carte de densité par département produite.\n")
