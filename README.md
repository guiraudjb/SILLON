# SILLON — Système d'Interrogation Local et Libre d'Outils Numériques

**SILLON** est une plateforme locale d'analyse de données destinée aux data analystes d'une direction. Elle permet d'importer des fichiers CSV, de les transformer en bases PostgreSQL correctement typées, de les interroger en SQL libre ou via des scripts Python/R exécutés côté serveur, et de partager les résultats — sans dépendre du lac de données national.

Le détail complet des choix fonctionnels et techniques est consigné dans [`SILLON_cahier_des_charges.md`](./SILLON_cahier_des_charges.md).

---

## Fonctionnalités principales

- **Import CSV qualifié** : dépôt d'un fichier, détection automatique de l'encodage/délimiteur, proposition de type par colonne, création automatique d'une table avec indexation différée.
- **Base personnelle par agent** : une base par utilisateur habilité, enrichie à chaque import.
- **Requêtes SQL libres** : éditeur SQL, export des résultats en CSV UTF-8 en flux (jamais chargé entièrement en mémoire).
- **Scripts Python/R** : exécution isolée côté serveur (conteneur éphémère, lecture seule, utilisateur non privilégié), pour les traitements que le SQL seul ne couvre pas.
- **File d'attente et notifications** : les traitements longs sont mis en file, avec mail à l'utilisateur une fois le résultat prêt.
- **Partage entre utilisateurs** : un agent peut ouvrir sa base en lecture à d'autres utilisateurs de la direction, avec autorisation distincte pour l'exécution de scripts.

---

## Architecture et stack technologique

Philosophie identique aux autres applicatifs de la direction : pas de framework front-end lourd, sécurité et droits d'accès portés nativement par PostgreSQL plutôt que reconstruits en couche applicative.

| Composant | Technologie | Rôle |
|---|---|---|
| Système d'exploitation | Debian 13 (Trixie) | Socle de déploiement |
| Base de données | PostgreSQL 17 | Catalogue applicatif, bases utilisateurs, RBAC natif |
| API de requêtage | PostgREST | Authentification JWT, CRUD sur le catalogue |
| Orchestrateur | Python (Flask/Gunicorn) | Création des bases, SQL libre, import CSV, partage multi-base |
| Travailleur de file | Python | Consommation des jobs de script, lancement des conteneurs |
| Isolation des scripts | Conteneurs Podman éphémères | Image Debian 13 dédiée (Python/pandas/matplotlib, R/tidyverse), lecture seule, réseau interne |
| Serveur web / Proxy | Nginx | Terminaison SSL, reverse proxy, limitation de débit |
| Sécurité systémique | Fail2Ban | Anti-bruteforce sur l'authentification |
| Front-end | Vanilla JS + HTML5 + DSFR | SPA, export CSV côté client |

---

## Paquets Debian

| Paquet | Rôle |
|---|---|
| `sillon-server` | Paquet principal (obligatoire) — PostgreSQL, Nginx, API de requêtage, catalogue applicatif |
| `sillon-orchestrateur` | Création/suppression des bases, requêtes SQL libres, import CSV, partage |
| `sillon-worker` | Consommation de la file d'attente, lancement des conteneurs d'exécution |
| `sillon-image-execution` | Image figée (Python/R) utilisée pour l'exécution des scripts |

Ordre d'installation recommandé : `sillon-server` → `sillon-orchestrateur` → `sillon-worker` → `sillon-image-execution`.

---

## Sécurité

- Authentification par jeton signé, cookie `HttpOnly ; Secure ; SameSite=Strict`.
- Un rôle PostgreSQL personnel par utilisateur, `NOLOGIN` en permanence : les droits d'accès sont portés nativement par le moteur de base de données. Un compte désactivé perd immédiatement la capacité de connexion, indépendamment de la validité de son jeton.
- Scripts Python/R exécutés dans des conteneurs éphémères (utilisateur non privilégié, système de fichiers en lecture seule, réseau interne), avec des identifiants PostgreSQL éphémères générés pour la seule durée du conteneur — le rôle redevient `NOLOGIN` immédiatement après, succès ou échec confondus.
- Aucune installation de paquet à la volée dans les conteneurs de script : l'image est figée et versionnée.
- Anti-bruteforce Nginx + Fail2Ban sur l'authentification.
- Journal d'audit immuable au niveau du moteur de base de données.

Aucun mécanisme de sauvegarde n'est porté par l'application : la protection contre la perte de données relève de l'infrastructure d'hébergement de la direction.

---

## État du projet

Avant-projet basé sur le cahier des charges v1.2. Back-end, front-end et construction des paquets sont désormais tous implémentés et validés par des tests réels (base PostgreSQL jetable, vrais conteneurs) au fil du développement.

| Composant | État |
|---|---|
| `usr/share/sillon/schema.sql` (catalogue applicatif) | Implémenté et testé : RBAC natif, authentification JWT, partage inter-utilisateurs, file d'attente, audit immuable, identifiants éphémères pour l'exécution de scripts |
| `sillon-server` (`postinst`/`postrm`/`prerm`) | Implémenté : génération des secrets, déploiement/migration du schéma, configuration Nginx et Fail2Ban, jamais de recréation destructive à la mise à jour |
| `sillon-orchestrateur` (`orchestrateur.py`) | Implémenté et testé : SQL libre, export CSV en flux, import CSV avec indexation différée, dépôt de scripts, partage multi-base |
| `sillon-worker` (`worker.py`) | Implémenté et testé avec de vrais conteneurs : consommation de la file, identifiants éphémères, arrêt gracieux et remise en file sur interruption |
| `sillon-image-execution` (`Dockerfile`) | Implémenté, construit et testé (Python/pandas/matplotlib et R/tidyverse fonctionnels, isolation lecture seule/non-root vérifiée par de vrais conteneurs) |
| Front-end (`index.html`/`app.js`/`styles.css`) | Implémenté : authentification, gestion des bases, SQL libre, import CSV, dépôt de scripts, administration et audit — vanilla JS + DSFR, sans bundler |
| Construction des paquets `.deb` (`build/build.sh`) | Implémenté : vendoring de PostgREST (vérifié par SHA256) et de l'image d'exécution Podman ; les 4 paquets (`sillon-server`, `sillon-orchestrateur`, `sillon-worker`, `sillon-image-execution`) ont été construits avec succès |

Reste à faire avant mise en production : test d'import à grande échelle avec un jeu de données réel, initialisation du dépôt git (`Upload.sh` suppose un remote `origin/main` qui n'existe pas encore), et les points de vigilance ci-dessous.

### Points de vigilance — validés sur la cible réelle (VM de test, 2026-08-11)

Les tests menés pendant le développement ont utilisé des substituts faute d'accès à l'environnement cible (PostgreSQL 15 jetable au lieu de 17 packagé, Docker au lieu de Podman). Deux points avaient été identifiés comme nécessitant une vérification explicite sur un Debian 13 + Podman réel :

- La convention de casse des clés JSON de `podman network inspect` — **caduc** : cette logique d'extraction de sous-réseau n'existe plus dans le code, remplacée par la détection d'adresse hôte via route (§7.7, cf. `sillon-worker/DEBIAN/postinst`), tranchée par un déploiement réel antérieur.
- Le comportement de `--pids-limit` sous cgroups v2 avec `cgroup_manager = cgroupfs` — **validé** : testé sur la VM cible (Debian 13, Podman 5.4.2), la limite est bien appliquée par le runtime (`pids.max` correctement propagé au conteneur, dépassement effectivement bloqué), pas seulement déclarée.
