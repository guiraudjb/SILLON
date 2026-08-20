# SILLON — Guide utilisateur

### Prise en main complète, onglet par onglet

---

## À propos de ce guide

Ce guide illustre, captures d'écran réelles à l'appui, l'ensemble des fonctionnalités de SILLON telles qu'elles se présentent à l'écran. Il complète trois autres documents disponibles depuis la modale « À propos » de l'application :

- Le **guide d'installation administrateur**, pour la mise en place du serveur.
- La **nomenclature logicielle (SBOM)**, qui recense l'ensemble des composants installés (réglementation NIS2).
- Le **cahier des charges**, qui détaille précisément le comportement attendu de chaque fonctionnalité.

Les captures de ce guide ont été réalisées avec le jeu de données réel de communes françaises du paquet optionnel `sillon-tutoriel` (partagé automatiquement avec tout compte dès lors que ce paquet est installé, plus besoin du compte de démonstration) et avec les fichiers d'exemple pour la cartographie, les graphiques et les représentations DSFR, également téléchargeables depuis la modale « À propos ».

---

## Connexion

L'accès à SILLON se fait par adresse email professionnelle et mot de passe — aucune inscription libre, les comptes sont créés par un administrateur (voir la fin de ce guide).

![Écran de connexion](01_connexion.jpg)

Une fois connecté, la barre d'onglets s'affiche en haut de l'application. Les onglets **Bases**, **Travaux**, **Import**, **Scripts** et **Suivi** sont réservés aux données de travail ; **Carto**, **Graphiques**, **Diagrammes** et **Représentations DSFR** permettent de produire manuellement des visualisations ; **Administration** n'apparaît que pour un compte administrateur.

---

## Onglet « Bases »

Point d'entrée de l'application : c'est ici que se choisit la base de données sur laquelle porteront les onglets Travaux et Scripts. Chaque utilisateur dispose d'une base personnelle (créée automatiquement au premier import), activée par défaut si elle existe.

![Liste des bases](02_bases_liste.jpg)

Le bouton « Tables » d'une base déplie la liste de ses tables, avec le nombre de lignes, la taille occupée et la date du dernier import — utile pour vérifier en un coup d'œil l'état d'une base sans écrire de requête.

