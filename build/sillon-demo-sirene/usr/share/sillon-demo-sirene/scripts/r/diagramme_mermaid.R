# SILLON - Script R d'exemple : diagramme Mermaid (sillon-demo-sirene).
#
# Même principe que diagramme_mermaid.py : le bac à sable n'a ni Node.js
# ni Chromium (§7.7/§8.7), impossible d'y rendre une image Mermaid - le
# script écrit seulement le texte (aucun package requis, cat/writeLines
# suffisent), rendu ensuite côté navigateur par SILLON (mermaid.min.js
# vendorisé, bouton "Diagrammes" dans l'onglet Suivi).
#
# Agrégation SQL, jamais un SELECT * sur les ~43,9 millions de lignes.
suppressMessages({
  library(DBI)
  library(RPostgreSQL)
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
par_caractere <- dbGetQuery(connexion, "
  SELECT CASE caractere_employeur WHEN 'O' THEN 'Employeur' WHEN 'N' THEN 'Non employeur' ELSE 'Non renseigne' END AS categorie,
         COUNT(*) AS nb
  FROM sirene_etablissements WHERE etat_administratif = 'A'
  GROUP BY categorie ORDER BY nb DESC
")
dbDisconnect(connexion)

lignes <- c("pie showData title Établissements actifs, employeurs ou non")
for (i in seq_len(nrow(par_caractere))) {
  lignes <- c(lignes, sprintf('    "%s" : %d', par_caractere$categorie[i], par_caractere$nb[i]))
}

writeLines(lignes, file.path(resultats, "repartition_employeurs.mmd"))

cat(sprintf("Diagramme Mermaid produit pour %d categories.\n", nrow(par_caractere)))
