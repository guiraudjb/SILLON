# SILLON — Guide utilisateur

### Prise en main complète, onglet par onglet

---

## À propos de ce guide

Ce guide illustre, captures d'écran réelles à l'appui, l'ensemble des fonctionnalités de SILLON telles qu'elles se présentent à l'écran. Il complète deux autres documents disponibles depuis la modale « À propos » de l'application :

- Le **cahier des charges**, qui détaille précisément le comportement attendu de chaque fonctionnalité.
- Le **guide d'installation administrateur**, pour la mise en place du serveur.

Les captures de ce guide ont été réalisées avec le compte de démonstration du paquet optionnel `sillon-tutoriel` (jeu de données réel de communes françaises) et avec les fichiers d'exemple pour la cartographie et les graphiques, également téléchargeables depuis la modale « À propos ».

---

## Connexion

L'accès à SILLON se fait par adresse email professionnelle et mot de passe — aucune inscription libre, les comptes sont créés par un administrateur (voir la fin de ce guide).

![Écran de connexion](01_connexion.jpg)

Une fois connecté, la barre d'onglets s'affiche en haut de l'application. Les onglets **Bases**, **Travaux**, **Import**, **Scripts** et **Suivi** sont réservés aux données de travail ; **Carto**, **Graphiques** et **Diagrammes** permettent de produire manuellement des visualisations ; **Administration** n'apparaît que pour un compte administrateur.

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

Six échelles sont disponibles (monde, France métropolitaine, région, département, EPCI, commune), avec sélection en cascade pour les échelles les plus fines. La colonne « code INSEE » est exclue des colonnes proposables comme valeur, pour ne jamais cartographier le code lui-même par erreur.

![Carte choroplèthe départementale](15_carto_carte.jpg)

Une fois les étiquettes activées, un réglage fin est disponible : taille, filtre par nom ou code, filtre avancé sur une autre colonne, et deux curseurs pilotant la répartition automatique des étiquettes pour éviter les recouvrements.

La coloration propose, en plus d'une palette par défaut et de deux dégradés divergents prédéfinis, un dégradé personnalisé construit à partir des couleurs du système de design de l'État : une teinte, puis une nuance de cette teinte, du plus clair au plus soutenu, choisies indépendamment pour les valeurs basses et les valeurs hautes.

![Nuancier de couleurs à deux niveaux](16_carto_nuancier.jpg)

La carte s'exporte ensuite en image PNG.

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

## Modale « À propos »

Accessible à tout moment depuis l'en-tête de l'application, elle regroupe la documentation technique téléchargeable (guide administrateur, cahier des charges, ce guide utilisateur), ainsi que les fichiers d'exemple pour les onglets Carto et Graphiques.

![Modale À propos](19_a_propos.jpg)

Pour le compte de démonstration du paquet optionnel `sillon-tutoriel`, une section « Formation » supplémentaire donne accès au tutoriel complet et aux corrigés téléchargeables de tous ses exercices.

---

## Panneau Administration

Réservé aux comptes de profil administrateur, ce panneau permet de gérer l'ensemble de la plateforme sans passer par la ligne de commande.

**Comptes utilisateurs** : création (email, profil, mot de passe provisoire), désactivation, réinitialisation de mot de passe.

![Gestion des comptes utilisateurs](20_administration_comptes.jpg)

**Quotas** : réglage des limites globales de la plateforme (connexions simultanées, mémoire et CPU par conteneur de script, taille maximale des fichiers, durée maximale d'un job...).

![Réglage des quotas](21_administration_quotas.jpg)

**Journal d'audit** : traçabilité de toutes les actions sensibles (création de compte, création ou suppression de base ou de table, modification de mot de passe...), consultable directement depuis l'interface.

![Journal d'audit](22_administration_audit.jpg)

---

## Pour aller plus loin

- Le **cahier des charges** détaille le comportement attendu de chaque fonctionnalité, la sécurité, les performances et le packaging de la plateforme.
- Le **guide d'installation administrateur** couvre la mise en place du serveur, la sauvegarde et la maintenance courante.
- Si le paquet optionnel `sillon-tutoriel` est installé, le **tutoriel** propose une prise en main progressive en SQL, Python et R sur un vrai jeu de données, avec tous les corrigés téléchargeables.

Ces trois documents sont accessibles depuis la modale « À propos » de l'application.
