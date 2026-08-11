// SILLON - Front-end applicatif
// Vanilla JS, sans framework ni étape de build (cahier des charges §4.2).
// Organisation en objets par domaine fonctionnel (Auth, Bases, Travaux,
// Import, Scripts, Suivi, Administration), plutôt qu'en composants
// séparés : cohérent avec l'absence de bundler du projet.

const TYPES_COLONNE = ["Texte", "Entier", "Décimal", "Date", "Date/Heure", "Booléen", "JSON"];

const Etat = {
    utilisateur: null,
    bases: [],
    baseSelectionnee: null,
    dernierApercu: null,
    derniereVerification: null,
    dernieresLignesExclues: [],
};

// =============================================================================
// ACCES API
// =============================================================================
async function appel(url, options = {}) {
    const reponse = await fetch(url, { credentials: "include", ...options });
    if (reponse.status === 401) {
        Auth.afficherEcranConnexion("Session expirée, merci de vous reconnecter.");
        throw new Error("Non authentifié");
    }
    return reponse;
}

async function appelJson(url, options = {}) {
    // Un corps FormData (dépôt de fichier) ne doit JAMAIS recevoir de
    // Content-Type manuel : le navigateur doit calculer lui-même la
    // frontière "multipart/form-data; boundary=...", sans quoi le corps
    // n'est plus reconnu côté serveur (constaté en pratique : Flask ne
    // trouve alors aucun fichier dans la requête).
    const enTetes = { ...(options.headers || {}) };
    if (!(options.body instanceof FormData)) {
        enTetes["Content-Type"] = "application/json";
    }
    const reponse = await appel(url, { ...options, headers: enTetes });
    const corps = await reponse.json().catch(() => null);
    if (!reponse.ok) {
        throw new Error((corps && (corps.erreur || corps.message)) || `Erreur HTTP ${reponse.status}`);
    }
    return corps;
}

