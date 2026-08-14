# SILLON - Tutoriel, corrigé de l'exercice R 3.4.
#
# Trois graphiques assemblés dans un seul rapport PDF via pdf()/dev.off()
# (aucun package supplémentaire requis, contrairement à PdfPages en
# Python qui vient de matplotlib).
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
communes <- dbGetQuery(connexion, "SELECT reg_nom, population, densite, altitude_moyenne FROM communes_france")
dbDisconnect(connexion)

pdf(file.path(resultats, "rapport_trois_graphiques.pdf"), width = 8, height = 6)

# Histogramme en log10 plutôt qu'en échelle linéaire : la densité est
# extrêmement asymétrique (quelques communes très denses face à des
# dizaines de milliers de communes rurales) - un histogramme linéaire
# entasse alors la quasi-totalité des communes dans le tout premier
# intervalle, illisible (constaté en pratique). Mêmes conventions que le
# nuage de points ci-dessous (log = "y"), qui traite déjà ce même défaut.
hist(log10(communes$densite[communes$densite > 0]), breaks = 50,
     main = "Distribution de la densité (échelle log)", xlab = "Densité (hab/km², log10)")

par_region <- communes %>% group_by(reg_nom) %>% summarise(population_totale = sum(population))
barplot(par_region$population_totale, names.arg = par_region$reg_nom, las = 2,
        main = "Population par région", cex.names = 0.6)

plot(communes$altitude_moyenne, communes$densite, log = "y", pch = 20, col = rgb(0, 0, 0.57, 0.2),
     main = "Altitude vs densité", xlab = "Altitude moyenne (m)", ylab = "Densité (log)")

dev.off()
cat("Rapport PDF genere : rapport_trois_graphiques.pdf\n")
