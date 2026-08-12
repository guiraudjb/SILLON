# SILLON - Script R d'exemple : pipeline dplyr (sillon-demo-sirene).
#
# Un classement (top 20 divisions NAF actives) construit avec un pipeline
# dplyr classique (mutate/group_by/summarise/arrange), à partir d'une
# requête déjà agrégée côté PostgreSQL - jamais un SELECT * sur les ~43,9
# millions de lignes de sirene_etablissements. dplyr fait ici le second
# passage (calcul de la part en %, tri) sur un résultat déjà réduit à
# quelques dizaines de lignes.
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

par_secteur <- dbGetQuery(connexion, "
  SELECT LEFT(activite_principale, 2) AS division_naf, COUNT(*) AS nb
  FROM sirene_etablissements
  WHERE etat_administratif = 'A' AND activite_principale IS NOT NULL AND activite_principale != ''
  GROUP BY division_naf
")
dbDisconnect(connexion)

classement <- par_secteur %>%
  mutate(part_pct = round(100 * nb / sum(nb), 2)) %>%
  arrange(desc(nb)) %>%
  mutate(rang = row_number()) %>%
  select(rang, division_naf, nb, part_pct) %>%
  head(20)

write.csv(classement, file.path(resultats, "classement_secteurs_naf.csv"), row.names = FALSE)

cat("Top 5 divisions NAF (établissements actifs) :\n")
print(head(classement, 5))
cat(sprintf("\n%d divisions NAF analysees au total, classement complet dans classement_secteurs_naf.csv\n",
            nrow(par_secteur)))
