<!-- title: SILLON — Nomenclature des composants logiciels (SBOM) -->

# Nomenclature des composants logiciels (SBOM) — SILLON

| Champ | Valeur |
|---|---|
| Date | 19 août 2026 |
| Périmètre | Les 6 paquets `.deb` de SILLON (`build/build.sh`), leur fermeture de dépendances Debian complète, et les composants vendorisés hors `dpkg` |
| Méthode | Dépendances directes relevées dans `DEBIAN/control` et le `Dockerfile` de l'image d'exécution ; fermeture transitive et versions résolues **directement depuis la VM de test SILLON réelle** (`192.168.122.114`, Debian 13/Trixie), reprise en conditions réelles après une première version basée sur des dépôts Debian génériques |
| Format | Ce document (synthèse de lecture) + `sbom/sillon-sbom-cyclonedx.json` (référence machine-lisible, CycloneDX 1.6, 590 composants, validée sans erreur contre le schéma officiel) |
| Statut | Nomenclature établie pour appuyer les obligations de gestion de la chaîne d'approvisionnement logicielle et de gestion des vulnérabilités du règlement **NIS2** — voir « Limites » (§7) |
| Dernière mise à jour de sécurité appliquée | **19 août 2026** — PapaParse et DSFR corrigés dans `sillon-server` (0.1.28 → **0.1.29**, déployé et vérifié) ; `debian:13-slim` épinglé par digest dans `sillon-image-execution` (0.1.0 → **0.1.2**, déployé et vérifié par une exécution réelle de script après correction d'une régression de build détectée en cours de route) — voir §6.1, §7 et journal ci-dessous |

**Journal des révisions** (même journée, 19 août 2026) :

| # | Contenu |
|---|---|
| 1 | Version initiale : dépendances Debian résolues via des conteneurs Debian 13 éphémères interrogeant les dépôts génériques (VM de test alors injoignable) |
| 2 | Dépendances Debian ré-résolues **en conditions réelles** directement sur la VM de test SILLON (`192.168.122.114`, redevenue joignable) — 11 écarts de version constatés et documentés (§7, constat 7) |
| 3 | Vérification des correctifs de sécurité amont des 10 composants vendorisés (§6.1) — 1 CVE active trouvée (PapaParse) et 1 correctif de sécurité manquant (DSFR) |
| 4 | **Correction construite** : PapaParse 5.0.2 → 5.6.0 et DSFR 1.14.3 → 1.15.2 vendorisés dans `sillon-server` (nouvelle version `0.1.29`), package reconstruit et vérifié statiquement (voir §6.1 et §7, constats 8-9) |
| 5 | **Correction déployée et vérifiée en conditions réelles** : `sillon-server` 0.1.29 installé sur la VM de test (mise à niveau propre depuis 0.1.28), application réelle testée en HTTPS — connexion, chargement de toutes les ressources front, import CSV réel via PapaParse 5.6.0. Constats §7.8-7.9 clos (voir §11) |
| 6 | `FROM debian:13-slim` épinglé par empreinte de digest dans le `Dockerfile` de `sillon-image-execution` (constat §7.1) ; image reconstruite à l'identique (`sillon-image-execution` 0.1.0 → 0.1.1), `.deb` déposé sur la VM de test |
| 7 | **Régression détectée avant tout impact sur la cible** : la reconstruction 0.1.1 chargeait sans erreur sur la VM (`podman load` silencieux) mais tout script échouait aussitôt, journal vide — Docker BuildKit enveloppe par défaut l'image dans un index de provenance/attestation que `podman load` ne sait pas déplier. Corrigé en 0.1.2 (`docker build --provenance=false --sbom=false`), `build/build.sh` mis à jour pour ne plus jamais reproduire cette régression, exécution réelle vérifiée sur la VM (job `script_python` abouti) — voir §7, constat 1 |

---

## 1. Contexte

SILLON s'installe comme 6 paquets `.deb` interdépendants, sur une cible Debian 13 sans accès réseau hors dépôts Debian (proxy d'entreprise) — voir `GUIDE_INSTALLATION_ADMINISTRATEUR.md`. Cette contrainte se retrouve dans la manière dont les dépendances sont assemblées : tout ce qui n'est pas un paquet Debian officiel est vendorisé (téléchargé et embarqué) au moment du build, jamais installé à la volée sur la cible.

Le règlement NIS2 impose aux entités concernées de documenter la composition de leurs logiciels critiques (nomenclature logicielle, *Software Bill of Materials*) et d'assurer un suivi des vulnérabilités sur cette composition. Ce document — et son pendant machine-lisible `sbom/sillon-sbom-cyclonedx.json` — répond à ce besoin pour SILLON : il énumère l'intégralité des composants installés, qu'ils proviennent des dépôts Debian ou qu'ils soient vendorisés, avec leur version exacte, leur provenance et, quand elle est identifiable, leur licence.

## 2. Méthodologie

**Dépendances directes** — relevées depuis le champ `Depends` de `DEBIAN/control` de chacun des 6 paquets `.deb` construits par `build/build.sh`, et depuis le `Dockerfile` de `sillon-image-execution`.

**Fermeture transitive et versions** — résolues le 19 août 2026 directement sur la VM de test SILLON réelle (`192.168.122.114`, Debian 13/Trixie, les 5 paquets `sillon-*` installables déjà présents — voir §5), en conditions réelles plutôt que par simulation :

- **Univers hôte** (195 paquets) : `dpkg-query -W` exécuté sur la VM elle-même, filtré sur l'ensemble des paquets réellement tirés par les dépendances directes de `sillon-server`, `sillon-orchestrateur`, `sillon-worker`, `sillon-tutoriel`.
- **Univers de l'image d'exécution** (378 paquets) : l'image `sillon-image-execution:latest` réellement chargée sur cette VM (`podman load`, jamais reconstruite sur cible) a été inspectée directement — extraction du fichier `var/lib/dpkg/status` de la couche `apt-get install` de l'image (`/usr/lib/sillon/image-execution.tar`), sans exécuter le conteneur.

Une première résolution, antérieure, s'appuyait sur des conteneurs Debian 13 éphémères interrogeant les dépôts Debian génériques (la VM étant alors injoignable) : 11 versions différaient de l'état réel de la VM (dérive de correctifs de sécurité Debian publiés entre-temps, dans les deux sens — voir §7, constat 7).

**Composants vendorisés** — inventoriés manuellement à partir des scripts de vendoring de `build/build.sh` (PostgREST, somme SHA-256 incluse) et des en-têtes de licence présents dans chaque bibliothèque JS livrée sous `var/www/html/SILLON/`.

**Hors périmètre de cette nomenclature** (voir « Limites », §7) : scan de vulnérabilités connues (CVE) sur les composants listés, revue légale exhaustive des licences.

## 3. Synthèse chiffrée

| Indicateur | Valeur |
|---|---|
| Paquets `.deb` SILLON | 6 |
| Paquets Debian résolus — univers hôte | 195 (134 paquets source uniques) |
| Paquets Debian résolus — univers image d'exécution | 378 (314 paquets source uniques) |
| Composants vendorisés hors `dpkg` | 10 (1 binaire, 9 bibliothèques JS) |
| Images conteneur figées | 1 (`image-execution.tar`, 384 Mo) |
| Licences front identifiées | 10/10, toutes permissives (MIT, BSD-3-Clause, ISC) |
| CVE connue affectant un composant vendorisé | 0 — **CVE-2020-36649** (PapaParse) détectée puis **corrigée le 19/08/2026**, voir §6.1 et §7 |
| Composants vendorisés en retard sur un correctif de sécurité amont | 0/10 (PapaParse et DSFR corrigés le 19/08/2026 — `sillon-server` 0.1.29) |
| Composants totaux (fichier CycloneDX) | 590 |

## 4. Architecture et chaîne de dépendances

Les 6 paquets SILLON dépendent les uns des autres en chaîne, mais traversent surtout **deux univers de paquets Debian distincts et hermétiques** : celui de l'hôte, et celui, isolé, de l'image conteneur d'exécution. Le passage de l'un à l'autre ne se fait pas par une dépendance `apt` mais par un `podman run` au moment de l'exécution — un point qui ne se lit pas dans les fichiers `control`.