![Liste des tables d'une base](03_bases_tables.jpg)

Une base peut aussi être partagée en lecture seule avec un collègue, ou supprimée (avec une confirmation renforcée demandant de ressaisir son nom).

---

## Onglet « Travaux »

L'onglet pour interroger une base en SQL libre, avec coloration syntaxique et auto-complétion des noms de table et de colonne (`Ctrl+Espace`).

![Éditeur de requête SQL](04_travaux_requete.jpg)

Le résultat s'affiche sous forme de tableau, avec le nombre de lignes et le temps d'exécution. Un résultat de lecture peut être exporté en CSV, ou directement réutilisé dans les onglets Carto et Graphiques sans avoir à le retéléscharger.

![Résultat d'une requête](05_travaux_resultat.jpg)

Un historique des requêtes précédentes et une liste de requêtes enregistrées (nommées, réutilisables) sont disponibles sous l'éditeur.

---

## Onglet « Import »

Pour transformer un fichier CSV en table PostgreSQL correctement typée, sans écrire de SQL. Le fichier peut être déposé par glisser-déposer ou par sélection classique.

![Analyse d'un fichier CSV](06_import_analyse.jpg)

Après analyse, SILLON détecte l'encodage, le délimiteur et propose un type pour chaque colonne (Texte, Entier, Décimal, Date...) — modifiable avant validation. Un contrôle de cohérence est ensuite passé sur tout le fichier (pas seulement l'aperçu), avec la possibilité d'exclure les lignes en anomalie plutôt que d'annuler tout l'import.

![Colonnes détectées et types proposés](07_import_colonnes.jpg)

Un fichier n'est pas toujours déjà sur son poste : le bouton « Importer depuis data.gouv.fr », en haut de l'onglet, ouvre une recherche par mot-clé dans le catalogue national et propose directement les ressources exploitables des jeux de données trouvés (CSV, TXT, JSON ou ZIP — converti automatiquement, sans action à faire). Le fichier choisi est téléchargé côté serveur (avec la vitesse et le volume déjà reçu affichés pendant le transfert) puis rejoint automatiquement la même analyse de colonnes que pour un dépôt manuel. Si le jeu de données propose aussi des fichiers PDF de documentation, un menu permet d'en joindre un (facultatif) à la table qui sera créée — consultable ensuite depuis sa fiche.

![Recherche « population communes » depuis data.gouv.fr](25_import_datagouv.jpg)

---

## Onglet « Scripts »

Pour exécuter du code Python ou R dans un environnement isolé, avec une connexion à la base cible fournie automatiquement (aucun identifiant à saisir dans le script). La liste des librairies disponibles est affichée avant tout dépôt, pour éviter les échecs liés à une dépendance manquante.

![Onglet Scripts](08_scripts_onglet.jpg)

Avant tout lancement, le contenu du script s'ouvre dans un éditeur pour relecture ou modification — jamais envoyé tel quel. Sans fichier déposé, un squelette de connexion pré-rempli évite de partir d'une page blanche.

![Éditeur de script vierge](09_scripts_editeur.jpg)

Avec un fichier déposé, l'éditeur affiche son contenu réel :

![Éditeur avec un script réel chargé](10_scripts_editeur_charge.jpg)

Le script est ensuite mis en file d'attente et son exécution se suit depuis l'onglet Suivi.

---

## Onglet « Suivi »

Vue consolidée de tous les traitements de l'utilisateur — imports, requêtes longues, scripts — filtrable par type et par statut, rafraîchie automatiquement toutes les 10 secondes, paginée par 10 lignes.

![Liste des traitements](11_suivi_liste.jpg)

Pour un script terminé, les fichiers de résultat qui s'y prêtent (tableaux CSV, images, diagrammes Mermaid) se prévisualisent directement dans le navigateur, sans télécharger l'archive complète.

![Aperçu d'un résultat CSV](12_suivi_apercu_csv.jpg)

![Aperçu d'un résultat image](14_suivi_apercu_image.jpg)

En bas de liste, la pagination indique la page courante et le nombre total de traitements.

![Pagination de l'onglet Suivi](13_suivi_pagination.jpg)

---

## Onglet « Carto »

Pour produire manuellement une carte choroplèthe à partir d'un jeu de données par code INSEE, sans passer par un script. La source des données est au choix : un fichier CSV déposé, ou le résultat de la dernière requête de lecture exécutée dans l'onglet Travaux.

La carte se règle en deux temps : le **cadrage** fixe l'étendue géographique globale (monde, France métropolitaine, région, département, EPCI ou commune), et le **détail** fixe le niveau réellement colorié à l'intérieur de ce cadrage — par exemple un cadrage « Région » avec un détail « Département » dessine une seule région, chaque département colorié individuellement ; un cadrage « France métropolitaine » avec un détail « EPCI » colorie tout le pays intercommunalité par intercommunalité. Les options de détail proposées dépendent du cadrage choisi, et une sélection en cascade (région puis, si besoin, département) affine le cadrage pour les échelles les plus fines. La colonne « code INSEE » est exclue des colonnes proposables comme valeur, pour ne jamais cartographier le code lui-même par erreur.

![Cadrage régional, détail départemental, légende verticale à droite](23_carto_cadrage_detail.jpg)

Une fois les étiquettes activées, un réglage fin est disponible : taille, filtre par nom ou code, filtre avancé sur une autre colonne, et deux curseurs pilotant la répartition automatique des étiquettes pour éviter les recouvrements.

La légende est optionnelle et se positionne librement (bas à droite ou à gauche à l'horizontale, ou verticale centrée à droite ou à gauche) — utile pour la dégager d'une zone chargée de la carte. La coloration propose les 19 teintes du système de design de l'État en dégradé continu, deux dégradés divergents prédéfinis, ou un dégradé entièrement personnalisé construit à partir de ces mêmes teintes : une teinte, puis une nuance de cette teinte, du plus clair au plus soutenu, choisies indépendamment pour les valeurs basses et les valeurs hautes.

![Position de la légende et palette de couleurs DSFR](24_carto_legende_palette.jpg)

![Nuancier de couleurs à deux niveaux (dégradé personnalisé)](16_carto_nuancier.jpg)

La génération d'une carte peut prendre quelques secondes (le fond communal, le plus détaillé, pèse une vingtaine de mégaoctets) : un indicateur de chargement s'affiche pendant ce temps et les boutons de l'onglet sont désactivés pour éviter un double clic. La carte s'exporte ensuite en image PNG.

---

## Onglet « Graphiques »

Pour produire un graphique à partir de données tabulaires (même mécanisme de source de données que l'onglet Carto). La première colonne fournit les étiquettes, les colonnes suivantes autant de séries.

Six types de graphique sont proposés (barres, barres horizontales, ligne, anneau, aires polaires, radar), avec une palette de couleurs choisie parmi les teintes du système de design de l'État.

![Graphique radar](17_graphiques_radar.jpg)

Un tableau de données équivalent au graphique, masqué visuellement mais accessible aux technologies d'assistance, est généré automatiquement à chaque rendu (conformité RGAA). Le graphique s'exporte en image PNG.

---

## Onglet « Diagrammes »

Un éditeur de diagrammes Mermaid en texte libre, avec aperçu mis à jour automatiquement après une courte pause de saisie. Une bibliothèque de modèles de départ (processus métier, séquence, architecture, planning, matrice de risques...) évite de partir d'une syntaxe vierge.

![Diagramme de séquence](18_diagrammes_sequence.jpg)

Le diagramme s'exporte en image PNG (repli au format SVG si la conversion échoue). Cet onglet n'a volontairement pas de lien avec un fichier CSV : la syntaxe Mermaid ne s'y prête pas nativement, contrairement aux onglets Carto et Graphiques.

---

## Onglet « Représentations DSFR »

Pour produire manuellement cinq blocs visuels du système de design de l'État, édités par formulaire avec un aperçu mis à jour en direct (pas de bouton « Actualiser », ces rendus étant légers) et exportés en image PNG. Les 19 palettes de couleurs DSFR sont partagées avec les onglets Carto et Graphiques.

**Mise en exergue** : un titre et un texte, avec un liseré de couleur.

![Mise en exergue](26_representations_exergue.jpg)

**Chiffre clé** : une valeur mise en avant (ex. « 34 868 ») et son texte explicatif.

![Chiffre clé](27_representations_chiffre.jpg)

**Citation** : le texte, l'auteur, sa fonction, et un portrait optionnel (à gauche, à droite, ou absent) déposé en image.

![Citation avec portrait](28_representations_citation.jpg)

**Tableau** : le contenu de chaque cellule se saisit dans une grille dédiée, qui se redimensionne en conservant les valeurs déjà saisies — ou s'alimente directement, comme pour Carto et Graphiques, depuis un fichier CSV déposé ou le résultat de la dernière requête SQL exécutée dans l'onglet Travaux.

![Tableau alimenté par une requête SQL](29_representations_tableau.jpg)

**Frise chronologique** : un fichier CSV (colonnes date/étape, titre, description optionnelle), orientation horizontale ou verticale, et une case à cocher par étape pour choisir celles à afficher. Un fichier d'exemple (`frise.csv`) est téléchargeable depuis la modale « À propos », aux côtés des exemples déjà disponibles pour Carto et Graphiques.

![Frise chronologique](30_representations_frise.jpg)

---

## Modale « À propos »

Accessible à tout moment depuis l'en-tête de l'application, elle regroupe la documentation technique téléchargeable (guide administrateur, nomenclature logicielle SBOM, cahier des charges, ce guide utilisateur), ainsi que les fichiers d'exemple pour les onglets Carto, Graphiques et Représentations DSFR.

![Modale À propos](19_a_propos.jpg)

Si le paquet optionnel `sillon-tutoriel` est installé, une section « Formation » supplémentaire donne accès au tutoriel complet et aux corrigés téléchargeables de tous ses exercices — visible pour **tout compte**, plus seulement celui de démonstration : le jeu de données du tutoriel lui est partagé automatiquement (onglet Bases), chacun le suit avec sa propre identité.

---

## Panneau Administration

Réservé aux comptes de profil administrateur, ce panneau permet de gérer l'ensemble de la plateforme sans passer par la ligne de commande.

**Comptes utilisateurs** : création (email, profil, mot de passe provisoire), désactivation, réinitialisation de mot de passe.

![Gestion des comptes utilisateurs](20_administration_comptes.jpg)

**Quotas** : réglage des limites globales de la plateforme (connexions simultanées, mémoire et CPU par conteneur de script, taille maximale des fichiers, durée maximale d'un job...).

![Réglage des quotas](21_administration_quotas.jpg)

**Proxy sortant (data.gouv.fr)** : sur une plateforme sans accès Internet direct, l'adresse d'un proxy HTTP peut être enregistrée puis testée depuis cet écran, pour que l'import depuis data.gouv.fr (onglet Import) reste utilisable.

**Journal d'audit** : traçabilité de toutes les actions sensibles (création de compte, création ou suppression de base ou de table, modification de mot de passe...), consultable directement depuis l'interface.

![Journal d'audit](22_administration_audit.jpg)

---

## Pour aller plus loin

- Le **cahier des charges** détaille le comportement attendu de chaque fonctionnalité, la sécurité, les performances et le packaging de la plateforme.
- Le **guide d'installation administrateur** couvre la mise en place du serveur, la sauvegarde et la maintenance courante.
- La **nomenclature logicielle (SBOM)** recense l'ensemble des composants installés, pour la conformité NIS2.
- Si le paquet optionnel `sillon-tutoriel` est installé, le **tutoriel** propose une prise en main progressive en SQL, Python et R sur un vrai jeu de données, avec tous les corrigés téléchargeables — avec votre propre compte, sans identifiant à part.

Ces quatre documents sont accessibles depuis la modale « À propos » de l'application.
