<!-- title: SILLON — Audit d'accessibilité RGAA -->

# Audit d'accessibilité RGAA — SILLON

| Champ | Valeur |
|---|---|
| Date | 15 août 2026 |
| Périmètre | Application SILLON (front-end), tous profils (lecteur non testé — pas d'onglet propre), agent, administrateur |
| Méthode | Tests automatisés (axe-core 4.13.0, règles WCAG 2.0/2.1 A et AA + bonnes pratiques) sur chaque écran de l'application déployée, complétés par une relecture manuelle ciblée sur les points qu'un outil automatisé ne peut pas évaluer |
| Statut | Audit ciblé et corrections associées — **pas une déclaration d'accessibilité au sens de l'article 47** (voir « Limites » ci-dessous) |

## 1. Contexte

Ce document consigne un audit d'accessibilité mené sur l'application SILLON, en vue d'une future mise en conformité RGAA. Il ne remplace pas un audit RGAA complet (106 critères, méthodologie officielle, échantillon de pages représentatif défini contradictoirement) ni la déclaration d'accessibilité, le schéma pluriannuel et le plan d'action annuel exigés par l'article 47 de la loi du 11 février 2005 pour un service public numérique — ces documents n'ont pas été demandés à ce stade et devront faire l'objet d'un travail dédié le moment venu.

Son objectif est plus restreint : détecter et corriger les défauts d'accessibilité réels de l'application, avec des outils reproductibles, avant tout travail de certification proprement dit.

## 2. Méthodologie

**Tests automatisés** — axe-core (moteur utilisé par la majorité des outils d'audit du marché, dont certains outils officiels de contrôle RGAA) exécuté directement dans le navigateur, sur l'application déployée sur la VM de test, pour chacun des écrans suivants :
- Écran de connexion
- Les 9 onglets de l'application (Bases, Travaux, Import, Scripts, Suivi, Carto, Graphiques, Diagrammes, Administration), sous les profils agent et administrateur
- Les 3 modales (« À propos », éditeur de script, import depuis data.gouv.fr)
- Le rendu réel d'un graphique (Graphiques) et d'un diagramme Mermaid (Diagrammes), pas seulement les écrans vides

**Relecture manuelle ciblée** — navigation clavier (ordre de tabulation, visibilité du focus, piège au clavier), présence d'un lien d'évitement, langue de la page, titre de la page, hiérarchie des titres, attribut `lang`.

**Hors périmètre de cet audit** (voir « Limites ») : vérification exhaustive des 106 critères RGAA, test avec un lecteur d'écran réel (NVDA/JAWS/VoiceOver), zoom/réflow à 200 %, contraste de couleurs au-delà de ce que couvre axe-core, compatibilité avec d'autres technologies d'assistance.

## 3. Constats et corrections

| # | Constat | Sévérité (axe) | Écran(s) concerné(s) | Correction apportée |
|---|---|---|---|---|
| 1 | Aucun landmark `<main>` visible une fois connecté (le seul `<main>` de la page n'entourait que l'écran de connexion, masqué après authentification) | Modéré | Toute l'application authentifiée | `#application` converti en `<main>` |
| 2 | Aucun titre de niveau 1 (`<h1>`) sur les écrans applicatifs (seules les modales en avaient un) | Modéré | Tous les onglets | `<h1 id="titre-onglet">` masqué visuellement (`fr-sr-only`), mis à jour dynamiquement avec le libellé de l'onglet actif |
| 3 | Aucun lien d'évitement (« Aller au contenu ») | — (relevé manuellement, critère RGAA 12.7) | Toute l'application | Ajout du bloc `.fr-skiplinks` standard du Système de Design de l'État |
| 4 | En-tête de colonne de tableau vide (`<th></th>`) dans « Mes bases » | Mineur | Onglet Bases | Colonne « Propriétaire » (non pertinente pour ses propres bases) omise plutôt que vidée |
| 5 | Champ de saisie interne de l'éditeur SQL (CodeMirror) sans nom accessible | **Critique** | Onglet Travaux | `aria-label="Requête SQL"` posé sur le champ interne de CodeMirror |
| 6 | Menus déroulants de la cascade géographique (région/département/EPCI/commune, monde) sans nom accessible | **Critique** | Onglet Carto | `aria-label` posé sur chaque `<select>` généré dynamiquement |
| 7 | Champs de la section Quotas (panneau Administration) avec un `<label>` non lié à son champ (`for` manquant) | **Critique** | Administration | Attribut `for` ajouté, generé dynamiquement pour chaque paramètre |
| 8 | Diagramme Mermaid (aperçu de l'onglet Diagrammes) rendu en SVG sans alternative textuelle | — (relevé manuellement, critère RGAA image) | Onglet Diagrammes | Aperçu marqué `aria-hidden="true"` (le code Mermaid, strictement équivalent, est déjà affiché en texte juste à côté) ; l'aperçu de diagramme dans l'onglet Suivi (où le code source n'est pas visible à côté) reçoit à la place un `aria-label` explicite nommant le fichier |
| 9 | Hiérarchie des titres non conforme : saut direct de H1 à H6 (modale « À propos ») puis, une fois le H1 global ajouté (constat 2), saut de H1 à H3 (onglet Travaux, « Requêtes enregistrées » / « Historique ») | Modéré | Modale « À propos », onglet Travaux | Titres reclassés au niveau H2 (classe visuelle `fr-h6` conservée, seul le niveau sémantique change) |

Tous les correctifs ont été déployés sur la VM de test et revérifiés par un nouveau passage axe-core : **0 violation détectée, sur les 9 onglets (profils agent et administrateur), les 3 modales et les rendus dynamiques (graphique, diagramme) testés.**

## 4. Points déjà conformes, vérifiés au passage

- Modales : piège au clavier correct (`showModal()`), focus restitué au déclencheur à la fermeture, bouton de fermeture toujours présent et atteignable.
- Graphiques (Chart.js) : un tableau de données équivalent, masqué visuellement (`fr-sr-only`) mais accessible aux technologies d'assistance, est bien généré à chaque rendu.
- Attribut `lang="fr"` présent, titre de page pertinent.
- Focus clavier visible par défaut (aucune règle CSS ne désactive `outline` sur les éléments interactifs).
- Aucune violation de contraste de couleur détectée par axe-core sur les palettes DSFR utilisées, y compris les palettes personnalisées de Carto/Graphiques/Diagrammes (cf. limites ci-dessous sur la portée réelle de cette vérification).

## 5. Limites de cet audit

- **Pas un audit RGAA complet** : la méthodologie officielle RGAA impose la vérification systématique des 106 critères sur un échantillon de pages représentatif défini contradictoirement avec le commanditaire, avec des tests spécifiques que les outils automatisés ne couvrent pas tous (ordre de lecture, pertinence des alternatives, cohérence de la navigation au clavier sur des interactions complexes, etc.). Cet audit s'appuie sur axe-core (qui ne détecte, selon les études indépendantes publiées, qu'environ 30 à 50 % des critères WCAG de façon fiable) et une relecture manuelle volontairement ciblée sur les points les plus fréquemment défaillants, pas une revue exhaustive.
- **Pas de test avec un lecteur d'écran réel** (NVDA, JAWS, VoiceOver) : les corrections apportées (noms accessibles, landmarks, titres) suivent les règles WCAG/RGAA mais n'ont pas été vérifiées à l'écoute.
- **Zoom et réflow à 200 %** non testés.
- **Contraste de couleurs** : seules les combinaisons que axe-core sait évaluer automatiquement (texte sur fond uni, essentiellement) ont été vérifiées ; les couleurs de données (palettes Carto/Graphiques appliquées à des séries de données, pas à du texte) sortent du champ de cette vérification par nature.
- **Documents PDF** (guides, cahier des charges) non audités : seule l'application web a été testée.
- Cet audit ne constitue donc **ni une certification, ni le fondement suffisant à lui seul d'une déclaration de conformité RGAA** — il réduit un risque réel et documenté, sans épuiser le sujet.

## 6. Suite possible

Si une véritable démarche de mise en conformité RGAA est engagée par la suite, ce document peut servir de point de départ : les corrections déjà faites n'auront pas à être refaites, et la structure (landmark, titre, lien d'évitement) déjà en place facilite le travail d'un audit complet. Les trois documents légaux (déclaration d'accessibilité, schéma pluriannuel, plan d'action annuel) restent à rédiger séparément, sur la base des résultats d'un audit RGAA complet à mener le moment venu.
