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
    if (nomOnglet === "scripts") Scripts.remplirSelecteurBase();
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".fr-tabs__tab").forEach((bouton) => {
        bouton.addEventListener("click", () => basculerOnglet(bouton.dataset.onglet));
    });
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
                    ${proprietaire ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-share-line bouton-partager" data-id="${b.id}">Partager</button>` : ""}
                </td>
            </tr>
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
        document.querySelectorAll(".bouton-partager").forEach((bouton) => {
            bouton.addEventListener("click", () => Bases.afficherPartage(Number(bouton.dataset.id)));
        });
    },

    selectionner(idBase) {
        Etat.baseSelectionnee = Etat.bases.find((b) => b.id === idBase) || null;
        const rappel = document.getElementById("rappel-base-selectionnee");
        rappel.querySelector("p").textContent = `Base active : ${Etat.baseSelectionnee.nom_pg}`;
        document.getElementById("travaux-base-active").textContent = `Base active : ${Etat.baseSelectionnee.nom_pg}`;
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
};

// =============================================================================
// ONGLET TRAVAUX (§5.3)
// =============================================================================
const Travaux = {
    historique: [],

    async executer() {
        const conteneur = document.getElementById("resultat-travaux");
        if (!Etat.baseSelectionnee) return afficherErreur(conteneur, new Error("Sélectionnez d'abord une base dans l'onglet Bases."));
        const requete = document.getElementById("champ-sql").value.trim();
        if (!requete) return;

        const estEcriture = /^\s*(insert|update|delete|create|drop|alter|truncate|grant|revoke)\b/i.test(requete);
        if (estEcriture && !confirm("Cette requête modifie la structure ou les données. Continuer ?")) return;

        conteneur.innerHTML = "Exécution…";
        try {
            const resultat = await appelJson("/orchestrateur/sql", {
                method: "POST",
                body: JSON.stringify({ base_id: Etat.baseSelectionnee.id, requete }),
            });
            Travaux.afficherResultat(resultat);
            Travaux.historique.unshift({ requete, date: new Date() });
            Travaux.rendreHistorique();
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
        const requete = document.getElementById("champ-sql").value.trim();
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

    rendreHistorique() {
        document.getElementById("historique-travaux").innerHTML = Travaux.historique
            .slice(0, 10)
            .map((h) => `<li><code>${echapper(h.requete)}</code> — ${h.date.toLocaleTimeString("fr-FR")}</li>`)
            .join("");
    },
};

// =============================================================================
// ONGLET IMPORT (§5.1)
// =============================================================================
const Import = {
    async analyser() {
        const fichier = document.getElementById("champ-fichier-csv").files[0];
        const conteneur = document.getElementById("resultat-import");
        if (!fichier) return afficherErreur(conteneur, new Error("Choisissez un fichier."));

        const donnees = new FormData();
        donnees.append("fichier", fichier);
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

    async valider() {
        const conteneur = document.getElementById("resultat-import");
        const apercu = Etat.dernierApercu;
        if (!apercu) return;

        const colonnes = apercu.colonnes.map((_, i) => ({
            nom_normalise: document.getElementById(`import-col-nom-${i}`).value.trim(),
            type: document.getElementById(`import-col-type-${i}`).value,
        }));
        const baseId = document.getElementById("import-base-cible").value || null;

        conteneur.innerHTML = "Import en cours…";
        try {
            const resultat = await appelJson("/orchestrateur/import/valider", {
                method: "POST",
                body: JSON.stringify({
                    jeton: apercu.jeton,
                    base_id: baseId ? Number(baseId) : null,
                    nom_table: document.getElementById("import-nom-table").value.trim(),
                    colonnes,
                    encodage: apercu.encodage_detecte,
                    delimiteur: apercu.delimiteur_detecte,
                    valeur_manquante: document.getElementById("import-valeur-manquante").value,
                }),
            });
            conteneur.innerHTML = resultat.statut === "termine"
                ? `<div class="fr-alert fr-alert--success fr-alert--sm">Table « ${echapper(resultat.table)} » créée avec succès.</div>`
                : `<div class="fr-alert fr-alert--info fr-alert--sm">Fichier volumineux : import mis en file d'attente (job n°${resultat.id_job}), suivez sa progression dans l'onglet Suivi.</div>`;
            document.getElementById("assistant-import").hidden = true;
            await Bases.charger();
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },
};

// =============================================================================
// ONGLET SCRIPTS (§5.4)
// =============================================================================
const Scripts = {
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
    async rafraichir() {
        let jobs = [];
        try {
            jobs = await appelJson("/api/vue_mes_jobs?order=date_creation.desc");
        } catch (erreur) { /* tableau vide en cas d'échec */ }

        const badges = { en_attente: "fr-badge--info", en_cours: "fr-badge--info", termine: "fr-badge--success", erreur: "fr-badge--error", annule: "" };

        document.getElementById("table-suivi").innerHTML = jobs.map((job) => `
            <tr>
                <td>${echapper(job.type)}</td>
                <td><span class="fr-badge fr-badge--sm ${badges[job.statut] || ""}">${echapper(job.statut)}</span></td>
                <td>${new Date(job.date_creation).toLocaleString("fr-FR")}</td>
                <td>${echapper(job.message_erreur || "")}</td>
                <td>
                    ${["en_attente", "en_cours"].includes(job.statut) ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-close-line" onclick="Suivi.annuler(${job.id})">Annuler</button>` : ""}
                    ${job.statut === "termine" && job.chemin_resultat ? `<a class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-download-line" href="/orchestrateur/jobs/${job.id}/telecharger">Télécharger</a>` : ""}
                </td>
            </tr>`).join("") || `<tr><td colspan="5">Aucun traitement pour l'instant.</td></tr>`;
    },

    async annuler(idJob) {
        await appelJson("/api/rpc/annuler_job", { method: "POST", body: JSON.stringify({ _id_job: idJob }) });
        Suivi.rafraichir();
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