function afficherErreur(conteneur, erreur) {
    conteneur.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message || String(erreur))}</div>`;
}

function echapper(texte) {
    const div = document.createElement("div");
    div.textContent = texte == null ? "" : String(texte);
    return div.innerHTML;
}

function formaterTaille(octets) {
    if (octets == null) return "—";
    const unites = ["o", "Ko", "Mo", "Go", "To"];
    let taille = octets, i = 0;
    while (taille >= 1024 && i < unites.length - 1) { taille /= 1024; i++; }
    return `${taille.toFixed(i === 0 ? 0 : 1)} ${unites[i]}`;
}

function tronquer(texte, longueurMax) {
    return texte.length > longueurMax ? `${texte.slice(0, longueurMax)}…` : texte;
}

// =============================================================================
// AUTHENTIFICATION (§4.3, §8.1, §8.2)
// =============================================================================
const Auth = {
    afficherEcranConnexion(messageErreur) {
        document.getElementById("ecran-connexion").hidden = false;
        document.getElementById("application").hidden = true;
        document.getElementById("zone-utilisateur").hidden = true;
        const alerte = document.getElementById("alerte-connexion");
        if (messageErreur) {
            alerte.textContent = messageErreur;
            alerte.hidden = false;
        } else {
            alerte.hidden = true;
        }
    },

    async tenterConnexion(evenement) {
        evenement.preventDefault();
        const email = document.getElementById("champ-email").value.trim();
        const mdp = document.getElementById("champ-mdp").value;
        try {
            const reponse = await fetch("/api/rpc/login", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password: mdp }),
            });
            if (!reponse.ok) {
                const corps = await reponse.json().catch(() => ({}));
                throw new Error(corps.message || "Identifiants incorrects");
            }
            await Auth.chargerSession();
        } catch (erreur) {
            Auth.afficherEcranConnexion(erreur.message);
        }
    },

    async deconnecter() {
        await appel("/api/rpc/logout", { method: "POST" }).catch(() => {});
        // Remet l'état à zéro : sans ça, la base sélectionnée (et la liste
        // des bases) d'une session précédente reste affichée après
        // reconnexion sous un autre compte, tant que la page n'est pas
        // rechargée (l'appli ne fait jamais de rechargement complet entre
        // deux connexions, §4.2 - SPA).
        Etat.utilisateur = null;
        Etat.bases = [];
        Etat.baseSelectionnee = null;
        Etat.dernierApercu = null;
        Etat.derniereVerification = null;
        Etat.dernieresLignesExclues = [];
        document.getElementById("rappel-base-selectionnee").querySelector("p").textContent =
            "Aucune base sélectionnée. Choisissez une base ci-dessous pour l'utiliser dans les onglets Travaux et Scripts.";
        document.getElementById("travaux-base-active").textContent = "";
        Auth.afficherEcranConnexion();
    },

    async chargerSession() {
        const reponse = await fetch("/api/rpc/me", {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
        });
        const corps = await reponse.json().catch(() => null);
        if (!reponse.ok || !corps) {
            Auth.afficherEcranConnexion();
            return false;
        }
        Etat.utilisateur = corps;
        Auth.afficherApplication();
        return true;
    },

    afficherApplication() {
        document.getElementById("ecran-connexion").hidden = true;
        document.getElementById("application").hidden = false;
        document.getElementById("zone-utilisateur").hidden = false;
        document.getElementById("libelle-utilisateur").textContent = `${Etat.utilisateur.email} (${Etat.utilisateur.profil})`;
        document.getElementById("onglet-nav-administration").hidden = Etat.utilisateur.profil !== "administrateur";

        Bases.charger();
        Suivi.rafraichir();
    },
};

// =============================================================================
// NAVIGATION ENTRE ONGLETS
// =============================================================================
function basculerOnglet(nomOnglet) {
    document.querySelectorAll(".fr-tabs__tab").forEach((bouton) => {
        const actif = bouton.dataset.onglet === nomOnglet;
        bouton.setAttribute("aria-selected", actif ? "true" : "false");
    });
    document.querySelectorAll(".fr-tabs__panel").forEach((panneau) => {
        const actif = panneau.id === `panneau-${nomOnglet}`;
        panneau.hidden = !actif;
        panneau.classList.toggle("fr-tabs__panel--selected", actif);
    });
    if (nomOnglet === "suivi") Suivi.rafraichir();
    if (nomOnglet === "administration") Administration.charger();
    if (nomOnglet === "scripts") {
        Scripts.remplirSelecteurBase();
        Scripts.afficherLibrairies();
    }
    if (nomOnglet === "travaux") {
        // Initialisation différée au premier passage sur l'onglet plutôt
        // qu'au chargement de la page : CodeMirror mesure la largeur des
        // caractères à l'initialisation et se retrouve mal dimensionné
        // s'il est créé pendant que son panneau est encore [hidden]
        // (display:none) - le panneau est déjà visible à ce stade de
        // basculerOnglet(), la boucle de bascule ci-dessus s'exécutant
        // avant ce bloc.
        if (!Travaux.editeur) Travaux.initEditeur();
        Travaux.chargerSchema();
        Travaux.rafraichirHistorique();
        Travaux.rafraichirRequetesEnregistrees();
    }
}

// =============================================================================
// MODALES (§4.2) - ouverture/fermeture de <dialog class="fr-modal">
// =============================================================================
// Le CSS de DSFR pilote l'affichage via la classe "fr-modal--opened", pas via
// l'attribut natif [open] seul (hérité de versions antérieures au <dialog>
// natif) : "show()" lève juste le display:none par défaut du navigateur,
// la classe fait le reste (positionnement plein écran, fondu). "show()" est
// préféré à "showModal()" pour ne pas cumuler le ::backdrop natif avec la
// surcouche déjà peinte par le CSS de DSFR (--modal, arrière-plan opaque).
const Modales = {
    ouvrir(modale) {
        modale.show();
        modale.classList.add("fr-modal--opened");
    },
    fermer(modale) {
        modale.classList.remove("fr-modal--opened");
        modale.close();
    },
    init() {
        document.querySelectorAll("[data-fr-opened]").forEach((declencheur) => {
            declencheur.addEventListener("click", () => {
                const modale = document.getElementById(declencheur.getAttribute("aria-controls"));
                if (modale) Modales.ouvrir(modale);
            });
        });
        document.querySelectorAll(".fr-modal").forEach((modale) => {
            modale.querySelector(".fr-btn--close")?.addEventListener("click", () => Modales.fermer(modale));
            // Clic sur la surcouche (en dehors de fr-modal__body) : ferme comme un clic hors-modale classique.
            modale.addEventListener("click", (evenement) => {
                if (evenement.target === modale) Modales.fermer(modale);
            });
        });
        document.addEventListener("keydown", (evenement) => {
            if (evenement.key !== "Escape") return;
            document.querySelectorAll(".fr-modal--opened").forEach((modale) => Modales.fermer(modale));
        });
    },
};

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".fr-tabs__tab").forEach((bouton) => {
        bouton.addEventListener("click", () => basculerOnglet(bouton.dataset.onglet));
    });
    Modales.init();
    Import.initGlisserDeposer();
    Auth.chargerSession();
});

// =============================================================================
// ONGLET BASES (§5.2)
// =============================================================================
const Bases = {
    async charger() {
        try {
            Etat.bases = await appelJson("/api/vue_mes_bases");
        } catch (erreur) {
            Etat.bases = [];
        }
        Bases.rendre();
    },

    rendre() {
        const mesBases = Etat.bases.filter((b) => b.je_suis_proprietaire);
        const basesPartagees = Etat.bases.filter((b) => !b.je_suis_proprietaire);

        document.getElementById("conteneur-mes-bases").innerHTML = mesBases.length
            ? Bases.tableau(mesBases, true)
            : `<p class="fr-text--sm">Aucune base pour l'instant : importez un fichier CSV depuis l'onglet Import pour en créer une.</p>`;

        document.getElementById("conteneur-bases-partagees").innerHTML = basesPartagees.length
            ? Bases.tableau(basesPartagees, false)
            : `<p class="fr-text--sm">Aucune base ne vous a été partagée.</p>`;

        Bases.attacherActions();
        Import.remplirSelecteurBase();
        Scripts.remplirSelecteurBase();
    },

    tableau(bases, proprietaire) {
        const lignes = bases.map((b) => `
            <tr>
                <td>${echapper(b.nom_pg)}</td>
                <td>${proprietaire ? "" : echapper(b.proprietaire_email)}</td>
                <td>${Number(b.taille_estimee_mo || 0).toFixed(1)} Mo</td>
                <td>${Bases.badgeAcces(b, proprietaire)}</td>
                <td>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-checkbox-circle-line bouton-selectionner" data-id="${b.id}">Sélectionner</button>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-table-line bouton-tables" data-id="${b.id}">Tables</button>
                    ${proprietaire ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-share-line bouton-partager" data-id="${b.id}">Partager</button>` : ""}
                    ${proprietaire ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-delete-bin-line" onclick="Bases.supprimerBase(${b.id}, '${b.nom_pg}')">Supprimer la base</button>` : ""}
                </td>
            </tr>
            <tr class="ligne-tables" id="tables-${b.id}" hidden><td colspan="5"></td></tr>
            ${proprietaire ? `<tr class="ligne-partage" id="partage-${b.id}" hidden><td colspan="5"></td></tr>` : ""}
        `).join("");

        return `
            <table class="fr-table"><caption class="fr-sr-only">Bases</caption>
                <thead><tr><th>Base</th><th>${proprietaire ? "" : "Propriétaire"}</th><th>Taille</th><th>Accès</th><th>Actions</th></tr></thead>
                <tbody>${lignes}</tbody>
            </table>`;
    },

    // autorise_scripts vaut NULL pour le propriétaire lui-même (LEFT JOIN
    // sans correspondance dans vue_mes_bases, §7 du schéma) : la distinction
    // "scripts autorisés / lecture seule" n'a de sens que pour un
    // bénéficiaire de partage, jamais pour le propriétaire.
    badgeAcces(base, proprietaire) {
        if (proprietaire) return '<span class="fr-badge fr-badge--sm fr-badge--green-emeraude">Propriétaire</span>';
        return base.autorise_scripts
            ? '<span class="fr-badge fr-badge--sm fr-badge--info">Scripts autorisés</span>'
            : '<span class="fr-badge fr-badge--sm">Lecture seule</span>';
    },

    attacherActions() {
        document.querySelectorAll(".bouton-selectionner").forEach((bouton) => {
            bouton.addEventListener("click", () => Bases.selectionner(Number(bouton.dataset.id)));
        });
        document.querySelectorAll(".bouton-tables").forEach((bouton) => {
            bouton.addEventListener("click", () => Bases.afficherTables(Number(bouton.dataset.id)));
        });
        document.querySelectorAll(".bouton-partager").forEach((bouton) => {
            bouton.addEventListener("click", () => Bases.afficherPartage(Number(bouton.dataset.id)));
        });
    },

    selectionner(idBase) {
        Etat.baseSelectionnee = Etat.bases.find((b) => b.id === idBase) || null;
        const rappel = document.getElementById("rappel-base-selectionnee");
        rappel.querySelector("p").textContent = `Base active : ${Etat.baseSelectionnee.nom_pg}`;
        document.getElementById("travaux-base-active").textContent = `Base active : ${Etat.baseSelectionnee.nom_pg}`;
        Travaux.chargerSchema();
    },

    async afficherPartage(idBase) {
        const ligne = document.getElementById(`partage-${idBase}`);
        const cellule = ligne.querySelector("td");
        ligne.hidden = !ligne.hidden;
        if (ligne.hidden) return;

        cellule.innerHTML = "Chargement…";
        let partages = [];
        try {
            partages = await appelJson(`/api/vue_partages_de_mes_bases?base_id=eq.${idBase}`);
        } catch (erreur) { /* liste vide en cas d'échec */ }

        const lignesPartage = partages.map((p) => `
            <li>${echapper(p.beneficiaire_email)}
                ${p.autorise_scripts ? "(scripts autorisés)" : "(lecture seule)"}
                <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-close-line" onclick="Bases.revoquer(${idBase}, '${p.beneficiaire_email}')">Retirer</button>
            </li>`).join("");

        cellule.innerHTML = `
            <div class="fr-p-2w" style="background:var(--background-alt-grey);">
                <p class="fr-text--bold fr-mb-1w">Partages actuels</p>
                <ul>${lignesPartage || "<li>Aucun partage pour l'instant.</li>"}</ul>
                <div class="fr-grid-row fr-grid-row--gutters fr-mt-2w">
                    <div class="fr-col-5"><input class="fr-input" type="email" placeholder="email du bénéficiaire" id="nouveau-partage-email-${idBase}"></div>
                    <div class="fr-col-4">
                        <div class="fr-checkbox-group fr-checkbox-group--sm">
                            <input type="checkbox" id="nouveau-partage-scripts-${idBase}">
                            <label class="fr-label" for="nouveau-partage-scripts-${idBase}">Autoriser l'exécution de scripts</label>
                        </div>
                    </div>
                    <div class="fr-col-3"><button class="fr-btn fr-btn--sm" onclick="Bases.partager(${idBase})">Accorder</button></div>
                </div>
            </div>`;
    },

    async partager(idBase) {
        const email = document.getElementById(`nouveau-partage-email-${idBase}`).value.trim();
        const autoriseScripts = document.getElementById(`nouveau-partage-scripts-${idBase}`).checked;
        try {
            await appelJson(`/orchestrateur/bases/${idBase}/partager`, {
                method: "POST",
                body: JSON.stringify({ email, autorise_scripts: autoriseScripts }),
            });
            await Bases.afficherPartage(idBase);
            await Bases.afficherPartage(idBase);
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    async revoquer(idBase, email) {
        try {
            await appelJson(`/orchestrateur/bases/${idBase}/revoquer`, {
                method: "POST",
                body: JSON.stringify({ email }),
            });
            await Bases.afficherPartage(idBase);
            await Bases.afficherPartage(idBase);
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    // Liste des tables d'une base (§5.2) : accessible aussi bien au
    // propriétaire qu'à un bénéficiaire de partage, le bouton "Supprimer"
    // par table n'apparaissant que pour le premier.
    async afficherTables(idBase) {
        const ligne = document.getElementById(`tables-${idBase}`);
        const cellule = ligne.querySelector("td");
        ligne.hidden = !ligne.hidden;
        if (ligne.hidden) return;

        cellule.innerHTML = "Chargement…";
        const base = Etat.bases.find((b) => b.id === idBase);
        let tables = [];
        try {
            tables = await appelJson(`/orchestrateur/bases/${idBase}/tables`);
        } catch (erreur) {
            cellule.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message)}</div>`;
            return;
        }

        // Nom de table retrouvé via un index numérique (data-index), jamais
        // interpolé tel quel dans le HTML : un identifiant Postgres entre
        // guillemets peut contenir n'importe quel caractère, y compris des
        // guillemets doubles - une table créée via l'onglet Travaux (§5.3,
        // requête libre) n'est pas soumise à la même normalisation que
        // celles créées par l'assistant d'import (§5.1), et echapper() ne
        // protège que du contenu texte, pas d'un attribut HTML.
        const lignesTables = tables.map((t, i) => `
            <tr>
                <td>${echapper(t.nom_table)}</td>
                <td>${t.nb_lignes}</td>
                <td>${formaterTaille(t.taille_octets)}</td>
                <td>${t.date_dernier_import ? new Date(t.date_dernier_import).toLocaleString("fr-FR") : "—"}</td>
                <td>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-eye-line bouton-fiche-table" data-index="${i}">Voir la fiche</button>
                    ${base.je_suis_proprietaire ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-delete-bin-line bouton-supprimer-table" data-index="${i}">Supprimer</button>` : ""}
                </td>
            </tr>`).join("");

        cellule.innerHTML = `
            <div class="fr-p-2w" style="background:var(--background-alt-grey);">
                <table class="fr-table fr-table--sm"><caption class="fr-sr-only">Tables de la base</caption>
                    <thead><tr><th>Table</th><th>Lignes</th><th>Taille</th><th>Dernier import</th><th>Actions</th></tr></thead>
                    <tbody>${lignesTables || `<tr><td colspan="5">Aucune table pour l'instant.</td></tr>`}</tbody>
                </table>
                <div id="fiche-table-${idBase}"></div>
            </div>`;

        cellule.querySelectorAll(".bouton-fiche-table").forEach((bouton) => {
            bouton.addEventListener("click", () => Bases.afficherFicheTable(idBase, tables[Number(bouton.dataset.index)].nom_table));
        });
        cellule.querySelectorAll(".bouton-supprimer-table").forEach((bouton) => {
            const t = tables[Number(bouton.dataset.index)];
            bouton.addEventListener("click", () => Bases.supprimerTable(idBase, t.nom_table, t.nb_lignes));
        });
    },

    // Fiche d'une table (§5.2) : colonnes/types, aperçu, date et taille du
    // dernier import (absente pour une table créée par requête SQL directe
    // dans l'onglet Travaux plutôt que par l'assistant d'import).
    async afficherFicheTable(idBase, nomTable) {
        const conteneur = document.getElementById(`fiche-table-${idBase}`);
        conteneur.innerHTML = "Chargement de la fiche…";
        let fiche;
        try {
            fiche = await appelJson(`/orchestrateur/bases/${idBase}/tables/${encodeURIComponent(nomTable)}`);
        } catch (erreur) {
            conteneur.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message)}</div>`;
            return;
        }

        const lignesColonnes = fiche.colonnes.map((c) => `<tr><td>${echapper(c.nom)}</td><td>${echapper(c.type)}</td></tr>`).join("");
        const entetesApercu = fiche.apercu_entetes.map((c) => `<th>${echapper(c)}</th>`).join("");
        const lignesApercu = fiche.apercu_lignes.map((l) => `<tr>${l.map((v) => `<td>${echapper(v)}</td>`).join("")}</tr>`).join("");

        conteneur.innerHTML = `
            <div class="fr-mt-2w fr-p-2w" style="border:1px solid var(--border-default-grey);">
                <p class="fr-text--bold">Fiche « ${echapper(fiche.nom_table)} »</p>
                <p class="fr-text--sm">
                    ${fiche.nb_lignes} ligne(s) — ${formaterTaille(fiche.taille_octets)}
                    — dernier import : ${fiche.date_dernier_import ? new Date(fiche.date_dernier_import).toLocaleString("fr-FR") : "aucun (table créée par requête SQL)"}
                </p>

                <table class="fr-table fr-table--sm"><caption>Colonnes</caption>
                    <thead><tr><th>Nom</th><th>Type</th></tr></thead>
                    <tbody>${lignesColonnes}</tbody>
                </table>

                <p class="fr-text--bold fr-mt-2w">Aperçu</p>
                <div style="overflow-x:auto;">
                    <table class="fr-table fr-table--sm"><caption class="fr-sr-only">Aperçu des données</caption>
                        <thead><tr>${entetesApercu}</tr></thead>
                        <tbody>${lignesApercu}</tbody>
                    </table>
                </div>
            </div>`;
    },

    async supprimerTable(idBase, nomTable, nbLignes) {
        if (!confirm(`Supprimer la table « ${nomTable} » et ses ${nbLignes} ligne(s) ? Cette action est irréversible.`)) return;
        try {
            await appelJson(`/orchestrateur/bases/${idBase}/tables/${encodeURIComponent(nomTable)}`, { method: "DELETE" });
            await Bases.afficherTables(idBase);
            await Bases.afficherTables(idBase);
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    // Suppression d'une base entière (§5.2) : confirmation renforcée par
    // saisie du nom exact, en plus de la vérification de propriété faite
    // côté serveur - la suppression physique est différée en job (§9),
    // suivie comme les autres traitements dans l'onglet Suivi.
    async supprimerBase(idBase, nomBase) {
        const saisie = prompt(`Action irréversible. Pour confirmer la suppression de la base, saisissez son nom exact :\n${nomBase}`);
        if (saisie === null) return;
        if (saisie !== nomBase) return alert("Nom incorrect, suppression annulée.");

        try {
            const resultat = await appelJson(`/orchestrateur/bases/${idBase}/supprimer`, { method: "POST" });
            if (Etat.baseSelectionnee && Etat.baseSelectionnee.id === idBase) {
                Etat.baseSelectionnee = null;
                document.getElementById("rappel-base-selectionnee").querySelector("p").textContent =
                    "Aucune base sélectionnée. Choisissez une base ci-dessous pour l'utiliser dans les onglets Travaux et Scripts.";
                document.getElementById("travaux-base-active").textContent = "";
            }
            alert(`Suppression de la base en cours (job n°${resultat.id_job}), suivez sa progression dans l'onglet Suivi.`);
            await Bases.charger();
        } catch (erreur) {
            alert(erreur.message);
        }
    },
};

// =============================================================================
// ONGLET TRAVAUX (§5.3)
// =============================================================================
const Travaux = {
    editeur: null,
    _historiqueCache: [],
    _requetesEnregistreesCache: [],

    // CodeMirror.fromTextArea masque le <textarea> d'origine et le
    // synchronise automatiquement (utile si un jour un <form> le soumet
    // directement) - toute lecture/écriture de la requête doit passer par
    // Travaux.editeur, plus par document.getElementById("champ-sql").
    initEditeur() {
        Travaux.editeur = CodeMirror.fromTextArea(document.getElementById("champ-sql"), {
            mode: "text/x-sql",
            lineNumbers: true,
            lineWrapping: true,
            extraKeys: { "Ctrl-Space": "autocomplete" },
            hintOptions: { tables: {} },
        });
    },

    // Rafraîchit l'auto-complétion des noms de tables/colonnes (§5.3) sur
    // la base actuellement sélectionnée - appelé à chaque changement de
    // base (Bases.selectionner), pas seulement à l'ouverture de l'onglet.
    async chargerSchema() {
        if (!Etat.baseSelectionnee || !Travaux.editeur) return;
        try {
            const schema = await appelJson(`/orchestrateur/bases/${Etat.baseSelectionnee.id}/schema`);
            Travaux.editeur.setOption("hintOptions", { tables: schema });
        } catch (erreur) { /* auto-complétion simplement indisponible */ }
    },

    async executer() {
        const conteneur = document.getElementById("resultat-travaux");
        if (!Etat.baseSelectionnee) return afficherErreur(conteneur, new Error("Sélectionnez d'abord une base dans l'onglet Bases."));
        const requete = Travaux.editeur.getValue().trim();
        if (!requete) return;

        const estEcriture = /^\s*(insert|update|delete|create|drop|alter|truncate|grant|revoke)\b/i.test(requete);
        if (estEcriture && !confirm("Cette requête modifie la structure ou les données. Continuer ?")) return;

        conteneur.innerHTML = "Exécution…";
        try {
            // appel() plutôt qu'appelJson() : un dépassement de délai (409
            // ci-dessous, "delai_depasse") appelle une réponse différente
            // d'une erreur SQL ordinaire (§5.3, §11), à distinguer avant
            // d'afficher quoi que ce soit.
            const reponse = await appel("/orchestrateur/sql", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ base_id: Etat.baseSelectionnee.id, requete }),
            });
            const resultat = await reponse.json().catch(() => ({}));
            if (!reponse.ok) {
                if (resultat.delai_depasse) return Travaux.afficherDelaiDepasse();
                throw new Error(resultat.erreur || `Erreur HTTP ${reponse.status}`);
            }
            Travaux.afficherResultat(resultat);
            Travaux.rafraichirHistorique();
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },

    afficherDelaiDepasse() {
        document.getElementById("resultat-travaux").innerHTML = `
            <div class="fr-alert fr-alert--warning fr-alert--sm">
                <p>Délai maximal dépassé : la requête a été interrompue avant de se terminer.</p>
                <ul class="fr-btns-group fr-btns-group--inline fr-mt-1w">
                    <li><button class="fr-btn fr-btn--sm" onclick="Travaux.executerEnTacheDeFond()">Exécuter en tâche de fond</button></li>
                </ul>
            </div>`;
    },

    async executerEnTacheDeFond() {
        const conteneur = document.getElementById("resultat-travaux");
        const requete = Travaux.editeur.getValue().trim();
        if (!Etat.baseSelectionnee || !requete) return;
        conteneur.innerHTML = "Mise en file d'attente…";
        try {
            const resultat = await appelJson("/orchestrateur/sql/job", {
                method: "POST",
                body: JSON.stringify({ base_id: Etat.baseSelectionnee.id, requete }),
            });
            conteneur.innerHTML = `<div class="fr-alert fr-alert--info fr-alert--sm">Requête mise en file d'attente (job n°${resultat.id_job}) : suivez sa progression dans l'onglet Suivi, vous serez notifié par mail à la fin.</div>`;
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },

    afficherResultat(resultat) {
        const conteneur = document.getElementById("resultat-travaux");
        if (resultat.type === "ecriture") {
            conteneur.innerHTML = `<div class="fr-alert fr-alert--success fr-alert--sm">${resultat.lignes_affectees} ligne(s) affectée(s) (${resultat.duree_ms} ms).</div>`;
            return;
        }
        const entetes = resultat.colonnes.map((c) => `<th>${echapper(c)}</th>`).join("");
        const lignes = resultat.lignes.map((ligne) => `<tr>${ligne.map((v) => `<td>${echapper(v)}</td>`).join("")}</tr>`).join("");
        conteneur.innerHTML = `
            <p class="fr-text--sm">${resultat.lignes.length} ligne(s) affichée(s) (${resultat.duree_ms} ms)${resultat.tronque ? " — résultat tronqué à l'écran, utilisez « Exporter en CSV » pour tout récupérer" : ""}.</p>
            <div style="overflow-x:auto;"><table class="fr-table"><caption class="fr-sr-only">Résultat</caption><thead><tr>${entetes}</tr></thead><tbody>${lignes}</tbody></table></div>`;
    },

    async exporter() {
        if (!Etat.baseSelectionnee) return alert("Sélectionnez d'abord une base.");
        const requete = Travaux.editeur.getValue().trim();
        if (!requete) return;
        const reponse = await appel("/orchestrateur/sql/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ base_id: Etat.baseSelectionnee.id, requete }),
        });
        if (!reponse.ok) {
            const corps = await reponse.json().catch(() => ({}));
            return alert(corps.erreur || "Export impossible.");
        }
        const blob = await reponse.blob();
        const lien = document.createElement("a");
        lien.href = URL.createObjectURL(blob);
        lien.download = "export.csv";
        lien.click();
        URL.revokeObjectURL(lien.href);
    },

    // Historique persistant (§5.3) : lu directement via l'API de requêtage
    // (vue_mon_historique se filtre déjà elle-même sur l'appelant, §8.4) -
    // écrit, lui, par l'orchestrateur à chaque exécution (§sql, §9).
    async rafraichirHistorique() {
        let historique = [];
        try {
            historique = await appelJson("/api/vue_mon_historique");
        } catch (erreur) { /* liste vide en cas d'échec */ }
        Travaux._historiqueCache = historique;

        document.getElementById("historique-travaux").innerHTML = historique.slice(0, 20).map((h, i) => `
            <li class="fr-mb-2w">
                <span class="fr-badge fr-badge--sm ${h.succes ? "fr-badge--success" : "fr-badge--error"}">${h.succes ? "OK" : "échec"}</span>
                <code>${echapper(tronquer(h.requete, 80))}</code><br>
                <span class="fr-text--xs">
                    ${new Date(h.date_execution).toLocaleString("fr-FR")} — ${h.duree_ms != null ? h.duree_ms + " ms" : "—"}
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-refresh-line" onclick="Travaux.reexecuterHistorique(${i})">Réexécuter</button>
                </span>
            </li>`).join("") || `<li class="fr-text--sm">Aucune requête exécutée pour l'instant.</li>`;
    },

    // "Relecture" (§5.3) : la requête est déjà lisible dans la liste elle-même
    // ; "réexécution" charge dans l'éditeur puis relance immédiatement.
    async reexecuterHistorique(index) {
        const h = Travaux._historiqueCache[index];
        if (!h) return;
        Travaux.editeur.setValue(h.requete);
        await Travaux.executer();
    },

    // Requêtes enregistrées (§5.3) : distinct de l'historique - un favori
    // nommé par l'utilisateur, jamais généré automatiquement.
    async rafraichirRequetesEnregistrees() {
        let requetes = [];
        try {
            requetes = await appelJson("/api/vue_mes_requetes_enregistrees");
        } catch (erreur) { /* liste vide en cas d'échec */ }
        Travaux._requetesEnregistreesCache = requetes;

        document.getElementById("requetes-enregistrees").innerHTML = requetes.map((r) => `
            <li class="fr-mb-1w">
                <strong>${echapper(r.nom)}</strong>
                <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-file-text-line" onclick="Travaux.chargerRequeteEnregistree(${r.id})">Charger</button>
                <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-delete-bin-line" onclick="Travaux.supprimerRequeteEnregistree(${r.id})">Supprimer</button>
            </li>`).join("") || `<li class="fr-text--sm">Aucune requête enregistrée.</li>`;
    },

    chargerRequeteEnregistree(id) {
        const r = Travaux._requetesEnregistreesCache.find((r) => r.id === id);
        if (r) Travaux.editeur.setValue(r.requete);
    },

    async enregistrerRequete() {
        const requete = Travaux.editeur.getValue().trim();
        if (!requete) return;
        const nom = prompt("Nom de la requête enregistrée :");
        if (!nom) return;
        try {
            await appelJson("/api/rpc/enregistrer_requete", {
                method: "POST",
                body: JSON.stringify({ _nom: nom, _requete: requete }),
            });
            await Travaux.rafraichirRequetesEnregistrees();
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    async supprimerRequeteEnregistree(id) {
        if (!confirm("Supprimer cette requête enregistrée ?")) return;
        try {
            await appelJson("/api/rpc/supprimer_requete_enregistree", {
                method: "POST",
                body: JSON.stringify({ _id: id }),
            });
            await Travaux.rafraichirRequetesEnregistrees();
        } catch (erreur) {
            alert(erreur.message);
        }
    },
};

// =============================================================================
// ONGLET IMPORT (§5.1)
// =============================================================================
const Import = {
    // Glisser-déposer (§5.1, étape 1), en complément de la sélection
    // classique par clic déjà portée par <input type="file">. preventDefault
    // sur dragover est indispensable : sans lui, le navigateur refuse
    // silencieusement l'événement "drop" et ouvre le fichier dans un nouvel
    // onglet à la place (comportement par défaut de tout élément non-cible
    // de dépôt).
    initGlisserDeposer() {
        const zone = document.getElementById("zone-depot-csv");
        ["dragenter", "dragover"].forEach((evenement) => {
            zone.addEventListener(evenement, (e) => {
                e.preventDefault();
                zone.classList.add("zone-glisser-survolee");
            });
        });
        ["dragleave", "drop"].forEach((evenement) => {
            zone.addEventListener(evenement, (e) => {
                e.preventDefault();
                zone.classList.remove("zone-glisser-survolee");
            });
        });
        zone.addEventListener("drop", (e) => {
            const fichier = e.dataTransfer.files[0];
            if (!fichier) return;
            document.getElementById("champ-fichier-csv").files = e.dataTransfer.files;
            Import.analyser();
        });
    },

    async analyser() {
        const fichier = document.getElementById("champ-fichier-csv").files[0];
        const conteneur = document.getElementById("resultat-import");
        if (!fichier) return afficherErreur(conteneur, new Error("Choisissez un fichier."));

        const donnees = new FormData();
        donnees.append("fichier", fichier);
        donnees.append("avec_entete", document.getElementById("import-avec-entete").checked);
        conteneur.innerHTML = "Analyse en cours…";
        try {
            const apercu = await appelJson("/orchestrateur/import/apercu", { method: "POST", body: donnees });
            Etat.dernierApercu = apercu;
            Import.afficherAssistant(apercu, fichier.name);
            conteneur.innerHTML = "";
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },

    afficherAssistant(apercu, nomFichier) {
        document.getElementById("assistant-import").hidden = false;
        document.getElementById("import-encodage").textContent = apercu.encodage_detecte;
        document.getElementById("import-delimiteur").textContent = apercu.delimiteur_detecte === "\t" ? "tabulation" : apercu.delimiteur_detecte;
        document.getElementById("import-nb-lignes").textContent = apercu.nb_lignes_totales;
        document.getElementById("import-nom-table").value = nomFichier.replace(/\.[^.]+$/, "");
        document.getElementById("import-valeur-manquante").value = "";

        document.getElementById("import-colonnes").innerHTML = apercu.colonnes.map((c, i) => `
            <tr>
                <td>${echapper(c.nom_source)}</td>
                <td><input class="fr-input" type="text" id="import-col-nom-${i}" value="${echapper(c.nom_normalise)}"></td>
                <td><select class="fr-select" id="import-col-type-${i}">
                    ${TYPES_COLONNE.map((t) => `<option ${t === c.type_suggere ? "selected" : ""}>${t}</option>`).join("")}
                </select></td>
            </tr>`).join("");

        Import.remplirSelecteurBase();
    },

    remplirSelecteurBase() {
        const selecteur = document.getElementById("import-base-cible");
        if (!selecteur) return;
        const mesBases = Etat.bases.filter((b) => b.je_suis_proprietaire);
        selecteur.innerHTML = '<option value="">Ma base personnelle (créée si nécessaire)</option>' +
            mesBases.map((b) => `<option value="${b.id}">${echapper(b.nom_pg)}</option>`).join("");
    },

    // remplacer=true seulement lors du second appel, après confirmation
    // explicite de l'utilisateur suite à une collision (§5.1, étape 6).
    colonnesSaisies() {
        return Etat.dernierApercu.colonnes.map((_, i) => ({
            nom_normalise: document.getElementById(`import-col-nom-${i}`).value.trim(),
            type: document.getElementById(`import-col-type-${i}`).value,
        }));
    },

    // Point d'entrée du bouton « Confirmer l'import » : contrôle de
    // cohérence sur tout le fichier avant tout chargement (§5.1, étape 4),
    // pas seulement sur les 50 lignes de l'aperçu.
    async valider() {
        const conteneur = document.getElementById("resultat-import");
        const apercu = Etat.dernierApercu;
        if (!apercu) return;

        conteneur.innerHTML = "Contrôle de cohérence en cours…";
        try {
            const verification = await appelJson("/orchestrateur/import/verifier", {
                method: "POST",
                body: JSON.stringify({
                    jeton: apercu.jeton,
                    colonnes: Import.colonnesSaisies(),
                    encodage: apercu.encodage_detecte,
                    delimiteur: apercu.delimiteur_detecte,
                    valeur_manquante: document.getElementById("import-valeur-manquante").value,
                    avec_entete: apercu.avec_entete,
                }),
            });
            if (verification.nb_lignes_anomalies > 0) {
                Import.afficherAnomalies(verification);
                return;
            }
        } catch (erreur) {
            return afficherErreur(conteneur, erreur);
        }

        Import.executerImport(false, []);
    },

    afficherAnomalies(verification) {
        const conteneur = document.getElementById("resultat-import");
        const lignesDetail = verification.anomalies.map((a) =>
            `<li>Ligne ${a.ligne}, colonne « ${echapper(a.colonne)} » : valeur « ${echapper(a.valeur)} » incompatible avec le type choisi.</li>`
        ).join("");
        const troncature = verification.nb_lignes_anomalies > verification.anomalies.length
            ? `<p class="fr-text--sm">… et ${verification.nb_lignes_anomalies - verification.anomalies.length} autre(s) ligne(s) en anomalie non détaillée(s) ici.</p>`
            : "";

        conteneur.innerHTML = `
            <div class="fr-alert fr-alert--warning fr-alert--sm">
                <p><strong>${verification.nb_lignes_anomalies}</strong> ligne(s) sur ${verification.nb_lignes_totales} ne correspondent pas au type choisi pour au moins une colonne :</p>
                <ul class="fr-text--sm">${lignesDetail}</ul>
                ${troncature}
                <ul class="fr-btns-group fr-btns-group--inline fr-mt-2w">
                    <li><button class="fr-btn fr-btn--sm fr-btn--secondary" onclick="Import.confirmerExclusion()">Exclure ces lignes et importer le reste</button></li>
                    <li><button class="fr-btn fr-btn--sm fr-btn--tertiary" onclick="document.getElementById('resultat-import').innerHTML=''">Corriger le typage ci-dessus</button></li>
                    <li><button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline" onclick="Import.annuler()">Annuler l'import</button></li>
                </ul>
            </div>`;
        Etat.derniereVerification = verification;
    },

    confirmerExclusion() {
        const lignes = Etat.derniereVerification.lignes_anomalies;
        if (!confirm(`${lignes.length} ligne(s) seront définitivement exclues de l'import. Continuer ?`)) return;
        Import.executerImport(false, lignes);
    },

    annuler() {
        document.getElementById("assistant-import").hidden = true;
        document.getElementById("resultat-import").innerHTML = "";
        Etat.dernierApercu = null;
        Etat.derniereVerification = null;
    },

    async executerImport(remplacer, exclureLignes) {
        const conteneur = document.getElementById("resultat-import");
        const apercu = Etat.dernierApercu;
        const baseId = document.getElementById("import-base-cible").value || null;

        conteneur.innerHTML = "Import en cours…";
        try {
            // appel() plutôt qu'appelJson() : la réponse 409 « collision »
            // n'est pas une erreur à afficher telle quelle, mais un choix à
            // proposer à l'utilisateur (renommer ou remplacer), donc le
            // statut HTTP doit être inspecté avant de décider quoi faire.
            const reponse = await appel("/orchestrateur/import/valider", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    jeton: apercu.jeton,
                    base_id: baseId ? Number(baseId) : null,
                    nom_table: document.getElementById("import-nom-table").value.trim(),
                    colonnes: Import.colonnesSaisies(),
                    encodage: apercu.encodage_detecte,
                    delimiteur: apercu.delimiteur_detecte,
                    valeur_manquante: document.getElementById("import-valeur-manquante").value,
                    avec_entete: apercu.avec_entete,
                    remplacer,
                    exclure_lignes: exclureLignes,
                }),
            });
            const resultat = await reponse.json().catch(() => ({}));

            if (reponse.status === 409 && resultat.statut === "collision") {
                Import.afficherCollision(resultat.table, exclureLignes);
                return;
            }
            if (!reponse.ok) throw new Error(resultat.erreur || `Erreur HTTP ${reponse.status}`);

            const suffixeExclusion = exclureLignes.length ? ` (${exclureLignes.length} ligne(s) exclue(s))` : "";
            conteneur.innerHTML = resultat.statut === "termine"
                ? `<div class="fr-alert fr-alert--success fr-alert--sm">Table « ${echapper(resultat.table)} » créée avec succès${suffixeExclusion}.</div>`
                : `<div class="fr-alert fr-alert--info fr-alert--sm">Fichier volumineux : import mis en file d'attente (job n°${resultat.id_job}), suivez sa progression dans l'onglet Suivi.</div>`;
            document.getElementById("assistant-import").hidden = true;
            await Bases.charger();
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },

    afficherCollision(nomTable, exclureLignes) {
        const conteneur = document.getElementById("resultat-import");
        conteneur.innerHTML = `
            <div class="fr-alert fr-alert--warning fr-alert--sm">
                <p>Une table « ${echapper(nomTable)} » existe déjà dans cette base.</p>
                <ul class="fr-btns-group fr-btns-group--inline fr-mt-1w">
                    <li><button class="fr-btn fr-btn--sm fr-btn--secondary" onclick="Import.confirmerRemplacement()">Remplacer son contenu</button></li>
                </ul>
                <p class="fr-text--sm fr-mt-1w">Ou modifiez le nom de la table ci-dessus puis validez à nouveau pour créer une table distincte.</p>
            </div>`;
        Etat.dernieresLignesExclues = exclureLignes;
    },

    confirmerRemplacement() {
        if (!confirm("Le contenu actuel de cette table sera définitivement supprimé et remplacé par le nouveau fichier. Continuer ?")) return;
        Import.executerImport(true, Etat.dernieresLignesExclues || []);
    },
};

