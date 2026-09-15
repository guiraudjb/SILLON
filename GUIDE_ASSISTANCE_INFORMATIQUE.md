# SILLON — Guide d'assistance informatique

### Gestes courants de support : mot de passe, comptes bloqués, adresses IP bannies

---

## À propos de ce guide

Ce guide s'adresse à l'assistance informatique de la direction (support niveau 1/2), pas aux administrateurs applicatifs de SILLON au sens du panneau Administration. Il rassemble les gestes de dépannage les plus fréquemment demandés par les utilisateurs — réinitialiser un mot de passe oublié, débloquer un compte, débannir une adresse IP après trop d'échecs de connexion — sous forme de procédures pas-à-pas, sans prérequis de connaissance de l'architecture interne de SILLON.

Il complète, sans les remplacer :

- Le **guide d'installation administrateur** (`GUIDE_INSTALLATION_ADMINISTRATEUR.md`), pour la mise en place du serveur et le dépannage technique d'infrastructure (réseau, PostgreSQL, paquets).
- Le **guide utilisateur** (`GUIDE_UTILISATEUR_SILLON.md`), pour le fonctionnement de l'application du point de vue d'un data analyste.
- Le **cahier des charges** (`SILLON_cahier_des_charges.md`), pour le comportement attendu et la justification de chaque règle de sécurité.

**Deux niveaux d'action distingués dans ce guide** :

- **Depuis l'interface web**, avec un compte administrateur SILLON (aucun accès au serveur requis) — la majorité des cas.
- **Depuis le serveur**, en ligne de commande (accès SSH/console requis) — réservé aux cas non couverts par l'interface, à escalader si le support n'a pas cet accès.

---

## 1. Réinitialiser le mot de passe d'un utilisateur

**Contexte** : il n'existe **aucune réinitialisation en libre-service** dans SILLON (choix de conception délibéré, cahier des charges §8.1, pour éliminer la surface d'attaque d'un mécanisme de récupération par email). Un utilisateur qui a oublié son mot de passe doit systématiquement passer par un administrateur.

**Procédure (interface web, compte administrateur requis)** :

1. Se connecter à SILLON avec un compte de profil **administrateur**.
2. Ouvrir l'onglet **Administration** (visible uniquement pour ce profil).
3. Dans le tableau des comptes utilisateurs, repérer la ligne de l'utilisateur concerné (recherche par email).
4. Cliquer sur le bouton **« Réinitialiser mdp »** de sa ligne.
5. Dans la fenêtre qui s'ouvre, saisir un nouveau mot de passe provisoire (**12 caractères minimum**, refusé en dessous par l'interface) et valider.
6. Communiquer ce mot de passe provisoire à l'utilisateur **hors bande** (jamais par le même canal qu'une demande de support non authentifiée) — un changement de mot de passe n'est pas techniquement forcé à la reconnexion pour un compte déjà actif, à la différence d'un compte tout juste créé.

**Point de vigilance** : l'interface ne demande aucune confirmation supplémentaire avant d'écraser l'ancien mot de passe — vérifier l'identité de l'utilisateur (email exact) avant de cliquer.

---

## 2. Désactiver ou réactiver un compte en urgence

**Contexte** : c'est le mécanisme de révocation d'urgence de SILLON (cahier des charges §8.13). Contrairement à un jeton de session classique, un compte désactivé perd **immédiatement** toute capacité d'action — le statut actif/inactif est revérifié côté serveur à **chaque requête**, indépendamment de la validité de sa session en cours (§8.2). Pas besoin d'attendre l'expiration de sa session (8h) ni de « tuer » une session séparément : désactiver suffit.

**Procédure (interface web, compte administrateur requis)** :

1. Onglet **Administration** → tableau des comptes utilisateurs.
2. Repérer la ligne de l'utilisateur.
3. Cliquer sur **« Désactiver »** (le même bouton devient **« Réactiver »** une fois le compte désactivé, pour l'opération inverse).

**Quand l'utiliser** : départ d'un agent, compte compromis suspecté, incident de sécurité en cours — c'est l'action la plus rapide et la plus sûre disponible depuis l'interface, à privilégier avant toute autre mesure.

**Point de vigilance** : aucune fenêtre de confirmation n'apparaît avant la désactivation — action immédiate dès le clic.

---

## 3. Débannir une adresse IP (Fail2Ban)

**Contexte** : SILLON bannit automatiquement une adresse IP après plusieurs échecs de connexion rapprochés (Fail2Ban, cahier des charges §8.6). Ce n'est **pas visible ni gérable depuis l'interface web** — uniquement en ligne de commande sur le serveur.

**Paramètres actuels du bannissement** (jail `sillon-login`, configuré par le paquet `sillon-server`) :

| Paramètre | Valeur |
|---|---|
| Seuil de déclenchement | 5 échecs |
| Fenêtre d'observation | 10 minutes |
| Durée du bannissement | 1 heure |

Un utilisateur qui enchaîne les erreurs de frappe sur son mot de passe (ou qui retente en boucle après un mot de passe expiré/oublié) peut donc se retrouver banni lui-même, sans aucune intention malveillante — c'est le cas le plus fréquent remonté au support.

**Procédure (ligne de commande, accès serveur requis)** :

```bash
# Vérifier si une adresse est actuellement bannie, et lister tous les bannissements en cours
sudo fail2ban-client status sillon-login

# Débannir une adresse précise
sudo fail2ban-client set sillon-login unbanip <adresse_ip>
```

**Point de vigilance** : le bannissement expire de lui-même au bout d'une heure — si l'urgence n'est pas absolue, il est souvent plus simple de prévenir l'utilisateur d'attendre plutôt que de mobiliser un accès serveur. Ne débannir qu'après avoir confirmé qu'il s'agit bien d'un échec légitime (vérifier le journal d'audit, §4, avant de lever un bannissement en cas de doute sur une tentative malveillante).