![Chaîne de dépendances des 6 paquets SILLON, univers hôte et univers image d'exécution](diagramme_dependances.png){width=17cm}

## 5. Les 6 paquets SILLON

| Paquet | Version | Arch. | Dépend de (Debian) | Dépend de (SILLON) | Vendorisé |
|---|---|---|---|---|---|
| `sillon-server` | 0.1.29 | amd64 | postgresql-17, nginx, openssl, sudo, fail2ban | — | PostgREST 14.8, 9 libs JS, DSFR 1.15.2 |
| `sillon-orchestrateur` | 0.1.13 | all | python3-flask, python3-psycopg2, python3-jwt, gunicorn, python3-ijson | sillon-server | — |
| `sillon-worker` | 0.1.3 | all | podman | sillon-orchestrateur | — |
| `sillon-image-execution` | 0.1.2 | amd64 | *(univers séparé, §4)* | sillon-worker | image podman figée (384 Mo), base épinglée par digest |
| `sillon-tutoriel` | 0.1.0 | all | python3 | sillon-server, sillon-orchestrateur, sillon-worker, sillon-image-execution | — |
| `sillon-demo-sirene` | 0.1.4 | all | python3 | sillon-tutoriel | — |

Les 5 premiers paquets sont installés sur la VM de test SILLON (`192.168.122.114`) avec exactement ces versions (`dpkg -l`, 19 août 2026) — `sillon-server` en particulier a été mis à niveau de 0.1.28 vers **0.1.29** le jour même, une fois la correction §6.1/§7 construite et vérifiée (voir §11 pour le détail de cette vérification en conditions réelles). `sillon-demo-sirene` n'y est pas installé (paquet optionnel, voir §11).

**Empreintes SHA-256 des `.deb` construits** (traçabilité de provenance) :

| Paquet | SHA-256 |
|---|---|
| `sillon-server_0.1.29_amd64.deb` | `c3e22be05165d5b4eb77372b82d7df07b830da4643bb21637e10fe16fe1aed6a` |
| `sillon-orchestrateur_0.1.13_all.deb` | `d408ecaa5481a026759a2602e8267e2a8be4465e7c0df2768ca283870f1b07da` |
| `sillon-worker_0.1.3_all.deb` | `a8543ce76490628c2d4ccfdf42472ae88afa6f68230c7c3759bd6ac9e8a1cc34` |
| `sillon-image-execution_0.1.2_amd64.deb` | `2609a036c884f9ede1692c11ce77a060c3fec23064bb58c04babeb4193dfa4a3` |
| `sillon-tutoriel_0.1.0_all.deb` | `7ab74cb735c3167eeb659c3f9b835458504b9800e246fa05a3eab79a64fac203` |
| `sillon-demo-sirene_0.1.4_all.deb` | `f0fabc42fa3f9d7949cde4f4f87ed942bbda421f73ff0c8a35059533d01055b4` |

## 6. Composants vendorisés hors `dpkg`

Dix composants ne transitent par aucun gestionnaire de paquets Debian et sont livrés directement dans les paquets `.deb` : à suivre manuellement pour toute mise à jour de sécurité amont, puisqu'aucun `apt upgrade` ne les couvrira.

| Composant | Version | Nature | Licence | Provenance / intégrité |
|---|---|---|---|---|
| PostgREST | 14.8 | Binaire officiel, statiquement lié (`usr/lib/sillon/postgrest`, `sillon-server`) | MIT | SHA-256 vérifié au build (`172a55ae…9909f0b0`) |
| PapaParse | 5.6.0 | Bibliothèque JS — parsing CSV (front) | MIT | En clair dans le fichier livré ; tarball npm vérifié par sha1 (`738e01b2…f14c46`) |
| Chart.js | 4.5.1 | Bibliothèque JS — graphiques (front) | MIT | En clair dans le fichier livré |
| chartjs-plugin-datalabels | 2.2.0 | Plugin Chart.js (front) | MIT | Confirmée via le registre npm (le fichier minifié livré n'affiche pas la licence en tête) |
| D3.js | 7.9.0 | Bibliothèque JS — visualisation (front) | ISC | En clair dans le fichier livré |
| Topojson-client | 3.0.2 | Bibliothèque JS — cartographie (front) | BSD-3-Clause | En clair dans le fichier livré |
| Mermaid | 11.16.1 | Bibliothèque JS — diagrammes (front) | MIT | En clair dans le fichier livré |
| html2canvas | 1.4.1 | Bibliothèque JS — export image (front) | MIT | En clair dans le fichier livré |
| CodeMirror | 5.65.21 | Éditeur SQL intégré (front) | MIT | En clair dans le fichier livré |
| DSFR | 1.15.2 | Système de Design de l'État (front) | **Etalab-2.0** (renommée depuis MIT en 1.15.1 par l'éditeur, sans changement de fond ; usage réservé aux entités administratives, domaine `.gouv.fr` — `LICENSE.md` vendoré) | `SPDX-License-Identifier` en tête de fichier ; tarball npm vérifié par sha1 (`6c9e5d87…6784446`) |

### 6.1 État des correctifs de sécurité amont (vérifié le 19 août 2026, corrigé le même jour)

Chacun des 10 composants a été confronté à sa dernière version amont (registre npm / releases GitHub) et à la base de vulnérabilités [OSV.dev](https://osv.dev/) interrogée sur la version exacte vendorisée. Les deux composants en retard sur un correctif de sécurité (PapaParse, DSFR) ont été mis à jour et reconstruits le jour même (`sillon-server` 0.1.28 → **0.1.29**) — le tableau ci-dessous reflète l'état **après correction**.

| Composant | Vendorisé | Dernière version amont | État | CVE connue affectant la version vendorisée |
|---|---|---|---|---|
| PostgREST | 14.8 | 14.17 (13/08/2026) | En retard de 9 versions ; aucune mention de correctif de sécurité dans le changelog sur cet intervalle | Aucune connue |
| **PapaParse** | ~~5.0.2~~ **5.6.0** | 5.6.0 | **Corrigé le 19/08/2026** (était vulnérable, très en retard) | **CVE-2020-36649** — déni de service par expression régulière (ReDoS) dans `parse()`, CVSS 3.1 7,5 (élevé). Affectait 5.0.2, corrigé en amont depuis 5.2.0 ; la version vendorisée est désormais la dernière amont |
| Chart.js | 4.5.1 | 4.5.1 | À jour | Aucune |
| chartjs-plugin-datalabels | 2.2.0 | 2.2.0 (déc. 2022) | À jour (dernière release du projet) | Aucune |
| D3.js | 7.9.0 | 7.9.0 | À jour | Aucune |
| Topojson-client | 3.0.2 | 3.1.0 (nov. 2019) | Légèrement en retard (projet dormant depuis 2019) | Aucune |
| Mermaid | 11.16.1 | 11.17.0 | En retard d'un correctif, mais contient déjà les correctifs de **toutes** les CVE connues du projet (5 corrigées précisément en 11.16.1 : DoS, pollution de prototype, injection CSS) | Aucune affectant cette version |
| html2canvas | 1.4.1 | 1.4.1 (janv. 2022) | À jour (dernière release du projet) | Aucune |
| CodeMirror 5 | 5.65.21 | 5.65.21 (dernière version de la branche 5.x, succédée par CodeMirror 6) | À jour | Aucune |
| **DSFR** | ~~1.14.3~~ **1.15.2** | 1.15.2 (12/08/2026) | **Corrigé le 19/08/2026** (était en retard de 4 versions mineures) | Pas de CVE publiée ; la version **1.15.0** (17/07/2026, correctif de sanitisation du chargement de pictogrammes SVG) est désormais intégrée |

## 7. Points d'attention pour la conformité NIS2

| # | Constat | Sévérité | Concerne | Recommandation |
|---|---|---|---|---|
| 1 | `FROM debian:13-slim` dans le `Dockerfile` de l'image d'exécution n'était pas épinglé par empreinte (`@sha256:…`) | **Corrigé et déployé (19/08/2026)** | `sillon-image-execution` | Épinglé sur `debian:13-slim@sha256:3a39a059…8f94f258` ; `sillon-image-execution` 0.1.0 → 0.1.2 (voir constat 1bis pour une régression intermédiaire), installé sur la VM de test et vérifié par l'exécution réelle d'un script (job `script_python` abouti, `pandas`/`numpy` fonctionnels) |
| 1 bis | **Régression de build découverte pendant la correction du constat 1, avant qu'elle n'affecte durablement la cible** : la première reconstruction (`sillon-image-execution` 0.1.1) se chargeait sans erreur sur la VM (`podman load` silencieux, taille et manifeste d'apparence normale) mais tout script y échouait aussitôt, avec un journal d'exécution vide — signe que le conteneur ne démarrait jamais. Cause : Docker BuildKit (utilisé en substitution de `podman build`, absent sur la machine de build) enveloppe désormais l'image par défaut dans un index de provenance/attestation que `podman load` sur la cible ne sait pas déplier correctement | **Corrigé (19/08/2026)** | `sillon-image-execution`, `build/build.sh` | Rebuild avec `docker build --provenance=false --sbom=false` (0.1.2) ; `build/build.sh` modifié pour appliquer systématiquement ces options quand `docker` est utilisé en substitution de `podman`, afin qu'un futur build complet ne reproduise pas cette régression |
| 2 | `sillon-demo-sirene` télécharge ~2,86 Go depuis data.gouv.fr à l'installation — seule dérogation du système au principe « aucun accès réseau hors dépôts Debian » ; rien dans le paquet lui-même n'empêche techniquement son installation en production | Attention | `sillon-demo-sirene` | Exclure explicitement ce paquet de tout inventaire ou déploiement de production dans les procédures d'exploitation |
| 3 | `r-cran-tidyverse` entraîne des paquets R à capacité réseau (`httr`, `curl`, `googledrive`, `googlesheets4`) à l'intérieur de l'image d'exécution ; l'isolation réseau effective repose entièrement sur les options d'exécution imposées par `worker.py` (`--network` interne), pas sur l'absence de ces bibliothèques | À noter | `sillon-image-execution` | Défense en profondeur souhaitable si cette garantie d'exécution venait à être retirée par erreur |
| 4 | Aucun fichier `LICENSE` à la racine du dépôt pour le code propre à SILLON (les 6 paquets `.deb`) | À noter | Dépôt SILLON | À clarifier si cette nomenclature ou le code doivent circuler en dehors de l'organisation |
| 5 | PostgREST vendorisé avec intégrité vérifiée par somme SHA-256 à la construction | Conforme | `sillon-server` | Bonne pratique de traçabilité de provenance pour un composant vendorisé binaire, à reconduire |
| 6 | Les 10 composants vendorisés hors `dpkg` portent tous une licence permissive identifiée (MIT, BSD-3-Clause, ISC) | Conforme | Front (`sillon-server`) | Aucun risque de licence contaminante (copyleft) identifié côté front |
| 7 | 11 des 573 paquets Debian relevés sur la VM de test (192.168.122.114) portent une version différente de celle publiée sur les dépôts Debian au 19 août 2026 (`util-linux` et ses paquets liés en retard d'un correctif de sécurité ; `libexpat1` inversement plus récent sur les dépôts que sur la VM) | À noter | Univers hôte et image d'exécution | Confirme l'absence de mise à jour automatique (`apt upgrade`) de la cible depuis son installation — comportement attendu en production, mais à surveiller explicitement via le suivi de vulnérabilités (§8) plutôt que de supposer une cible toujours à jour |
| 8 | PapaParse 5.0.2 (vendorisé) était concerné par CVE-2020-36649 (déni de service par expression régulière, CVSS 3.1 7,5/10), corrigée en amont depuis la version 5.2.0 (novembre 2020) — la version vendorisée en était dépourvue depuis près de 6 ans | **Corrigé et déployé (19/08/2026)** | `sillon-server` (front, import CSV) | Mis à jour vers PapaParse 5.6.0, `sillon-server` reconstruit en 0.1.29, **installé sur la VM de test et vérifié** : import CSV réel abouti (§11) |
| 9 | DSFR 1.14.3 (vendorisé) n'intégrait pas le correctif de sécurité publié en 1.15.0 (17/07/2026 — sanitisation du chargement de pictogrammes SVG en ligne, contournement d'injection sur IE11) | **Corrigé et déployé (19/08/2026)** | `sillon-server` (front) | Mis à jour vers DSFR 1.15.2, `sillon-server` reconstruit en 0.1.29, **installé sur la VM de test et vérifié** : rendu conforme, aucune régression visuelle (§11) |

## 8. Veille des vulnérabilités

**Paquets Debian** — Les 573 paquets Debian de cette nomenclature (§9) sont, par construction, tous suivis par le [Debian Security Tracker](https://security-tracker.debian.org/tracker/) via leur paquet source (colonne « Paquet source Debian » des tableaux ci-dessous). Rapprocher périodiquement `sbom/sillon-sbom-cyclonedx.json` de ce suivi — ou d'un scanner tel que `grype`/`trivy` exécuté directement contre la VM cible — constitue la mécanique de veille recommandée pour couvrir l'obligation de gestion des vulnérabilités du règlement NIS2.

**Composants vendorisés hors `dpkg`** — ne bénéficient d'aucun suivi automatique de type `apt upgrade` et ont été vérifiés manuellement le 19 août 2026 (résultat détaillé en §6.1) : dernière version amont relevée via l'API GitHub et le registre npm, vulnérabilités connues interrogées via [OSV.dev](https://osv.dev/) sur la version exacte vendorisée de chaque composant JS, changelog/notes de version parcourus pour PostgREST et DSFR à la recherche de correctifs de sécurité non couverts par une CVE publiée. Un composant s'est révélé concerné par une CVE active (PapaParse, constat §7.8) et un autre par un correctif de sécurité non couvert par une CVE (DSFR, constat §7.9) ; les deux ont été corrigés le jour même (§6.1). Cette vérification n'est pas automatisée : à rejouer manuellement à chaque nouvelle version de `sillon-server`, ou via un outil dédié (`npm audit`, `osv-scanner`) intégré au build si cette charge devient récurrente.

## 9. Annexe A — Paquets Debian résolus, univers hôte (195)

| Paquet | Version | Paquet source Debian | Arch. |
|---|---|---|---|
| `adduser` | 3.152 | `adduser` | all |
| `apt` | 3.0.3 | `apt` | amd64 |
| `base-files` | 13.8+deb13u6 | `base-files` | amd64 |
| `base-passwd` | 3.6.7 | `base-passwd` | amd64 |
| `bash` | 5.2.37-2+b9 | `bash` | amd64 |
| `bsdutils` | 1:2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `conmon` | 2.1.12-4 | `conmon` | amd64 |
| `containernetworking-plugins` | 1.1.1+ds1-3+b17 | `golang-github-containernetworking-plugins` | amd64 |
| `coreutils` | 9.7-3 | `coreutils` | amd64 |
| `crun` | 1.21-1 | `crun` | amd64 |
| `dash` | 0.5.12-12 | `dash` | amd64 |
| `debconf` | 1.5.91 | `debconf` | all |
| `debian-archive-keyring` | 2025.1 | `debian-archive-keyring` | all |
| `debianutils` | 5.23.2 | `debianutils` | amd64 |
| `diffutils` | 1:3.10-4 | `diffutils` | amd64 |
| `dirmngr` | 2.4.7-21+deb13u1+b4 | `gnupg2` | amd64 |
| `dpkg` | 1.22.22 | `dpkg` | amd64 |
| `fail2ban` | 1.1.0-8 | `fail2ban` | all |
| `findutils` | 4.10.0-3 | `findutils` | amd64 |
| `gcc-14-base` | 14.2.0-19 | `gcc-14` | amd64 |
| `gnupg` | 2.4.7-21+deb13u1 | `gnupg2` | all |
| `gnupg-l10n` | 2.4.7-21+deb13u1 | `gnupg2` | all |
| `golang-github-containers-common` | 0.62.2+ds1-2 | `golang-github-containers-common` | all |
| `golang-github-containers-image` | 5.34.2-1 | `golang-github-containers-image` | all |
| `gpg` | 2.4.7-21+deb13u1+b4 | `gnupg2` | amd64 |
| `gpg-agent` | 2.4.7-21+deb13u1+b4 | `gnupg2` | amd64 |
| `gpgconf` | 2.4.7-21+deb13u1+b4 | `gnupg2` | amd64 |
| `gpgsm` | 2.4.7-21+deb13u1+b4 | `gnupg2` | amd64 |
| `grep` | 3.11-4 | `grep` | amd64 |
| `gunicorn` | 23.0.0-1 | `gunicorn` | all |
| `gzip` | 1.13-1 | `gzip` | amd64 |
| `hostname` | 3.25 | `hostname` | amd64 |
| `init-system-helpers` | 1.69~deb13u1 | `init-system-helpers` | all |
| `iproute2` | 6.15.0-1 | `iproute2` | amd64 |
| `iptables` | 1.8.11-2 | `iptables` | amd64 |
| `libacl1` | 2.3.2-2+b1 | `acl` | amd64 |
| `libapparmor1` | 4.1.0-1 | `apparmor` | amd64 |
| `libapt-pkg7.0` | 3.0.3 | `apt` | amd64 |
| `libassuan9` | 3.0.2-2 | `libassuan` | amd64 |
| `libatomic1` | 14.2.0-19 | `gcc-14` | amd64 |
| `libattr1` | 1:2.5.2-3 | `attr` | amd64 |
| `libaudit-common` | 1:4.0.2-2 | `audit` | all |
| `libaudit1` | 1:4.0.2-2+b2 | `audit` | amd64 |
| `libblkid1` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `libbpf1` | 1:1.5.0-3 | `libbpf` | amd64 |
| `libbsd0` | 0.12.2-2 | `libbsd` | amd64 |
| `libbz2-1.0` | 1.0.8-6 | `bzip2` | amd64 |
| `libc-bin` | 2.41-12+deb13u3 | `glibc` | amd64 |
| `libc-l10n` | 2.41-12+deb13u3 | `glibc` | all |
| `libc6` | 2.41-12+deb13u3 | `glibc` | amd64 |
| `libcap-ng0` | 0.8.5-4+b1 | `libcap-ng` | amd64 |
| `libcap2` | 1:2.75-10+deb13u1+b1 | `libcap2` | amd64 |
| `libcap2-bin` | 1:2.75-10+deb13u1+b1 | `libcap2` | amd64 |
| `libcom-err2` | 1.47.2-3+b11 | `e2fsprogs` | amd64 |
| `libcrypt1` | 1:4.4.38-1 | `libxcrypt` | amd64 |
| `libdb5.3t64` | 5.3.28+dfsg2-9 | `db5.3` | amd64 |
| `libdebconfclient0` | 0.280 | `cdebconf` | amd64 |
| `libedit2` | 3.1-20250104-1 | `libedit` | amd64 |
| `libelf1t64` | 0.192-4 | `elfutils` | amd64 |
| `libexpat1` | 2.8.2-1~deb13u1 | `expat` | amd64 |
| `libffi8` | 3.4.8-2 | `libffi` | amd64 |
| `libgcc-s1` | 14.2.0-19 | `gcc-14` | amd64 |
| `libgcrypt20` | 1.11.0-7+deb13u1 | `libgcrypt20` | amd64 |
| `libgdbm-compat4t64` | 1.24-2 | `gdbm` | amd64 |
| `libgdbm6t64` | 1.24-2 | `gdbm` | amd64 |
| `libglib2.0-0t64` | 2.84.4-3~deb13u3 | `glib2.0` | amd64 |
| `libgmp10` | 2:6.3.0+dfsg-3 | `gmp` | amd64 |
| `libgnutls30t64` | 3.8.9-3+deb13u4 | `gnutls28` | amd64 |
| `libgpg-error0` | 1.51-4 | `libgpg-error` | amd64 |
| `libgpgme11t64` | 1.24.2-3 | `gpgme1.0` | amd64 |
| `libgssapi-krb5-2` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libhogweed6t64` | 3.10.1-1 | `nettle` | amd64 |
| `libicu76` | 76.1-4 | `icu` | amd64 |
| `libidn2-0` | 2.3.8-2 | `libidn2` | amd64 |
| `libio-pty-perl` | 1:1.20-1+b3 | `libio-pty-perl` | amd64 |
| `libip4tc2` | 1.8.11-2 | `iptables` | amd64 |
| `libip6tc2` | 1.8.11-2 | `iptables` | amd64 |
| `libipc-run-perl` | 20231003.0-2 | `libipc-run-perl` | all |
| `libjson-perl` | 4.10000-1 | `libjson-perl` | all |
| `libk5crypto3` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libkeyutils1` | 1.6.3-6 | `keyutils` | amd64 |
| `libkrb5-3` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libkrb5support0` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libksba8` | 1.6.7-2+b1 | `libksba` | amd64 |
| `liblastlog2-2` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `libldap2` | 2.6.10+dfsg-1 | `openldap` | amd64 |
| `libllvm19` | 1:19.1.7-3+b1 | `llvm-toolchain-19` | amd64 |
| `liblz4-1` | 1.10.0-4 | `lz4` | amd64 |
| `liblzma5` | 5.8.1-1+deb13u1 | `xz-utils` | amd64 |
| `libmd0` | 1.1.0-2+b1 | `libmd` | amd64 |
| `libmnl0` | 1.0.5-3 | `libmnl` | amd64 |
| `libmount1` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `libncursesw6` | 6.5+20250216-2 | `ncurses` | amd64 |
| `libnetfilter-conntrack3` | 1.1.0-1 | `libnetfilter-conntrack` | amd64 |
| `libnettle8t64` | 3.10.1-1 | `nettle` | amd64 |
| `libnfnetlink0` | 1.0.2-3 | `libnfnetlink` | amd64 |
| `libnftnl11` | 1.2.9-1 | `libnftnl` | amd64 |
| `libnpth0t64` | 1.8-3 | `npth` | amd64 |
| `libp11-kit0` | 0.25.5-3 | `p11-kit` | amd64 |
| `libpam-modules` | 1.7.0-5 | `pam` | amd64 |
| `libpam-modules-bin` | 1.7.0-5 | `pam` | amd64 |
| `libpam-runtime` | 1.7.0-5 | `pam` | all |
| `libpam0g` | 1.7.0-5 | `pam` | amd64 |
| `libpcre2-8-0` | 10.46-1~deb13u1 | `pcre2` | amd64 |
| `libperl5.40` | 5.40.1-6 | `perl` | amd64 |
| `libpq5` | 17.11-0+deb13u1 | `postgresql-17` | amd64 |
| `libproc2-0` | 2:4.0.4-9 | `procps` | amd64 |
| `libpython3-stdlib` | 3.13.5-1 | `python3-defaults` | amd64 |
| `libpython3.13-minimal` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `libpython3.13-stdlib` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `libreadline8t64` | 8.2-6 | `readline` | amd64 |
| `libsasl2-2` | 2.1.28+dfsg1-9 | `cyrus-sasl2` | amd64 |
| `libsasl2-modules-db` | 2.1.28+dfsg1-9 | `cyrus-sasl2` | amd64 |
| `libseccomp2` | 2.6.0-2 | `libseccomp` | amd64 |
| `libselinux1` | 3.8.1-1 | `libselinux` | amd64 |
| `libsemanage-common` | 3.8.1-1 | `libsemanage` | all |
| `libsemanage2` | 3.8.1-1 | `libsemanage` | amd64 |
| `libsepol2` | 3.8.1-1 | `libsepol` | amd64 |
| `libsmartcols1` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `libsqlite3-0` | 3.46.1-7+deb13u1 | `sqlite3` | amd64 |
| `libssl3t64` | 3.5.6-1~deb13u2 | `openssl` | amd64 |
| `libstdc++6` | 14.2.0-19 | `gcc-14` | amd64 |
| `libsubid5` | 1:4.17.4-2 | `shadow` | amd64 |
| `libsystemd0` | 257.13-1~deb13u1 | `systemd` | amd64 |
| `libtasn1-6` | 4.20.0-2+deb13u1 | `libtasn1-6` | amd64 |
| `libtext-charwidth-perl` | 0.04-11+b4 | `libtext-charwidth-perl` | amd64 |
| `libtext-wrapi18n-perl` | 0.06-10 | `libtext-wrapi18n-perl` | all |
| `libtinfo6` | 6.5+20250216-2 | `ncurses` | amd64 |
| `libtirpc-common` | 1.3.6+ds-1 | `libtirpc` | all |
| `libtirpc3t64` | 1.3.6+ds-1 | `libtirpc` | amd64 |
| `libudev1` | 257.13-1~deb13u1 | `systemd` | amd64 |
| `libunistring5` | 1.3-2 | `libunistring` | amd64 |
| `libuuid1` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `libxml2` | 2.12.7+dfsg+really2.9.14-2.1+deb13u3 | `libxml2` | amd64 |
| `libxslt1.1` | 1.1.35-1.2+deb13u3 | `libxslt` | amd64 |
| `libxtables12` | 1.8.11-2 | `iptables` | amd64 |
| `libxxhash0` | 0.8.3-2 | `xxhash` | amd64 |
| `libyajl2` | 2.1.0-5+b2 | `yajl` | amd64 |
| `libz3-4` | 4.13.3-1 | `z3` | amd64 |
| `libzstd1` | 1.5.7+dfsg-1 | `libzstd` | amd64 |
| `locales` | 2.41-12+deb13u3 | `glibc` | all |
| `login` | 1:4.16.0-2+really2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `login.defs` | 1:4.17.4-2 | `shadow` | all |
| `mawk` | 1.3.4.20250131-1 | `mawk` | amd64 |
| `media-types` | 13.0.0 | `media-types` | all |
| `mount` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `ncurses-base` | 6.5+20250216-2 | `ncurses` | all |
| `ncurses-bin` | 6.5+20250216-2 | `ncurses` | amd64 |
| `netavark` | 1.14.0-2 | `netavark` | amd64 |
| `netbase` | 6.5 | `netbase` | all |
| `nginx` | 1.26.3-3+deb13u7 | `nginx` | amd64 |
| `nginx-common` | 1.26.3-3+deb13u7 | `nginx` | all |
| `openssl` | 3.5.6-1~deb13u2 | `openssl` | amd64 |
| `openssl-provider-legacy` | 3.5.6-1~deb13u2 | `openssl` | amd64 |
| `passwd` | 1:4.17.4-2 | `shadow` | amd64 |
| `perl` | 5.40.1-6 | `perl` | amd64 |
| `perl-base` | 5.40.1-6 | `perl` | amd64 |
| `perl-modules-5.40` | 5.40.1-6 | `perl` | all |
| `pinentry-curses` | 1.3.1-2 | `pinentry` | amd64 |
| `podman` | 5.4.2+ds1-2+b2 | `podman` | amd64 |
| `postgresql-17` | 17.11-0+deb13u1 | `postgresql-17` | amd64 |
| `postgresql-client-17` | 17.11-0+deb13u1 | `postgresql-17` | amd64 |
| `postgresql-client-common` | 278 | `postgresql-common` | all |
| `postgresql-common` | 278 | `postgresql-common` | all |
| `postgresql-common-dev` | 278 | `postgresql-common` | all |
| `procps` | 2:4.0.4-9 | `procps` | amd64 |
| `python3` | 3.13.5-1 | `python3-defaults` | amd64 |
| `python3-blinker` | 1.9.0-1 | `blinker` | all |
| `python3-click` | 8.2.0+0.really.8.1.8-1 | `python-click` | all |
| `python3-flask` | 3.1.1-1 | `flask` | all |
| `python3-gunicorn` | 23.0.0-1 | `gunicorn` | all |
| `python3-ijson` | 3.4.0-1 | `python-ijson` | amd64 |
| `python3-itsdangerous` | 2.2.0-2 | `python-itsdangerous` | all |
| `python3-jinja2` | 3.1.6-1 | `jinja2` | all |
| `python3-jwt` | 2.10.1-2+deb13u1 | `pyjwt` | all |
| `python3-markupsafe` | 2.1.5-1+b3 | `markupsafe` | amd64 |
| `python3-minimal` | 3.13.5-1 | `python3-defaults` | amd64 |
| `python3-packaging` | 25.0-1 | `python-packaging` | all |
| `python3-psycopg2` | 2.9.10-1+b1 | `psycopg2` | amd64 |
| `python3-systemd` | 235-1+b6 | `python-systemd` | amd64 |
| `python3-werkzeug` | 3.1.3-2 | `python-werkzeug` | all |
| `python3.13` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `python3.13-minimal` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `readline-common` | 8.2-6 | `readline` | all |
| `sed` | 4.9-2+deb13u1 | `sed` | amd64 |
| `sensible-utils` | 0.0.25 | `sensible-utils` | all |
| `sqv` | 1.3.0-3+b2 | `rust-sequoia-sqv` | amd64 |
| `ssl-cert` | 1.1.3 | `ssl-cert` | all |
| `sudo` | 1.9.16p2-3+deb13u2 | `sudo` | amd64 |
| `sysvinit-utils` | 3.14-4 | `sysvinit` | amd64 |
| `tar` | 1.35+dfsg-3.1 | `tar` | amd64 |
| `tzdata` | 2026b-0+deb13u1 | `tzdata` | all |
| `ucf` | 3.0052 | `ucf` | all |
| `util-linux` | 2.41.5-0+deb13u1 | `util-linux` | amd64 |
| `zlib1g` | 1:1.3.dfsg+really1.3.1-1+b1 | `zlib` | amd64 |

## 10. Annexe B — Paquets Debian résolus, univers image d'exécution (378)

| Paquet | Version | Paquet source Debian | Arch. |
|---|---|---|---|
| `apt` | 3.0.3 | `apt` | amd64 |
| `base-files` | 13.8+deb13u6 | `base-files` | amd64 |
| `base-passwd` | 3.6.7 | `base-passwd` | amd64 |
| `bash` | 5.2.37-2+b9 | `bash` | amd64 |
| `blt` | 2.5.3+dfsg-8 | `blt` | amd64 |
| `bsdutils` | 1:2.41-5 | `util-linux` | amd64 |
| `ca-certificates` | 20250419 | `ca-certificates` | all |
| `coreutils` | 9.7-3 | `coreutils` | amd64 |
| `dash` | 0.5.12-12 | `dash` | amd64 |
| `debconf` | 1.5.91 | `debconf` | all |
| `debian-archive-keyring` | 2025.1 | `debian-archive-keyring` | all |
| `debianutils` | 5.23.2 | `debianutils` | amd64 |
| `diffutils` | 1:3.10-4 | `diffutils` | amd64 |
| `dpkg` | 1.22.22 | `dpkg` | amd64 |
| `findutils` | 4.10.0-3 | `findutils` | amd64 |
| `fontconfig` | 2.15.0-2.3 | `fontconfig` | amd64 |
| `fontconfig-config` | 2.15.0-2.3 | `fontconfig` | amd64 |
| `fonts-dejavu-core` | 2.37-8 | `fonts-dejavu` | all |
| `fonts-dejavu-mono` | 2.37-8 | `fonts-dejavu` | all |
| `fonts-font-awesome` | 5.0.10+really4.7.0~dfsg-4.1 | `fonts-font-awesome` | all |
| `fonts-glyphicons-halflings` | 1.009~3.4.1+dfsg-6 | `twitter-bootstrap3` | all |
| `fonts-lyx` | 2.4.3-1 | `lyx` | all |
| `fonts-mathjax` | 2.7.9+dfsg-1 | `mathjax` | all |
| `gcc-14-base` | 14.2.0-19 | `gcc-14` | amd64 |
| `grep` | 3.11-4 | `grep` | amd64 |
| `gzip` | 1.13-1 | `gzip` | amd64 |
| `hostname` | 3.25 | `hostname` | amd64 |
| `init-system-helpers` | 1.69~deb13u1 | `init-system-helpers` | all |
| `javascript-common` | 12+nmu1 | `javascript-common` | all |
| `libacl1` | 2.3.2-2+b1 | `acl` | amd64 |
| `libapt-pkg7.0` | 3.0.3 | `apt` | amd64 |
| `libatomic1` | 14.2.0-19 | `gcc-14` | amd64 |
| `libattr1` | 1:2.5.2-3 | `attr` | amd64 |
| `libaudit-common` | 1:4.0.2-2 | `audit` | all |
| `libaudit1` | 1:4.0.2-2+b2 | `audit` | amd64 |
| `libblas3` | 3.12.1-6 | `lapack` | amd64 |
| `libblkid1` | 2.41-5 | `util-linux` | amd64 |
| `libbrotli1` | 1.1.0-2+b7 | `brotli` | amd64 |
| `libbsd0` | 0.12.2-2 | `libbsd` | amd64 |
| `libbz2-1.0` | 1.0.8-6 | `bzip2` | amd64 |
| `libc-bin` | 2.41-12+deb13u3 | `glibc` | amd64 |
| `libc6` | 2.41-12+deb13u3 | `glibc` | amd64 |
| `libcairo2` | 1.18.4-1+b1 | `cairo` | amd64 |
| `libcap-ng0` | 0.8.5-4+b1 | `libcap-ng` | amd64 |
| `libcap2` | 1:2.75-10+deb13u1+b1 | `libcap2` | amd64 |
| `libcom-err2` | 1.47.2-3+b11 | `e2fsprogs` | amd64 |
| `libcrypt1` | 1:4.4.38-1 | `libxcrypt` | amd64 |
| `libcurl4t64` | 8.14.1-2+deb13u4 | `curl` | amd64 |
| `libdatrie1` | 0.2.13-3+b1 | `libdatrie` | amd64 |
| `libdb5.3t64` | 5.3.28+dfsg2-9 | `db5.3` | amd64 |
| `libdebconfclient0` | 0.280 | `cdebconf` | amd64 |
| `libdeflate0` | 1.23-2 | `libdeflate` | amd64 |
| `libexpat1` | 2.8.2-1~deb13u1 | `expat` | amd64 |
| `libffi8` | 3.4.8-2 | `libffi` | amd64 |
| `libfontconfig1` | 2.15.0-2.3 | `fontconfig` | amd64 |
| `libfreetype6` | 2.13.3+dfsg-1+deb13u1 | `freetype` | amd64 |
| `libfribidi0` | 1.0.16-1 | `fribidi` | amd64 |
| `libgcc-s1` | 14.2.0-19 | `gcc-14` | amd64 |
| `libgcrypt20` | 1.11.0-7+deb13u1 | `libgcrypt20` | amd64 |
| `libgfortran5` | 14.2.0-19 | `gcc-14` | amd64 |
| `libglib2.0-0t64` | 2.84.4-3~deb13u3 | `glib2.0` | amd64 |
| `libgmp10` | 2:6.3.0+dfsg-3 | `gmp` | amd64 |
| `libgnutls30t64` | 3.8.9-3+deb13u4 | `gnutls28` | amd64 |
| `libgomp1` | 14.2.0-19 | `gcc-14` | amd64 |
| `libgpg-error0` | 1.51-4 | `libgpg-error` | amd64 |
| `libgraphite2-3` | 1.3.14-2+deb13u1 | `graphite2` | amd64 |
| `libgssapi-krb5-2` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libharfbuzz0b` | 10.2.0-1+deb13u1 | `harfbuzz` | amd64 |
| `libhogweed6t64` | 3.10.1-1 | `nettle` | amd64 |
| `libice6` | 2:1.1.1-1 | `libice` | amd64 |
| `libicu76` | 76.1-4 | `icu` | amd64 |
| `libidn2-0` | 2.3.8-2 | `libidn2` | amd64 |
| `libimagequant0` | 2.18.0-1+b2 | `libimagequant` | amd64 |
| `libjbig0` | 2.1-6.1+b2 | `jbigkit` | amd64 |
| `libjpeg62-turbo` | 1:2.1.5-4 | `libjpeg-turbo` | amd64 |
| `libjs-bootstrap` | 3.4.1+dfsg-6 | `twitter-bootstrap3` | all |
| `libjs-bootstrap4` | 4.6.2+dfsg-1 | `twitter-bootstrap4` | all |
| `libjs-d3` | 3.5.17-4 | `d3` | all |
| `libjs-es5-shim` | 4.6.7-2 | `node-es5-shim` | all |
| `libjs-highlight.js` | 9.18.5+dfsg1-2 | `highlight.js` | all |
| `libjs-jquery` | 3.6.1+dfsg+~3.5.14-1 | `node-jquery` | all |
| `libjs-jquery-datatables` | 1.11.5+dfsg-2 | `datatables.js` | all |
| `libjs-jquery-selectize.js` | 0.12.6+dfsg-1.1 | `libjs-jquery-selectize.js` | all |
| `libjs-jquery-ui` | 1.13.2+dfsg-1 | `jqueryui` | all |
| `libjs-json` | 0~20221030+~1.0.8-1 | `json-js` | all |
| `libjs-mathjax` | 2.7.9+dfsg-1 | `mathjax` | all |
| `libjs-microplugin.js` | 0.0.3+dfsg-1.1 | `libjs-microplugin.js` | all |
| `libjs-modernizr` | 3.13.0-0.1 | `modernizr` | all |
| `libjs-popper.js` | 1.16.1+ds-6 | `popper.js` | all |
| `libjs-prettify` | 2015.12.04+dfsg-1.1 | `prettify.js` | all |
| `libjs-sifter.js` | 0.6.0+dfsg-3 | `libjs-sifter.js` | all |
| `libjs-twitter-bootstrap-datepicker` | 1.3.1+dfsg1-4.1 | `libjs-twitter-bootstrap-datepicker` | all |
| `libk5crypto3` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libkeyutils1` | 1.6.3-6 | `keyutils` | amd64 |
| `libkrb5-3` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `libkrb5support0` | 1.21.3-5+deb13u1 | `krb5` | amd64 |
| `liblapack3` | 3.12.1-6 | `lapack` | amd64 |
| `liblastlog2-2` | 2.41-5 | `util-linux` | amd64 |
| `liblcms2-2` | 2.16-2+deb13u2 | `lcms2` | amd64 |
| `libldap2` | 2.6.10+dfsg-1 | `openldap` | amd64 |
| `liblerc4` | 4.0.0+ds-5 | `lerc` | amd64 |
| `liblua5.4-0` | 5.4.7-1+b2 | `lua5.4` | amd64 |
| `liblz4-1` | 1.10.0-4 | `lz4` | amd64 |
| `liblzma5` | 5.8.1-1+deb13u1 | `xz-utils` | amd64 |
| `libmd0` | 1.1.0-2+b1 | `libmd` | amd64 |
| `libmount1` | 2.41-5 | `util-linux` | amd64 |
| `libncursesw6` | 6.5+20250216-2 | `ncurses` | amd64 |
| `libnettle8t64` | 3.10.1-1 | `nettle` | amd64 |
| `libnghttp2-14` | 1.64.0-1.1+deb13u1 | `nghttp2` | amd64 |
| `libnghttp3-9` | 1.8.0-1 | `nghttp3` | amd64 |
| `libnuma1` | 2.0.19-1 | `numactl` | amd64 |
| `libopenjp2-7` | 2.5.3-2.1~deb13u2 | `openjpeg2` | amd64 |
| `libp11-kit0` | 0.25.5-3 | `p11-kit` | amd64 |
| `libpam-modules` | 1.7.0-5 | `pam` | amd64 |
| `libpam-modules-bin` | 1.7.0-5 | `pam` | amd64 |
| `libpam-runtime` | 1.7.0-5 | `pam` | all |
| `libpam0g` | 1.7.0-5 | `pam` | amd64 |
| `libpango-1.0-0` | 1.56.3-1 | `pango1.0` | amd64 |
| `libpangocairo-1.0-0` | 1.56.3-1 | `pango1.0` | amd64 |
| `libpangoft2-1.0-0` | 1.56.3-1 | `pango1.0` | amd64 |
| `libpaper-utils` | 2.2.5-0.3+b2 | `libpaper` | amd64 |
| `libpaper2` | 2.2.5-0.3+b2 | `libpaper` | amd64 |
| `libpcre2-8-0` | 10.46-1~deb13u1 | `pcre2` | amd64 |
| `libpixman-1-0` | 0.44.0-3 | `pixman` | amd64 |
| `libpng16-16t64` | 1.6.48-1+deb13u5 | `libpng1.6` | amd64 |
| `libpq5` | 17.11-0+deb13u1 | `postgresql-17` | amd64 |
| `libproc2-0` | 2:4.0.4-9 | `procps` | amd64 |
| `libpsl5t64` | 0.21.2-1.1+b1 | `libpsl` | amd64 |
| `libpython3-stdlib` | 3.13.5-1 | `python3-defaults` | amd64 |
| `libpython3.13-minimal` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `libpython3.13-stdlib` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `libqhull-r8.0` | 2020.2-6+b2 | `qhull` | amd64 |
| `libraqm0` | 0.10.2-1 | `raqm` | amd64 |
| `libreadline8t64` | 8.2-6 | `readline` | amd64 |
| `librtmp1` | 2.4+20151223.gitfa8646d.1-2+b5 | `rtmpdump` | amd64 |
| `libsasl2-2` | 2.1.28+dfsg1-9 | `cyrus-sasl2` | amd64 |
| `libsasl2-modules-db` | 2.1.28+dfsg1-9 | `cyrus-sasl2` | amd64 |
| `libseccomp2` | 2.6.0-2 | `libseccomp` | amd64 |
| `libselinux1` | 3.8.1-1 | `libselinux` | amd64 |
| `libsemanage-common` | 3.8.1-1 | `libsemanage` | all |
| `libsemanage2` | 3.8.1-1 | `libsemanage` | amd64 |
| `libsepol2` | 3.8.1-1 | `libsepol` | amd64 |
| `libsharpyuv0` | 1.5.0-0.1 | `libwebp` | amd64 |
| `libsm6` | 2:1.2.6-1 | `libsm` | amd64 |
| `libsmartcols1` | 2.41-5 | `util-linux` | amd64 |
| `libsqlite3-0` | 3.46.1-7+deb13u1 | `sqlite3` | amd64 |
| `libssh2-1t64` | 1.11.1-1+deb13u1 | `libssh2` | amd64 |
| `libssl3t64` | 3.5.6-1~deb13u2 | `openssl` | amd64 |
| `libstdc++6` | 14.2.0-19 | `gcc-14` | amd64 |
| `libsystemd0` | 257.13-1~deb13u1 | `systemd` | amd64 |
| `libtasn1-6` | 4.20.0-2+deb13u1 | `libtasn1-6` | amd64 |
| `libtcl8.6` | 8.6.16+dfsg-1 | `tcl8.6` | amd64 |
| `libtext-charwidth-perl` | 0.04-11+b4 | `libtext-charwidth-perl` | amd64 |
| `libtext-wrapi18n-perl` | 0.06-10 | `libtext-wrapi18n-perl` | all |
| `libthai-data` | 0.1.29-2 | `libthai` | all |
| `libthai0` | 0.1.29-2+b1 | `libthai` | amd64 |
| `libtiff6` | 4.7.0-3+deb13u3 | `tiff` | amd64 |
| `libtinfo6` | 6.5+20250216-2 | `ncurses` | amd64 |
| `libtirpc-common` | 1.3.6+ds-1 | `libtirpc` | all |
| `libtirpc3t64` | 1.3.6+ds-1 | `libtirpc` | amd64 |
| `libtk8.6` | 8.6.16-1 | `tk8.6` | amd64 |
| `libudev1` | 257.13-1~deb13u1 | `systemd` | amd64 |
| `libunistring5` | 1.3-2 | `libunistring` | amd64 |
| `libuuid1` | 2.41-5 | `util-linux` | amd64 |
| `libuv1t64` | 1.50.0-2 | `libuv1` | amd64 |
| `libwebp7` | 1.5.0-0.1 | `libwebp` | amd64 |
| `libwebpdemux2` | 1.5.0-0.1 | `libwebp` | amd64 |
| `libwebpmux3` | 1.5.0-0.1 | `libwebp` | amd64 |
| `libx11-6` | 2:1.8.12-1 | `libx11` | amd64 |
| `libx11-data` | 2:1.8.12-1 | `libx11` | all |
| `libxau6` | 1:1.0.11-1 | `libxau` | amd64 |
| `libxcb-render0` | 1.17.0-2+b1 | `libxcb` | amd64 |
| `libxcb-shm0` | 1.17.0-2+b1 | `libxcb` | amd64 |
| `libxcb1` | 1.17.0-2+b1 | `libxcb` | amd64 |
| `libxdmcp6` | 1:1.1.5-1 | `libxdmcp` | amd64 |
| `libxext6` | 2:1.3.4-1+b3 | `libxext` | amd64 |
| `libxft2` | 2.3.6-1+b4 | `xft` | amd64 |
| `libxml2` | 2.12.7+dfsg+really2.9.14-2.1+deb13u3 | `libxml2` | amd64 |
| `libxrender1` | 1:0.9.12-1 | `libxrender` | amd64 |
| `libxslt1.1` | 1.1.35-1.2+deb13u3 | `libxslt` | amd64 |
| `libxss1` | 1:1.2.3-1+b3 | `libxss` | amd64 |
| `libxt6t64` | 1:1.2.1-1.2+b2 | `libxt` | amd64 |
| `libxxhash0` | 0.8.3-2 | `xxhash` | amd64 |
| `libyaml-0-2` | 0.2.5-2 | `libyaml` | amd64 |
| `libzopfli1` | 1.0.3-3 | `zopfli` | amd64 |
| `libzstd1` | 1.5.7+dfsg-1 | `libzstd` | amd64 |
| `littler` | 0.3.21-1 | `littler` | all |
| `login` | 1:4.16.0-2+really2.41-5 | `util-linux` | amd64 |
| `login.defs` | 1:4.17.4-2 | `shadow` | all |
| `mawk` | 1.3.4.20250131-1 | `mawk` | amd64 |
| `media-types` | 13.0.0 | `media-types` | all |
| `mount` | 2.41-5 | `util-linux` | amd64 |
| `ncurses-base` | 6.5+20250216-2 | `ncurses` | all |
| `ncurses-bin` | 6.5+20250216-2 | `ncurses` | amd64 |
| `netbase` | 6.5 | `netbase` | all |
| `node-bootstrap-sass` | 3.4.3-2 | `node-bootstrap-sass` | all |
| `node-html5shiv` | 3.7.3+dfsg-5 | `node-html5shiv` | all |
| `node-normalize.css` | 8.0.1-5 | `node-normalize.css` | all |
| `openssl` | 3.5.6-1~deb13u2 | `openssl` | amd64 |
| `openssl-provider-legacy` | 3.5.6-1~deb13u2 | `openssl` | amd64 |
| `pandoc` | 3.1.11.1+ds-2 | `pandoc` | amd64 |
| `pandoc-data` | 3.1.11.1-3 | `haskell-pandoc` | all |
| `passwd` | 1:4.17.4-2 | `shadow` | amd64 |
| `perl-base` | 5.40.1-6 | `perl` | amd64 |
| `procps` | 2:4.0.4-9 | `procps` | amd64 |
| `python-matplotlib-data` | 3.10.1+dfsg1-4 | `matplotlib` | all |
| `python3` | 3.13.5-1 | `python3-defaults` | amd64 |
| `python3-attr` | 25.3.0-1 | `python-attrs` | all |
| `python3-brotli` | 1.1.0-2+b7 | `brotli` | amd64 |
| `python3-contourpy` | 1.3.1-1+b1 | `contourpy` | amd64 |
| `python3-cycler` | 0.12.1-1 | `python-cycler` | all |
| `python3-dateutil` | 2.9.0-4 | `python-dateutil` | all |
| `python3-decorator` | 5.2.1-2 | `python-decorator` | all |
| `python3-et-xmlfile` | 2.0.0-1 | `python-et-xmlfile` | all |
| `python3-fonttools` | 4.57.0-1+deb13u1 | `fonttools` | amd64 |
| `python3-fs` | 2.4.16-7 | `python-fs` | all |
| `python3-kiwisolver` | 1.4.7-3+b1 | `kiwisolver` | amd64 |
| `python3-lxml` | 5.4.0-1 | `lxml` | amd64 |
| `python3-lz4` | 4.4.0+dfsg-2 | `python-lz4` | amd64 |
| `python3-matplotlib` | 3.10.1+dfsg1-4 | `matplotlib` | amd64 |
| `python3-minimal` | 3.13.5-1 | `python3-defaults` | amd64 |
| `python3-mpmath` | 1.3.0-1 | `mpmath` | all |
| `python3-numpy` | 1:2.2.4+ds-1 | `numpy` | amd64 |
| `python3-numpy-dev` | 1:2.2.4+ds-1 | `numpy` | amd64 |
| `python3-openpyxl` | 3.1.5+dfsg-2 | `openpyxl` | all |
| `python3-packaging` | 25.0-1 | `python-packaging` | all |
| `python3-pandas` | 2.2.3+dfsg-9 | `pandas` | all |
| `python3-pandas-lib` | 2.2.3+dfsg-9 | `pandas` | amd64 |
| `python3-pil` | 11.1.0-5+deb13u4 | `pillow` | amd64 |
| `python3-pil.imagetk` | 11.1.0-5+deb13u4 | `pillow` | amd64 |
| `python3-platformdirs` | 4.3.7-1 | `platformdirs` | all |
| `python3-psycopg2` | 2.9.10-1+b1 | `psycopg2` | amd64 |
| `python3-pyparsing` | 3.1.2-1 | `pyparsing` | all |
| `python3-pytz` | 2025.2-3 | `python-tz` | all |
| `python3-scipy` | 1.15.3-1 | `scipy` | amd64 |
| `python3-sympy` | 1.13.3-5 | `sympy` | all |
| `python3-tk` | 3.13.5-1 | `python3-stdlib-extensions` | amd64 |
| `python3-ufolib2` | 0.17.1+dfsg1-1 | `ufolib2` | all |
| `python3-unicodedata2` | 15.1.0+ds-1+b4 | `python-unicodedata2` | amd64 |
| `python3-zopfli` | 0.2.3.post1-1+b1 | `python-zopfli` | amd64 |
| `python3.13` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `python3.13-minimal` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `python3.13-tk` | 3.13.5-2+deb13u4 | `python3.13` | amd64 |
| `r-base-core` | 4.5.0-3 | `r-base` | amd64 |
| `r-cran-askpass` | 1.2.1-1 | `r-cran-askpass` | amd64 |
| `r-cran-backports` | 1.5.0-2 | `r-cran-backports` | amd64 |
| `r-cran-base64enc` | 0.1-3-3 | `r-cran-base64enc` | amd64 |
| `r-cran-bit` | 4.6.0+dfsg-1 | `r-cran-bit` | amd64 |
| `r-cran-bit64` | 4.6.0-1-4 | `r-cran-bit64` | amd64 |
| `r-cran-blob` | 1.2.4-1 | `r-cran-blob` | all |
| `r-cran-broom` | 1.0.7+dfsg-1 | `r-cran-broom` | all |
| `r-cran-bslib` | 0.9.0+dfsg-3 | `r-cran-bslib` | all |
| `r-cran-cachem` | 1.1.0-1 | `r-cran-cachem` | amd64 |
| `r-cran-callr` | 3.7.6-1 | `r-cran-callr` | all |
| `r-cran-cellranger` | 1.1.0-3 | `r-cran-cellranger` | all |
| `r-cran-cli` | 3.6.4-1 | `r-cran-cli` | amd64 |
| `r-cran-clipr` | 0.8.0-1 | `r-cran-clipr` | all |
| `r-cran-colorspace` | 2.1-1+dfsg-1 | `r-cran-colorspace` | amd64 |
| `r-cran-commonmark` | 1.9.5-1 | `r-cran-commonmark` | amd64 |
| `r-cran-conflicted` | 1.2.0-1.1 | `r-cran-conflicted` | all |
| `r-cran-cpp11` | 0.5.2-1 | `r-cran-cpp11` | all |
| `r-cran-crayon` | 1.5.3-1 | `r-cran-crayon` | all |
| `r-cran-curl` | 6.2.1+dfsg-1 | `r-cran-curl` | amd64 |
| `r-cran-data.table` | 1.17.0+dfsg-1 | `r-cran-data.table` | amd64 |
| `r-cran-dbi` | 1.2.3-1 | `dbi` | all |
| `r-cran-dbplyr` | 2.5.0+dfsg-1 | `r-cran-dbplyr` | all |
| `r-cran-digest` | 0.6.37-1 | `r-cran-digest` | amd64 |
| `r-cran-dplyr` | 1.1.4-4 | `r-cran-dplyr` | amd64 |
| `r-cran-dtplyr` | 1.3.1-1 | `r-cran-dtplyr` | all |
| `r-cran-ellipsis` | 0.3.2-2 | `r-cran-ellipsis` | amd64 |
| `r-cran-evaluate` | 1.0.3-1 | `r-cran-evaluate` | all |
| `r-cran-fansi` | 1.0.6-2 | `r-cran-fansi` | amd64 |
| `r-cran-farver` | 2.1.2-1 | `r-cran-farver` | amd64 |
| `r-cran-fastmap` | 1.2.0-1 | `r-cran-fastmap` | amd64 |
| `r-cran-fontawesome` | 0.5.3-1 | `r-cran-fontawesome` | all |
| `r-cran-forcats` | 1.0.0-1 | `r-cran-forcats` | all |
| `r-cran-fs` | 1.6.5+dfsg-1 | `r-cran-fs` | amd64 |
| `r-cran-gargle` | 1.5.2-1 | `r-cran-gargle` | all |
| `r-cran-generics` | 0.1.3-1 | `r-cran-generics` | all |
| `r-cran-ggplot2` | 3.5.1+dfsg-1 | `r-cran-ggplot2` | all |
| `r-cran-glue` | 1.8.0-1 | `r-cran-glue` | amd64 |
| `r-cran-googledrive` | 2.1.1-3 | `r-cran-googledrive` | all |
| `r-cran-googlesheets4` | 1.1.1-1 | `r-cran-googlesheets4` | all |
| `r-cran-gtable` | 0.3.6+dfsg-1 | `r-cran-gtable` | all |
| `r-cran-haven` | 2.5.4-1 | `r-cran-haven` | amd64 |
| `r-cran-highr` | 0.11+dfsg-1 | `r-cran-highr` | all |
| `r-cran-hms` | 1.1.3-1 | `r-cran-hms` | all |
| `r-cran-htmltools` | 0.5.8.1-1 | `r-cran-htmltools` | amd64 |
| `r-cran-httpuv` | 1.6.15+dfsg-1 | `r-cran-httpuv` | amd64 |
| `r-cran-httr` | 1.4.7+dfsg-1 | `r-cran-httr` | all |
| `r-cran-ids` | 1.0.1-2 | `r-cran-ids` | all |
| `r-cran-isoband` | 0.2.7-1 | `r-cran-isoband` | amd64 |
| `r-cran-jquerylib` | 0.1.4+dfsg-4 | `r-cran-jquerylib` | all |
| `r-cran-jsonlite` | 1.9.1+dfsg-1 | `r-cran-jsonlite` | amd64 |
| `r-cran-knitr` | 1.50+dfsg-1 | `r-cran-knitr` | all |
| `r-cran-labeling` | 0.4.3-1 | `r-cran-labeling` | all |
| `r-cran-later` | 1.4.1+dfsg-1 | `r-cran-later` | amd64 |
| `r-cran-lattice` | 0.22-7-1 | `lattice` | amd64 |
| `r-cran-lifecycle` | 1.0.4+dfsg-1 | `r-cran-lifecycle` | all |
| `r-cran-littler` | 0.3.21-1 | `littler` | amd64 |
| `r-cran-lubridate` | 1.9.4+dfsg-1 | `r-cran-lubridate` | amd64 |
| `r-cran-magrittr` | 2.0.3-1 | `r-cran-magrittr` | amd64 |
| `r-cran-mass` | 7.3-65-1 | `r-cran-mass` | amd64 |
| `r-cran-matrix` | 1.7-3-1 | `rmatrix` | amd64 |
| `r-cran-memoise` | 2.0.1-1 | `r-cran-memoise` | all |
| `r-cran-mgcv` | 1.9-3-1 | `mgcv` | amd64 |
| `r-cran-mime` | 0.12-2 | `r-cran-mime` | amd64 |
| `r-cran-modelr` | 0.1.11-1 | `r-cran-modelr` | all |
| `r-cran-munsell` | 0.5.1-1 | `r-cran-munsell` | all |
| `r-cran-nlme` | 3.1.168-1 | `nlme` | amd64 |
| `r-cran-openssl` | 2.3.2+dfsg-1 | `r-cran-openssl` | amd64 |
| `r-cran-pillar` | 1.10.1+dfsg-1 | `r-cran-pillar` | all |
| `r-cran-pkgconfig` | 2.0.3-2 | `r-cran-pkgconfig` | all |
| `r-cran-pkgkitten` | 0.2.4-1 | `r-cran-pkgkitten` | all |
| `r-cran-prettyunits` | 1.2.0-1 | `r-cran-prettyunits` | all |
| `r-cran-processx` | 3.8.6-1 | `r-cran-processx` | amd64 |
| `r-cran-progress` | 1.2.3-1 | `r-cran-progress` | all |
| `r-cran-promises` | 1.3.2+dfsg-1 | `r-cran-promises` | amd64 |
| `r-cran-ps` | 1.9.0-1 | `r-cran-ps` | amd64 |
| `r-cran-purrr` | 1.0.4-1 | `r-cran-purrr` | amd64 |
| `r-cran-r6` | 2.6.1-1 | `r-cran-r6` | all |
| `r-cran-ragg` | 1.3.3-1 | `r-cran-ragg` | amd64 |
| `r-cran-rappdirs` | 0.3.3-1 | `r-cran-rappdirs` | amd64 |
| `r-cran-rcolorbrewer` | 1.1-3-1 | `rcolorbrewer` | all |
| `r-cran-rcpp` | 1.0.14-1 | `rcpp` | amd64 |
| `r-cran-readr` | 2.1.5-1 | `r-cran-readr` | amd64 |
| `r-cran-readxl` | 1.4.5-1 | `r-cran-readxl` | amd64 |
| `r-cran-rematch` | 2.0.0-1 | `r-cran-rematch` | all |
| `r-cran-rematch2` | 2.1.2-2 | `r-cran-rematch2` | all |
| `r-cran-reprex` | 2.1.1-1 | `r-cran-reprex` | all |
| `r-cran-rlang` | 1.1.5-3 | `r-cran-rlang` | amd64 |
| `r-cran-rmarkdown` | 2.29+dfsg-1 | `r-cran-rmarkdown` | all |
| `r-cran-rpostgresql` | 0.7-7+dfsg-1 | `r-cran-rpostgresql` | amd64 |
| `r-cran-rstudioapi` | 0.17.1-1 | `r-cran-rstudioapi` | all |
| `r-cran-rvest` | 1.0.4-1 | `r-cran-rvest` | all |
| `r-cran-sass` | 0.4.9+dfsg-1 | `r-cran-sass` | amd64 |
| `r-cran-scales` | 1.3.0-1 | `r-cran-scales` | all |
| `r-cran-selectr` | 0.4-2-2 | `r-cran-selectr` | all |
| `r-cran-shiny` | 1.10.0+dfsg-2 | `r-cran-shiny` | all |
| `r-cran-sourcetools` | 0.1.7-1-1 | `r-cran-sourcetools` | amd64 |
| `r-cran-stringi` | 1.8.4-1+b1 | `r-cran-stringi` | amd64 |
| `r-cran-stringr` | 1.5.1-1 | `r-cran-stringr` | all |
| `r-cran-sys` | 3.4.3-1 | `r-cran-sys` | amd64 |
| `r-cran-systemfonts` | 1.2.1-1 | `r-cran-systemfonts` | amd64 |
| `r-cran-textshaping` | 0.3.7-2 | `r-cran-textshaping` | amd64 |
| `r-cran-tibble` | 3.2.1+dfsg-3 | `r-cran-tibble` | amd64 |
| `r-cran-tidyr` | 1.3.1-1 | `r-cran-tidyr` | amd64 |
| `r-cran-tidyselect` | 1.2.1+dfsg-1 | `r-cran-tidyselect` | amd64 |
| `r-cran-tidyverse` | 2.0.0+dfsg-2 | `r-cran-tidyverse` | all |
| `r-cran-timechange` | 0.3.0-2 | `r-cran-timechange` | amd64 |
| `r-cran-tinytex` | 0.56-1 | `r-cran-tinytex` | all |
| `r-cran-tzdb` | 0.5.0-1 | `r-cran-tzdb` | amd64 |
| `r-cran-utf8` | 1.2.4-1 | `r-cran-utf8` | amd64 |
| `r-cran-uuid` | 1.2-1-1 | `r-cran-uuid` | amd64 |
| `r-cran-vctrs` | 0.6.5-1 | `r-cran-vctrs` | amd64 |
| `r-cran-viridislite` | 0.4.2-2 | `r-cran-viridislite` | all |
| `r-cran-vroom` | 1.6.5-1 | `r-cran-vroom` | amd64 |
| `r-cran-withr` | 3.0.2+dfsg-1 | `r-cran-withr` | all |
| `r-cran-xfun` | 0.51+dfsg-1 | `r-cran-xfun` | amd64 |
| `r-cran-xml2` | 1.3.8-1 | `r-cran-xml2` | amd64 |
| `r-cran-xtable` | 1:1.8-4-2 | `r-cran-xtable` | all |
| `r-cran-yaml` | 2.3.10-1 | `r-cran-yaml` | amd64 |
| `readline-common` | 8.2-6 | `readline` | all |
| `sed` | 4.9-2+deb13u1 | `sed` | amd64 |
| `sensible-utils` | 0.0.25 | `sensible-utils` | all |
| `sqv` | 1.3.0-3+b2 | `rust-sequoia-sqv` | amd64 |
| `sysvinit-utils` | 3.14-4 | `sysvinit` | amd64 |
| `tar` | 1.35+dfsg-3.1 | `tar` | amd64 |
| `tk8.6-blt2.5` | 2.5.3+dfsg-8 | `blt` | amd64 |
| `tzdata` | 2026b-0+deb13u1 | `tzdata` | all |
| `ucf` | 3.0052 | `ucf` | all |
| `unicode-data` | 15.1.0-1 | `unicode-data` | all |
| `unzip` | 6.0-29+deb13u1 | `unzip` | amd64 |
| `util-linux` | 2.41-5 | `util-linux` | amd64 |
| `x11-common` | 1:7.7+24+deb13u1 | `xorg` | all |
| `xdg-utils` | 1.2.1-2 | `xdg-utils` | all |
| `zip` | 3.0-15+deb13u1 | `zip` | amd64 |
| `zlib1g` | 1:1.3.dfsg+really1.3.1-1+b1 | `zlib` | amd64 |

## 11. Limites

- **Une seule VM cible auditée** : les annexes A et B reflètent l'état réellement installé sur `192.168.122.114` au 19 août 2026. Une autre installation de SILLON (autre date, autre séquence de correctifs Debian appliqués) peut légitimement différer sur quelques paquets — voir le constat §7.7, déjà observé entre deux résolutions successives de cette même nomenclature.
- **`sillon-demo-sirene` non installé sur la VM auditée** : ce paquet optionnel n'était pas présent sur `192.168.122.114` au moment de cette résolution ; ses dépendances Debian (`python3` seul, déjà couvert par l'univers hôte) restent inchangées depuis la première version de cette nomenclature.
- **Aucun scan de vulnérabilités connues (CVE) réalisé sur les paquets Debian** : seuls les 10 composants vendorisés hors `dpkg` ont fait l'objet d'une vérification individuelle (§6.1) ; les 573 paquets Debian listés en annexe n'ont pas été confrontés un à un au Debian Security Tracker — voir §8 pour la mécanique de veille recommandée sur ce périmètre.
- **Couverture OSV.dev non exhaustive** : la vérification des composants vendorisés (§6.1) s'appuie sur OSV.dev, le registre npm et les changelogs/notes de version amont — une base fiable et largement utilisée, mais qui ne garantit pas l'absence de vulnérabilité non encore publiée ou non répertoriée (0-day, faille signalée mais non encore publiée sous forme d'avis).
- **Revue de licence non exhaustive** : les licences des paquets Debian (annexes A et B) ne sont pas reproduites ici (elles sont chacune consultables via `apt-cache show` ou `/usr/share/doc/<paquet>/copyright` sur une machine Debian) ; seules celles des 10 composants vendorisés hors `dpkg` (§6) ont été relevées individuellement.
- Cette nomenclature couvre les 6 paquets `.deb` de SILLON. Elle ne couvre pas les outils de build eux-mêmes (`build/build.sh`, scripts `generer_pdf_*.py`, `pandoc`, `libreoffice`), qui ne sont jamais installés sur la cible de production.
- **Correctif construit, déployé et vérifié en conditions réelles** : `sillon-server` 0.1.29 (PapaParse 5.6.0, DSFR 1.15.2) a été reconstruit le 19 août 2026, installé sur la VM de test (`apt install`, mise à niveau propre depuis 0.1.28, migrations incrémentales appliquées sans recréation du catalogue) et vérifié de bout en bout sur l'application réelle servie en HTTPS par cette VM : connexion avec le compte de démonstration, chargement de toutes les ressources front (CSS, polices, icônes, PapaParse) sans erreur console ni requête en échec, et **import CSV réel** (onglet Import, fichier `graphique.csv`) analysé avec succès par PapaParse 5.6.0 jusqu'à la détection des colonnes. Aucune régression visuelle ou fonctionnelle constatée après la mise à jour de DSFR et PapaParse.
- **Image de base épinglée, déployée et vérifiée par exécution réelle** : `sillon-image-execution` (base `debian:13-slim` épinglée par digest) a été reconstruit le 19 août 2026. Une première reconstruction (0.1.1) chargeait sans erreur sur la VM mais ne produisait plus aucun conteneur exécutable (constat §7.1 bis) — détecté en testant un script réel avant toute clôture du constat, pas seulement par relecture du build. Corrigée en 0.1.2, installée sur la VM de test (mise à niveau réelle, `podman load` confirmé dans la sortie de `postinst`) et vérifiée par un job `script_python` réel mené à terme (import `pandas`/`numpy`, sortie standard conforme).

## 12. Suite possible

- Rejouer cette résolution à chaque nouvelle version des paquets `.deb`, ou périodiquement, pour tenir la nomenclature à jour des correctifs de sécurité Debian réellement appliqués sur la cible (constat §7.7) et des composants vendorisés (§6.1, §8).
- Mettre en place un rapprochement périodique (par exemple à chaque publication d'un nouveau `.deb`) entre `sbom/sillon-sbom-cyclonedx.json` et le Debian Security Tracker ou un scanner de vulnérabilités.
- Ajouter un fichier `LICENSE` à la racine du dépôt si le code SILLON doit circuler en dehors de l'organisation (constat §7.4).