// =============================================================================
// ONGLET SCRIPTS (§5.4)
// =============================================================================
const Scripts = {
    _librairiesChargees: false,

    // Liste statique (§5.4) : fichier JSON servi directement par Nginx,
    // pas un appel à l'orchestrateur - reflet de ce qui est réellement
    // installé dans l'image d'exécution vendorisée (§7.7), figé au
    // moment de sa construction plutôt que découvert dynamiquement.
    async afficherLibrairies() {
        if (Scripts._librairiesChargees) return;
        const conteneur = document.getElementById("scripts-librairies");
        try {
            const reponse = await fetch("librairies-scripts.json");
            const librairies = await reponse.json();
            const ligne = (l) => `<code>${echapper(l.module)}</code>`;
            conteneur.innerHTML = `
                <p class="fr-callout__text fr-text--sm">
                    <strong>Librairies disponibles dans l'environnement d'exécution</strong><br>
                    Python : ${librairies.python.map(ligne).join(", ")}<br>
                    R : ${librairies.r.map(ligne).join(", ")}
                </p>`;
            Scripts._librairiesChargees = true;
        } catch (erreur) {
            conteneur.innerHTML = `<p class="fr-callout__text fr-text--sm">Liste des librairies indisponible pour l'instant.</p>`;
        }
    },

    remplirSelecteurBase() {
        const selecteur = document.getElementById("scripts-base-cible");
        if (!selecteur) return;
        const basesAutorisees = Etat.bases.filter((b) => b.je_suis_proprietaire || b.autorise_scripts);
        selecteur.innerHTML = basesAutorisees.map((b) => `<option value="${b.id}">${echapper(b.nom_pg)}</option>`).join("")
            || '<option value="">Aucune base disponible pour l\'exécution de scripts</option>';
    },

    async deposer() {
        const conteneur = document.getElementById("resultat-scripts");
        const fichier = document.getElementById("champ-fichier-script").files[0];
        const baseId = document.getElementById("scripts-base-cible").value;
        if (!fichier || !baseId) return afficherErreur(conteneur, new Error("Choisissez une base et un fichier .py ou .R."));

        const donnees = new FormData();
        donnees.append("fichier", fichier);
        donnees.append("base_id", baseId);

        conteneur.innerHTML = "Envoi du script…";
        try {
            const resultat = await appelJson("/orchestrateur/scripts/deposer", { method: "POST", body: donnees });
            conteneur.innerHTML = `<div class="fr-alert fr-alert--info fr-alert--sm">Script mis en file d'attente (job n°${resultat.id_job}). Suivez son exécution dans l'onglet Suivi.</div>`;
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },
};

// =============================================================================
// ONGLET SUIVI (§5.5)
// =============================================================================
const Suivi = {
    _intervallesJournal: {},

    async rafraichir() {
        // Un rafraîchissement (manuel ou périodique) reconstruit toute la
        // table : un intervalle de journal pointant vers une ligne que ce
        // rendu vient de recréer (hidden par défaut) tournerait pour rien
        // sans jamais s'arrêter de lui-même.
        Object.values(Suivi._intervallesJournal).forEach(clearInterval);
        Suivi._intervallesJournal = {};

        let jobs = [];
        try {
            jobs = await appelJson("/api/vue_mes_jobs?order=date_creation.desc");
        } catch (erreur) { /* tableau vide en cas d'échec */ }

        const badges = { en_attente: "fr-badge--info", en_cours: "fr-badge--info", termine: "fr-badge--success", erreur: "fr-badge--error", annule: "" };
        const estScript = (type) => type === "script_python" || type === "script_r";

        document.getElementById("table-suivi").innerHTML = jobs.map((job) => `
            <tr>
                <td>${echapper(job.type)}</td>
                <td><span class="fr-badge fr-badge--sm ${badges[job.statut] || ""}">${echapper(job.statut)}</span></td>
                <td>${new Date(job.date_creation).toLocaleString("fr-FR")}</td>
                <td>${echapper(job.message_erreur || "")}</td>
                <td>
                    ${["en_attente", "en_cours"].includes(job.statut) ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-close-line" onclick="Suivi.annuler(${job.id})">Annuler</button>` : ""}
                    ${estScript(job.type) && job.statut !== "annule" ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-file-text-line" onclick="Suivi.afficherJournal(${job.id})">Journal</button>` : ""}
                    ${job.statut === "termine" && job.chemin_resultat ? `<a class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-download-line" href="/orchestrateur/jobs/${job.id}/telecharger">Télécharger</a>` : ""}
                </td>
            </tr>
            ${estScript(job.type) ? `<tr class="ligne-journal" id="journal-${job.id}" hidden><td colspan="5"></td></tr>` : ""}`).join("")
            || `<tr><td colspan="5">Aucun traitement pour l'instant.</td></tr>`;
    },

    async annuler(idJob) {
        await appelJson("/api/rpc/annuler_job", { method: "POST", body: JSON.stringify({ _id_job: idJob }) });
        Suivi.rafraichir();
    },

    // Journal consultable pendant l'exécution, pas seulement une fois le
    // job terminé (§5.4) : rafraîchi périodiquement tant que le job est
    // en_attente/en_cours, arrêté de lui-même dès qu'il ne l'est plus.
    async afficherJournal(idJob) {
        const ligne = document.getElementById(`journal-${idJob}`);
        ligne.hidden = !ligne.hidden;
        if (ligne.hidden) {
            clearInterval(Suivi._intervallesJournal[idJob]);
            delete Suivi._intervallesJournal[idJob];
            return;
        }
        await Suivi.rafraichirJournal(idJob);
        Suivi._intervallesJournal[idJob] = setInterval(() => Suivi.rafraichirJournal(idJob), 3000);
    },

    async rafraichirJournal(idJob) {
        const cellule = document.querySelector(`#journal-${idJob} td`);
        if (!cellule) return;
        try {
            const resultat = await appelJson(`/orchestrateur/jobs/${idJob}/journal`);
            cellule.innerHTML = `
                <pre class="fr-p-2w" style="background:var(--background-alt-grey); max-height:300px; overflow:auto; white-space:pre-wrap;">${echapper(resultat.journal) || "(journal vide pour l'instant)"}</pre>
                ${resultat.tronque ? `<p class="fr-text--xs">Journal tronqué à l'affichage (le fichier complet est inclus dans l'archive téléchargeable une fois le job terminé).</p>` : ""}`;
            if (resultat.statut !== "en_attente" && resultat.statut !== "en_cours") {
                clearInterval(Suivi._intervallesJournal[idJob]);
                delete Suivi._intervallesJournal[idJob];
            }
        } catch (erreur) {
            cellule.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message)}</div>`;
            clearInterval(Suivi._intervallesJournal[idJob]);
            delete Suivi._intervallesJournal[idJob];
        }
    },
};

// =============================================================================
// PANNEAU ADMINISTRATION (§5.6)
// =============================================================================
const Administration = {
    async charger() {
        Administration.chargerUtilisateurs();
        Administration.chargerQuotas();
        Administration.chargerAudit();
    },

    async chargerUtilisateurs() {
        const utilisateurs = await appelJson("/api/utilisateurs?order=email.asc").catch(() => []);
        document.getElementById("table-utilisateurs").innerHTML = utilisateurs.map((u) => `
            <tr>
                <td>${echapper(u.email)}</td>
                <td>${echapper(u.nom_complet)}</td>
                <td><span class="fr-badge fr-badge--sm ${u.profil === "administrateur" ? "fr-badge--error" : "fr-badge--info"}">${echapper(u.profil)}</span></td>
                <td>${u.actif ? "Oui" : "Non"}</td>
                <td>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-lock-unlock-line" onclick="Administration.reinitialiserMdp('${u.email}')">Réinitialiser mdp</button>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-${u.actif ? "close-circle-line" : "check-line"}" onclick="Administration.basculerActivation('${u.email}', ${u.actif})">${u.actif ? "Désactiver" : "Réactiver"}</button>
                </td>
            </tr>`).join("");
    },

    async creerUtilisateur(evenement) {
        evenement.preventDefault();
        try {
            await appelJson("/api/rpc/creer_utilisateur", {
                method: "POST",
                body: JSON.stringify({
                    _email: document.getElementById("admin-nouvel-email").value.trim(),
                    _password: document.getElementById("admin-nouveau-mdp").value,
                    _nom_complet: document.getElementById("admin-nouveau-nom").value.trim(),
                    _profil: document.getElementById("admin-nouveau-profil").value,
                }),
            });
            document.getElementById("formulaire-creation-utilisateur").reset();
            Administration.chargerUtilisateurs();
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    async reinitialiserMdp(email) {
        const nouveauMdp = prompt(`Nouveau mot de passe pour ${email} (12 caractères minimum) :`);
        if (!nouveauMdp) return;
        try {
            await appelJson("/api/rpc/reinitialiser_mdp", { method: "POST", body: JSON.stringify({ _email: email, _nouveau_mdp: nouveauMdp }) });
            alert("Mot de passe réinitialisé.");
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    async basculerActivation(email, actifActuellement) {
        const fonction = actifActuellement ? "desactiver_utilisateur" : "reactiver_utilisateur";
        await appelJson(`/api/rpc/${fonction}`, { method: "POST", body: JSON.stringify({ _email: email }) });
        Administration.chargerUtilisateurs();
    },

    async chargerQuotas() {
        const parametres = await appelJson("/api/parametres?order=cle.asc").catch(() => []);
        document.getElementById("conteneur-quotas").innerHTML = parametres.map((p) => `
            <div class="fr-input-group fr-input-group--sm" style="display:inline-block; margin-right:1rem;">
                <label class="fr-label">${echapper(p.cle)}</label>
                <input class="fr-input" type="text" value="${echapper(p.valeur)}" id="quota-${p.cle}"
                    onchange="Administration.modifierQuota('${p.cle}', this.value)">
            </div>`).join("");
    },

    async modifierQuota(cle, valeur) {
        await appelJson(`/api/parametres?cle=eq.${encodeURIComponent(cle)}`, {
            method: "PATCH",
            body: JSON.stringify({ valeur }),
        }).catch((erreur) => alert(erreur.message));
    },

    async chargerAudit() {
        const audit = await appelJson("/api/audit_logs?order=id.desc&limit=50").catch(() => []);
        document.getElementById("table-audit").innerHTML = audit.map((a) => `
            <tr>
                <td>${new Date(a.date_action).toLocaleString("fr-FR")}</td>
                <td>${echapper(a.utilisateur)}</td>
                <td>${echapper(a.action)}</td>
                <td>${echapper(a.cible || "")}</td>
            </tr>`).join("");
    },
};