---

## 4. Consulter le journal d'audit (pour qualifier un incident)

**Contexte** : avant de débannir une IP ou de réactiver un compte, il est utile de vérifier ce qui s'est réellement passé. Le journal d'audit de SILLON est immuable (aucune entrée ne peut être modifiée ou supprimée, même par un administrateur — cahier des charges §8.12) et trace toute création/suppression de base ou de table, tout partage accordé ou révoqué, et toute action d'administration (création de compte, changement de profil, réinitialisation de mot de passe, désactivation).

**Procédure (interface web, compte administrateur requis)** :

1. Onglet **Administration** → section **Journal d'audit**.
2. Filtrer par utilisateur, par type d'action et/ou par période selon le besoin.

**Ce que le journal d'audit ne couvre pas** : les tentatives de connexion échouées (succès/échec de login) ne sont pas dans ce journal applicatif — elles sont dans les journaux Nginx/Fail2Ban du serveur (`/var/log/nginx/access.log`), consultables uniquement en ligne de commande :

```bash
sudo journalctl -u fail2ban -n 100
sudo grep "rpc/login" /var/log/nginx/access.log | tail -50
```

---

## 5. Compte compromis suspecté — mesure de dernier recours

**Contexte** : au-delà de la désactivation d'un compte précis (§2), SILLON prévoit la possibilité de régénérer le secret de signature des jetons de connexion, ce qui invalide **toutes** les sessions actives de **tous** les utilisateurs d'un coup (cahier des charges §8.11) — à réserver à une compromission avérée ou fortement suspectée touchant potentiellement plusieurs comptes (ex. fuite du secret lui-même), pas à un incident isolé sur un seul compte, pour lequel la désactivation ciblée (§2) suffit et est bien moins disruptive.

**Cette action n'est pas disponible depuis l'interface web** (aucun bouton dédié à ce jour) — elle nécessite un accès serveur et une intervention manuelle. **Le support niveau 1 ne doit pas exécuter cette procédure seul** : elle déconnecte immédiatement tous les utilisateurs de la plateforme sans exception. Elle est documentée ici pour que le support sache qu'elle existe et sache l'escalader correctement (administrateur technique / niveau 2), plutôt que pour l'exécuter directement.

**Principe (à dérouler par un administrateur technique)** : générer un nouveau secret aléatoire, le mettre à jour à la fois dans la base (`auth.secrets`, clé `jwt_secret`) et dans la configuration de PostgREST (`/etc/sillon/secrets.env` et `/etc/sillon-api.conf`), puis redémarrer les services `sillon-api` et `sillon-orchestrateur`. Voir `GUIDE_INSTALLATION_ADMINISTRATEUR.md` pour l'emplacement exact de ces fichiers.

---

## 6. Autres cas fréquents

**Job bloqué en file d'attente ou trop long** : ce n'est pas une action support — l'utilisateur peut annuler lui-même son propre job (import, requête, script) depuis l'onglet **Suivi**, tant qu'il est en attente ou en cours (cahier des charges §5.5). Rediriger l'utilisateur vers cet onglet plutôt qu'intervenir à sa place.

**Quota disque ou durée de job dépassé** : un dépassement place le job en erreur avec un message explicite, sans dégradation silencieuse (§11). Les quotas globaux (taille max de CSV, durée max de job, CPU/RAM par script, jobs simultanés, quota disque par base) se règlent depuis **Administration → Quotas**. **Point de vigilance** : à ce jour, seuls des quotas **globaux** sont réglables depuis l'interface — il n'existe pas encore de dérogation par utilisateur individuel dans l'application, malgré une mention en ce sens au cahier des charges (§3, §5.6) ; à vérifier auprès de l'équipe de développement si un cas concret le nécessite.

**Vérifier que les services SILLON tournent bien** (avant d'escalader un incident qui semble plus large qu'un compte isolé) :

```bash
sudo systemctl status sillon-api sillon-orchestrateur sillon-worker nginx postgresql fail2ban
```

---

## Pour aller plus loin

- Le **guide d'installation administrateur** couvre le dépannage d'infrastructure (réseau, PostgreSQL, paquets) et les procédures de sauvegarde/restauration.
- Le **cahier des charges** détaille la justification de chaque règle de sécurité citée dans ce guide.
- Ce guide reflète l'état de l'application au moment de sa rédaction ; en cas d'écart constaté avec l'interface réelle (bouton renommé, comportement différent), le signaler pour mise à jour plutôt que de supposer une erreur de manipulation.
