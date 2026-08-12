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

hist(communes$densite, breaks = 50, main = "Distribution de la densite", xlab = "Densite (hab/km2)")

par_region <- communes %>% group_by(reg_nom) %>% summarise(population_totale = sum(population))
barplot(par_region$population_totale, names.arg = par_region$reg_nom, las = 2,
        main = "Population par region", cex.names = 0.6)

plot(communes$altitude_moyenne, communes$densite, log = "y", pch = 20, col = rgb(0, 0, 0.57, 0.2),
     main = "Altitude vs densite", xlab = "Altitude moyenne (m)", ylab = "Densite (log)")

dev.off()
cat("Rapport PDF genere : rapport_trois_graphiques.pdf\n")
