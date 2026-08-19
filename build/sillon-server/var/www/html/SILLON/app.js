// SILLON - Front-end applicatif
// Vanilla JS, sans framework ni étape de build (cahier des charges §4.2).
// Organisation en objets par domaine fonctionnel (Auth, Bases, Travaux,
// Import, Scripts, Suivi, Administration), plutôt qu'en composants
// séparés : cohérent avec l'absence de bundler du projet.

const TYPES_COLONNE = ["Texte", "Entier", "Décimal", "Date", "Date/Heure", "Booléen", "JSON"];

// Couleurs illustratives du système de design de l'État, reprises telles
// quelles de l'application PLUME (même auteur) : utilisées comme nuancier
// pour les dégradés de carte (Carto) et les couleurs de séries (Graphiques).
// Pas de bascule de thème pour tout le site comme dans PLUME (--theme-main/
// sun/bg n'existent pas dans SILLON, qui garde son unique --sillon-accent) :
// la palette est un choix local à chacun de ces deux onglets.
const PALETTES_DSFR = {
    marianne:     { main: "#6a6af4", sun: "#000091", bg: "#f5f5fe" },
    rouge:        { main: "#e1000f", sun: "#c9191e", bg: "#fdf4f4" },
    tuile:        { main: "#ce614a", sun: "#a94645", bg: "#fef4f3" },
    macaron:      { main: "#e18b76", sun: "#8d533e", bg: "#fef4f2" },
    opera:        { main: "#c94668", sun: "#743242", bg: "#fef0f2" },
    terre_battue: { main: "#e4794a", sun: "#755348", bg: "#fee9e5" },
    tournesol:    { main: "#c8aa39", sun: "#716043", bg: "#fef6e3" },
    moutarde:     { main: "#c3992a", sun: "#695228", bg: "#fef5e8" },
    ecume:        { main: "#465f9d", sun: "#2f4077", bg: "#e9edfe" },
    cumulus:      { main: "#417dc4", sun: "#3558a2", bg: "#e6eefe" },
    glycine:      { main: "#a558a0", sun: "#6e445a", bg: "#fee7fc" },
    emeraude:     { main: "#00a95f", sun: "#297254", bg: "#c3fad5" },
    menthe:       { main: "#009081", sun: "#37635f", bg: "#bafaee" },
    archipel:     { main: "#009099", sun: "#006a6f", bg: "#e5fbfd" },
    bourgeon:     { main: "#68a532", sun: "#447049", bg: "#e6feda" },
    tilleul:      { main: "#b7a73f", sun: "#66673d", bg: "#fef7da" },
    cafe_creme:   { main: "#d1b781", sun: "#685c48", bg: "#f7ecce" },
    caramel:      { main: "#c08c65", sun: "#855b48", bg: "#f3e2d9" },
    gris_galet:   { main: "#aea397", sun: "#6a6156", bg: "#f3ede5" },
};

const PALETTE_LABELS_DSFR = {
    marianne: "Bleu France", rouge: "Rouge Marianne", tuile: "Rose Tuile",
    macaron: "Rose Macaron", opera: "Brun Opéra", terre_battue: "Orange Terre Battue",
    tournesol: "Jaune Tournesol", moutarde: "Jaune Moutarde", ecume: "Bleu Écume",
    cumulus: "Bleu Cumulus", glycine: "Violet Glycine", emeraude: "Vert Émeraude",
    menthe: "Vert Menthe", archipel: "Vert Archipel", bourgeon: "Vert Bourgeon",
    tilleul: "Vert Tilleul-Verveine", cafe_creme: "Brun Café Crème",
    caramel: "Brun Caramel", gris_galet: "Beige Gris Galet",
};

// Nuances (déclinaisons de teinte, "refonte du système de couleur" du DSFR)
// pour chacune des 19 teintes ci-dessus, extraites du CSS DSFR vendorisé
// (dsfr-v1.15.2/dist/dsfr.min.css, thème clair) plutôt que retranscrites à
// la main : chaque teinte y est déclinée en 5-6 nuances de la plus claire
// à la plus soutenue (ex. --blue-france-975-75, ..., --blue-france-main-525,
// --blue-france-sun-113-625 pour le Bleu France uniquement, seule teinte à
// avoir cette nuance supplémentaire). Utilisées par le nuancier à 2 niveaux
// (teinte puis nuance) du dégradé personnalisé de l'onglet Carto.
const NUANCES_DSFR = {
    marianne: [{ code: "975-75", hex: "#f5f5fe" }, { code: "950-100", hex: "#ececfe" }, { code: "925-125", hex: "#e3e3fd" }, { code: "850-200", hex: "#cacafb" }, { code: "main-525", hex: "#6a6af4" }, { code: "sun-113-625", hex: "#000091" }],
    rouge: [{ code: "975-75", hex: "#fef4f4" }, { code: "950-100", hex: "#fee9e9" }, { code: "925-125", hex: "#fddede" }, { code: "850-200", hex: "#fcbfbf" }, { code: "main-472", hex: "#e1000f" }],
    tuile: [{ code: "975-75", hex: "#fef4f3" }, { code: "950-100", hex: "#fee9e7" }, { code: "925-125", hex: "#fddfdb" }, { code: "850-200", hex: "#fcbfb7" }, { code: "main-556", hex: "#ce614a" }],
    macaron: [{ code: "975-75", hex: "#fef4f2" }, { code: "950-100", hex: "#fee9e6" }, { code: "925-125", hex: "#fddfda" }, { code: "850-200", hex: "#fcc0b4" }, { code: "main-689", hex: "#e18b76" }],
    opera: [{ code: "975-75", hex: "#fbf5f2" }, { code: "950-100", hex: "#f7ece4" }, { code: "925-125", hex: "#f3e2d7" }, { code: "850-200", hex: "#eac7ad" }, { code: "main-680", hex: "#bd987a" }],
    terre_battue: [{ code: "975-75", hex: "#fef4f2" }, { code: "950-100", hex: "#fee9e5" }, { code: "925-125", hex: "#fddfd8" }, { code: "850-200", hex: "#fcc0b0" }, { code: "main-645", hex: "#e4794a" }],
    tournesol: [{ code: "975-75", hex: "#fef6e3" }, { code: "950-100", hex: "#feecc2" }, { code: "925-125", hex: "#fde39c" }, { code: "850-200", hex: "#efcb3a" }, { code: "main-731", hex: "#c8aa39" }],
    moutarde: [{ code: "975-75", hex: "#fef5e8" }, { code: "950-100", hex: "#feebd0" }, { code: "925-125", hex: "#fde2b5" }, { code: "850-200", hex: "#fcc63a" }, { code: "main-679", hex: "#c3992a" }],
    ecume: [{ code: "975-75", hex: "#f4f6fe" }, { code: "950-100", hex: "#e9edfe" }, { code: "925-125", hex: "#dee5fd" }, { code: "850-200", hex: "#bfccfb" }, { code: "main-400", hex: "#465f9d" }],
    cumulus: [{ code: "975-75", hex: "#f3f6fe" }, { code: "950-100", hex: "#e6eefe" }, { code: "925-125", hex: "#dae6fd" }, { code: "850-200", hex: "#b6cffb" }, { code: "main-526", hex: "#417dc4" }],
    glycine: [{ code: "975-75", hex: "#fef3fd" }, { code: "950-100", hex: "#fee7fc" }, { code: "925-125", hex: "#fddbfa" }, { code: "850-200", hex: "#fbb8f6" }, { code: "main-494", hex: "#a558a0" }],
    emeraude: [{ code: "975-75", hex: "#e3fdeb" }, { code: "950-100", hex: "#c3fad5" }, { code: "925-125", hex: "#9ef9be" }, { code: "850-200", hex: "#6fe49d" }, { code: "main-632", hex: "#00a95f" }],
    menthe: [{ code: "975-75", hex: "#dffdf7" }, { code: "950-100", hex: "#bafaee" }, { code: "925-125", hex: "#8bf8e7" }, { code: "850-200", hex: "#73e0cf" }, { code: "main-548", hex: "#009081" }],
    archipel: [{ code: "975-75", hex: "#e5fbfd" }, { code: "950-100", hex: "#c7f6fc" }, { code: "925-125", hex: "#a6f2fa" }, { code: "850-200", hex: "#60e0eb" }, { code: "main-557", hex: "#009099" }],
    bourgeon: [{ code: "975-75", hex: "#e6feda" }, { code: "950-100", hex: "#c9fcac" }, { code: "925-125", hex: "#a9fb68" }, { code: "850-200", hex: "#95e257" }, { code: "main-640", hex: "#68a532" }],
    tilleul: [{ code: "975-75", hex: "#fef7da" }, { code: "950-100", hex: "#fceeac" }, { code: "925-125", hex: "#fbe769" }, { code: "850-200", hex: "#e2cf58" }, { code: "main-707", hex: "#b7a73f" }],
    cafe_creme: [{ code: "975-75", hex: "#fbf6ed" }, { code: "950-100", hex: "#f7ecdb" }, { code: "925-125", hex: "#f4e3c7" }, { code: "850-200", hex: "#e7ca8e" }, { code: "main-782", hex: "#d1b781" }],
    caramel: [{ code: "975-75", hex: "#fbf5f2" }, { code: "950-100", hex: "#f7ebe5" }, { code: "925-125", hex: "#f3e2d9" }, { code: "850-200", hex: "#eac7b2" }, { code: "main-648", hex: "#c08c65" }],
    gris_galet: [{ code: "975-75", hex: "#f9f6f2" }, { code: "950-100", hex: "#f3ede5" }, { code: "925-125", hex: "#eee4d9" }, { code: "850-200", hex: "#e0cab0" }, { code: "main-702", hex: "#aea397" }],
};

const NUANCE_LABELS_DSFR = {
    "975-75": "très clair", "950-100": "clair", "925-125": "clair moyen", "850-200": "moyen",
};

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

// Indicateur de chargement générique (spinner + message), pour toute action
// asynchrone dont la durée réelle n'est pas bornée (traitement serveur,
// import, requête longue...) - sans lui, un texte statique ("... en
// cours") reste affiché sans évolution visible, indiscernable d'un
// blocage sur un traitement de plusieurs minutes (constaté en pratique,
// import data.gouv.fr d'un gros fichier réel). Même motif que
// Carto.actualiserApercu(), généralisé ici pour être réutilisé partout où
// une action serveur peut prendre du temps.
function afficherChargement(conteneur, message) {
    conteneur.innerHTML = `
        <div class="sillon-chargement" role="status" aria-live="polite">
            <span class="sillon-spinner" aria-hidden="true"></span>
            <p>${echapper(message)}</p>
        </div>`;
}

// Désactive un bouton pour la durée d'une action asynchrone, avec un
// spinner compact affiché dans le bouton lui-même plutôt que dans un
// conteneur de résultat séparé - pour les actions qui n'ont pas de zone de
// résultat dédiée à remplacer (export, enregistrement...) sans recouvrir
// un résultat déjà affiché à l'écran. Retourne une fonction à appeler dans
// un "finally" pour restaurer le bouton.
function verrouillerBouton(bouton, texteChargement) {
    const contenuOriginal = bouton.innerHTML;
    bouton.disabled = true;
    if (texteChargement) {
        bouton.innerHTML = `<span class="sillon-spinner sillon-spinner--bouton" aria-hidden="true"></span>${echapper(texteChargement)}`;
    }
    return () => {
        bouton.disabled = false;
        bouton.innerHTML = contenuOriginal;
    };
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

// Notification transitoire (Carto/Graphiques/Diagrammes) : pour un feedback
// ponctuel (export terminé, sélection incomplète) sans conteneur de
// résultat associé où écrire une fr-alert classique. type: "success" |
// "error" | "info" | "warning" (classes fr-alert--* du DSFR).
function afficherToast(titre, message, type = "info") {
    let conteneur = document.getElementById("toast-container");
    if (!conteneur) {
        conteneur = document.createElement("div");
        conteneur.id = "toast-container";
        document.body.appendChild(conteneur);
    }
    const toast = document.createElement("div");
    toast.className = `fr-alert fr-alert--${type} fr-alert--sm sillon-toast`;
    toast.innerHTML = `<h3 class="fr-alert__title">${echapper(titre)}</h3><p>${echapper(message)}</p>`;
    conteneur.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("sillon-toast-sortie");
        setTimeout(() => toast.remove(), 300);
    }, 4500);
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
        Suivi.arreterAutoRafraichissement();
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
        // Titre de page RGAA (§9.1) : "Bases" est déjà l'onglet sélectionné
        // par défaut dans le HTML statique (fr-tabs__panel--selected), mais
        // basculerOnglet() - seul autre endroit qui met à jour le H1 - n'est
        // jamais appelée pour cette sélection initiale.
        document.getElementById("titre-onglet").textContent =
            document.querySelector('.fr-tabs__tab[data-onglet="bases"]').textContent.trim();
        document.getElementById("libelle-utilisateur").textContent = `${Etat.utilisateur.email} (${Etat.utilisateur.profil})`;
        document.getElementById("onglet-nav-administration").hidden = Etat.utilisateur.profil !== "administrateur";
        // Section "Formation" de la modale "À propos" (guide + corrigés) :
        // uniquement pour le compte de démonstration du paquet optionnel
        // sillon-tutoriel - ces liens 404 si ce paquet n'est pas installé,
        // jamais montrés à un compte réel dans ce cas.
        const estCompteDemo = Etat.utilisateur.email === "demo@sillon.local";
        document.getElementById("modal-about-formation").hidden = !estCompteDemo;

        // sillon-demo-sirene est un paquet séparé, optionnel : peut être
        // absent même avec le compte demo présent (sillon-tutoriel seul
        // suffit à créer ce compte) - un simple test d'existence du
        // fichier plutôt qu'un lien systématiquement affiché, qui 404rait
        // sinon pour quiconque n'a installé que sillon-tutoriel.
        if (estCompteDemo) {
            fetch("./Documentation/corriges-sirene.zip", { method: "HEAD" })
                .then((reponse) => { document.getElementById("modal-about-sirene").hidden = !reponse.ok; })
                .catch(() => {});
        }

        Bases.charger();
        Suivi.rafraichir();
    },
};

// =============================================================================
// NAVIGATION ENTRE ONGLETS
// =============================================================================
function basculerOnglet(nomOnglet) {
    // Titre de page RGAA (§9.1, index.html #titre-onglet) : le libellé du
    // bouton d'onglet actif sert aussi de contenu au H1 unique de la page,
    // plutôt qu'un texte dupliqué en dur ici.
    document.getElementById("titre-onglet").textContent =
        document.querySelector(`.fr-tabs__tab[data-onglet="${nomOnglet}"]`)?.textContent.trim() || "";
    document.querySelectorAll(".fr-tabs__tab").forEach((bouton) => {
        const actif = bouton.dataset.onglet === nomOnglet;
        bouton.setAttribute("aria-selected", actif ? "true" : "false");
    });
    document.querySelectorAll(".fr-tabs__panel").forEach((panneau) => {
        const actif = panneau.id === `panneau-${nomOnglet}`;
        panneau.hidden = !actif;
        panneau.classList.toggle("fr-tabs__panel--selected", actif);
    });
    if (nomOnglet === "suivi") {
        Suivi.rafraichir();
        Suivi.demarrerAutoRafraichissement();
    } else {
        Suivi.arreterAutoRafraichissement();
    }
    if (nomOnglet === "administration") Administration.charger();
    if (nomOnglet === "carto") Carto.init();
    if (nomOnglet === "graphiques") Graphiques.init();
    if (nomOnglet === "diagrammes") Diagrammes.init();
    if (nomOnglet === "representations") Representations.init();
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
// natif). "showModal()" est utilisé plutôt que "show()" (RGAA) : seule
// showModal() piège le focus clavier à l'intérieur de la modale et rend le
// reste de la page inerte pour les technologies d'assistance.
const Modales = {
    // showModal() plutôt que show() (RGAA) : seule showModal() piège le
    // focus clavier à l'intérieur de la modale et rend le reste de la page
    // inerte pour les technologies d'assistance - show() laissait la
    // tabulation atteindre le contenu masqué derrière, constaté en
    // pratique. Le déclencheur est mémorisé pour restituer le focus à sa
    // fermeture, plutôt que de le laisser perdu sur <body>.
    ouvrir(modale, declencheur) {
        modale._declencheur = declencheur || document.activeElement;
        modale.showModal();
        modale.classList.add("fr-modal--opened");
    },
    fermer(modale) {
        modale.classList.remove("fr-modal--opened");
        modale.close();
        modale._declencheur?.focus();
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

// Modale de consentement (§9/§10) : ouverte au moment de chaque mise en
// file d'attente déclenchée par un clic explicite de l'utilisateur (import
// volumineux, requête/script asynchrone, suppression de base), jamais pour
// la création de base personnelle (invisible, déclenchée en arrière-plan).
// demander() renvoie une promesse résolue par repondre() ; l'évènement
// natif "close" du <dialog> (déclenché par Modales.fermer() quel que soit
// le chemin - bouton Oui/Non, croix, clic hors-modale, Échap) sert de
// filet pour toujours résoudre la promesse, même sur un abandon sans
// réponse explicite (§ défaut prudent : pas de notification).
const ModaleNotification = {
    _resolve: null,
    _reponse: null,
    demander() {
        const modale = document.getElementById("modal-notification-mail");
        document.getElementById("modal-notification-mail-adresse").textContent = Etat.utilisateur?.email || "";
        document.getElementById("modal-notification-piece-jointe").checked = false;
        return new Promise((resolve) => {
            ModaleNotification._resolve = resolve;
            ModaleNotification._reponse = null;
            Modales.ouvrir(modale);
        });
    },
    repondre(notifier) {
        ModaleNotification._reponse = {
            notifier,
            pieceJointe: notifier && document.getElementById("modal-notification-piece-jointe").checked,
        };
        Modales.fermer(document.getElementById("modal-notification-mail"));
    },
    init() {
        document.getElementById("modal-notification-mail").addEventListener("close", () => {
            if (!ModaleNotification._resolve) return;
            ModaleNotification._resolve(ModaleNotification._reponse || { notifier: false, pieceJointe: false });
            ModaleNotification._resolve = null;
        });
    },
};

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".fr-tabs__tab").forEach((bouton) => {
        bouton.addEventListener("click", () => basculerOnglet(bouton.dataset.onglet));
    });
    Modales.init();
    ModaleNotification.init();
    Import.initGlisserDeposer();
    Auth.chargerSession();
    mermaid.initialize({
        startOnLoad: false,
        theme: "base",
        themeVariables: {
            primaryColor: PALETTES_DSFR.marianne.bg,
            primaryTextColor: "#161616",
            primaryBorderColor: PALETTES_DSFR.marianne.main,
            lineColor: PALETTES_DSFR.marianne.sun,
        },
    });
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

        // Base personnelle active par défaut si elle existe déjà (§4.4) :
        // seulement tant qu'aucune sélection n'a encore été faite dans
        // cette session, pour ne jamais écraser un choix délibéré (par
        // exemple une base partagée) au fil des rafraîchissements.
        if (!Etat.baseSelectionnee) {
            const basePersonnelle = Etat.bases.find((b) => b.je_suis_proprietaire);
            if (basePersonnelle) Bases.selectionner(basePersonnelle.id);
        }
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
        // Colonne "Propriétaire" entièrement omise (pas seulement vidée)
        // quand elle ne s'applique pas ("Mes bases" : toujours l'utilisateur
        // lui-même) : un <th> vide est un obstacle RGAA (§5.6/§5.7) pour la
        // navigation par tableau des technologies d'assistance, constaté
        // par un audit accessibilité.
        const colonnes = proprietaire ? 4 : 5;
        const lignes = bases.map((b) => `
            <tr>
                <td>${echapper(b.nom_pg)}</td>
                ${proprietaire ? "" : `<td>${echapper(b.proprietaire_email)}</td>`}
                <td>${Number(b.taille_estimee_mo || 0).toFixed(1)} Mo</td>
                <td>${Bases.badgeAcces(b, proprietaire)}</td>
                <td>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-checkbox-circle-line bouton-selectionner" data-id="${b.id}">Sélectionner</button>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-table-line bouton-tables" data-id="${b.id}">Tables</button>
                    ${proprietaire ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-share-line bouton-partager" data-id="${b.id}">Partager</button>` : ""}
                    ${proprietaire ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-delete-bin-line" onclick="Bases.supprimerBase(this, ${b.id}, '${b.nom_pg}')">Supprimer la base</button>` : ""}
                </td>
            </tr>
            <tr class="ligne-tables" id="tables-${b.id}" hidden><td colspan="${colonnes}"></td></tr>
            ${proprietaire ? `<tr class="ligne-partage" id="partage-${b.id}" hidden><td colspan="${colonnes}"></td></tr>` : ""}
        `).join("");

        return `
            <table class="fr-table"><caption class="fr-sr-only">Bases</caption>
                <thead><tr><th>Base</th>${proprietaire ? "" : "<th>Propriétaire</th>"}<th>Taille</th><th>Accès</th><th>Actions</th></tr></thead>
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
        // Boutons/champs de ce bloc désactivés pour la durée de l'appel
        // (§5.2) : sur succès, afficherPartage() régénère entièrement ce
        // contenu (donc les réactive de fait) ; sur échec, restaurés
        // explicitement ci-dessous.
        const cellule = document.getElementById(`partage-${idBase}`).querySelector("td");
        const elements = cellule.querySelectorAll("button, input");
        elements.forEach((el) => { el.disabled = true; });
        try {
            await appelJson(`/orchestrateur/bases/${idBase}/partager`, {
                method: "POST",
                body: JSON.stringify({ email, autorise_scripts: autoriseScripts }),
            });
            await Bases.afficherPartage(idBase);
            await Bases.afficherPartage(idBase);
        } catch (erreur) {
            elements.forEach((el) => { el.disabled = false; });
            alert(erreur.message);
        }
    },

    async revoquer(idBase, email) {
        const cellule = document.getElementById(`partage-${idBase}`).querySelector("td");
        const elements = cellule.querySelectorAll("button, input");
        elements.forEach((el) => { el.disabled = true; });
        try {
            await appelJson(`/orchestrateur/bases/${idBase}/revoquer`, {
                method: "POST",
                body: JSON.stringify({ email }),
            });
            await Bases.afficherPartage(idBase);
            await Bases.afficherPartage(idBase);
        } catch (erreur) {
            elements.forEach((el) => { el.disabled = false; });
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
            bouton.addEventListener("click", () => Bases.supprimerTable(bouton, idBase, t.nom_table, t.nb_lignes));
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
                    ${fiche.a_documentation
                        ? ` — <a href="/orchestrateur/bases/${idBase}/tables/${encodeURIComponent(nomTable)}/documentation" target="_blank" rel="noopener">Voir la documentation (PDF)</a>`
                        : ""}
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

    async supprimerTable(bouton, idBase, nomTable, nbLignes) {
        if (!confirm(`Supprimer la table « ${nomTable} » et ses ${nbLignes} ligne(s) ? Cette action est irréversible.`)) return;
        const restaurer = verrouillerBouton(bouton);
        try {
            await appelJson(`/orchestrateur/bases/${idBase}/tables/${encodeURIComponent(nomTable)}`, { method: "DELETE" });
            await Bases.afficherTables(idBase);
            await Bases.afficherTables(idBase);
        } catch (erreur) {
            restaurer();
            alert(erreur.message);
        }
    },

    // Suppression d'une base entière (§5.2) : confirmation renforcée par
    // saisie du nom exact, en plus de la vérification de propriété faite
    // côté serveur - la suppression physique est différée en job (§9),
    // suivie comme les autres traitements dans l'onglet Suivi.
    async supprimerBase(bouton, idBase, nomBase) {
        const saisie = prompt(`Action irréversible. Pour confirmer la suppression de la base, saisissez son nom exact :\n${nomBase}`);
        if (saisie === null) return;
        if (saisie !== nomBase) return alert("Nom incorrect, suppression annulée.");
        const { notifier, pieceJointe } = await ModaleNotification.demander();

        const restaurer = verrouillerBouton(bouton);
        try {
            const resultat = await appelJson(`/orchestrateur/bases/${idBase}/supprimer`, {
                method: "POST",
                body: JSON.stringify({ notifier_par_mail: notifier, joindre_piece_jointe: pieceJointe }),
            });
            if (Etat.baseSelectionnee && Etat.baseSelectionnee.id === idBase) {
                Etat.baseSelectionnee = null;
                document.getElementById("rappel-base-selectionnee").querySelector("p").textContent =
                    "Aucune base sélectionnée. Choisissez une base ci-dessous pour l'utiliser dans les onglets Travaux et Scripts.";
                document.getElementById("travaux-base-active").textContent = "";
            }
            alert(`Suppression de la base en cours (job n°${resultat.id_job}), suivez sa progression dans l'onglet Suivi.`);
            await Bases.charger();
        } catch (erreur) {
            restaurer();
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
    // Dernier résultat de lecture (colonnes/lignes), pour réutilisation par
    // les onglets Carto et Graphiques sans réexécuter la requête.
    _dernierResultat: null,

    // CodeMirror.fromTextArea masque le <textarea> d'origine et le
    // synchronise automatiquement (utile si un jour un <form> le soumet
    // directement) - toute lecture/écriture de la requête doit passer par
    // Travaux.editeur, plus par document.getElementById("champ-sql").
    initEditeur() {
        Travaux.editeur = CodeMirror.fromTextArea(document.getElementById("champ-sql"), {
            mode: "text/x-sql",
            lineNumbers: true,
            lineWrapping: true,
            // Pas "autocomplete" (générique) : sql-hint ne propose les
            // colonnes que via la notation pointée ("table.") sans
            // "defaultTable" (cf. sa logique interne, options.defaultTable
            // vide sinon) - le cas le plus courant, taper un nom de colonne
            // seul après FROM, ne suggérait donc jamais aucune colonne
            // (§5.3, constaté en pratique). "defaultTable" est recalculé à
            // chaque déclenchement plutôt que figé à l'ouverture de
            // l'éditeur, pour suivre la table couramment éditée.
            extraKeys: {
                "Ctrl-Space": (cm) => CodeMirror.showHint(cm, CodeMirror.hint.sql, {
                    tables: cm.options.hintOptions.tables,
                    defaultTable: Travaux._tableCourante(cm),
                }),
            },
            hintOptions: { tables: {} },
        });
        // CodeMirror crée son propre <textarea> de capture clavier (masqué
        // par positionnement, pas par "hidden"/display:none - donc toujours
        // exposé aux technologies d'assistance) sans nom accessible : sans
        // ceci, un lecteur d'écran l'annonce comme un champ de formulaire
        // vide et sans étiquette, constaté par un audit accessibilité.
        Travaux.editeur.getInputField().setAttribute("aria-label", "Requête SQL");
    },

    // Première table citée dans une clause FROM/JOIN avant le curseur :
    // meilleure estimation simple de "la table qu'on est en train
    // d'éditer" pour une requête mono-table (cas dominant de l'éditeur
    // libre, §5.3) - une requête à plusieurs tables reste couverte par la
    // notation pointée classique ("table.colonne").
    _tableCourante(cm) {
        const texte = cm.getRange({ line: 0, ch: 0 }, cm.getCursor());
        const correspondance = texte.match(/\b(?:from|join)\s+"?([a-zA-Z_][\w]*)"?/gi);
        if (!correspondance) return undefined;
        const derniere = correspondance[correspondance.length - 1].match(/"?([a-zA-Z_][\w]*)"?$/);
        return derniere ? derniere[1] : undefined;
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

        // Désactivé + spinner (§11) : une requête synchrone peut tourner
        // jusqu'à duree_max_job_minutes (30 min par défaut) sans aucun
        // évènement intermédiaire possible côté serveur (contrairement à
        // l'import data.gouv.fr, pas de flux NDJSON ici) - le texte statique
        // précédent restait figé tout ce temps, indiscernable d'un blocage.
        const bouton = document.getElementById("travaux-bouton-executer");
        bouton.disabled = true;
        afficherChargement(conteneur, "Exécution de la requête en cours…");
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
        } finally {
            bouton.disabled = false;
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
        const { notifier, pieceJointe } = await ModaleNotification.demander();
        afficherChargement(conteneur, "Mise en file d'attente…");
        try {
            const resultat = await appelJson("/orchestrateur/sql/job", {
                method: "POST",
                body: JSON.stringify({
                    base_id: Etat.baseSelectionnee.id, requete,
                    notifier_par_mail: notifier, joindre_piece_jointe: pieceJointe,
                }),
            });
            const suffixeMail = notifier ? ", vous serez notifié par mail à la fin" : "";
            conteneur.innerHTML = `<div class="fr-alert fr-alert--info fr-alert--sm">Requête mise en file d'attente (job n°${resultat.id_job}) : suivez sa progression dans l'onglet Suivi${suffixeMail}.</div>`;
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
        Travaux._dernierResultat = resultat;
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
        // Spinner dans le bouton lui-même, pas dans resultat-travaux (§5.3) :
        // cette action ne doit jamais recouvrir un résultat de requête déjà
        // affiché à l'écran, contrairement à Exécuter.
        const restaurer = verrouillerBouton(document.getElementById("travaux-bouton-exporter"), "Export en cours…");
        try {
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
        } finally {
            restaurer();
        }
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
        const restaurer = verrouillerBouton(document.getElementById("travaux-bouton-enregistrer"));
        try {
            await appelJson("/api/rpc/enregistrer_requete", {
                method: "POST",
                body: JSON.stringify({ _nom: nom, _requete: requete }),
            });
            await Travaux.rafraichirRequetesEnregistrees();
        } catch (erreur) {
            alert(erreur.message);
        } finally {
            restaurer();
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
    // Mémorisé après le premier appel plutôt que refait à chaque import
    // (§9/§10, prédiction sync/async côté client) : ce réglage n'est
    // modifiable que par un administrateur, une valeur légèrement
    // obsolète pendant la session en cours est sans conséquence réelle
    // (au pire, la modale est proposée ou non à tort une fois).
    _seuilSynchroneOctetsCache: null,
    async _seuilSynchroneOctets() {
        if (Import._seuilSynchroneOctetsCache === null) {
            const parametres = await appelJson("/api/parametres?cle=eq.seuil_import_synchrone_mo").catch(() => []);
            Import._seuilSynchroneOctetsCache = Number(parametres[0]?.valeur || 10) * 1024 * 1024;
        }
        return Import._seuilSynchroneOctetsCache;
    },

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
        const bouton = document.getElementById("import-bouton-confirmer");
        const apercu = Etat.dernierApercu;
        if (!apercu) return;

        // Désactivé ici (pas seulement dans executerImport) : sans ça, un
        // double-clic pendant cette phase de contrôle de cohérence déclenche
        // deux vérifications concurrentes - le bouton reste visible tout du
        // long, contrairement aux boutons dynamiques d'exclusion/remplacement
        // ci-dessous, remplacés avec le contenu de resultat-import dès le
        // premier appel (protection déjà assurée par ce remplacement).
        // Réactivé soit ici (anomalie détectée ou erreur, écran encore à ce
        // stade), soit dans executerImport (chemin normal, qui prend le relai).
        bouton.disabled = true;
        afficherChargement(conteneur, "Contrôle de cohérence en cours…");
        let verification;
        try {
            verification = await appelJson("/orchestrateur/import/verifier", {
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
        } catch (erreur) {
            bouton.disabled = false;
            return afficherErreur(conteneur, erreur);
        }
        if (verification.nb_lignes_anomalies > 0) {
            bouton.disabled = false;
            Import.afficherAnomalies(verification);
            return;
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
        const bouton = document.getElementById("import-bouton-confirmer");
        const apercu = Etat.dernierApercu;
        const baseId = document.getElementById("import-base-cible").value || null;

        // La modale de consentement (§9/§10) n'a de sens que si ce fichier
        // va effectivement partir en file d'attente : "taille_octets"
        // (fichier normalisé, cf. _analyser_fichier_stage) est comparé au
        // même seuil que celui utilisé côté serveur par valider_import()
        // pour cette décision (seuil_import_synchrone_mo) - un import qui
        // se termine en quelques secondes n'a pas à interrompre
        // l'utilisateur pour une notification qui ne partira jamais.
        let notifier = true;
        let pieceJointe = false;
        if (apercu?.taille_octets > (await Import._seuilSynchroneOctets())) {
            ({ notifier, pieceJointe } = await ModaleNotification.demander());
        }

        // Bouton principal désactivé ici aussi (pas seulement dans valider())
        // : cette fonction est également atteinte depuis les boutons
        // d'exclusion/remplacement, dynamiquement recréés à chaque appel -
        // seul "Confirmer l'import" reste un élément DOM stable tout du long,
        // donc le seul à nécessiter une désactivation explicite (§ commentaire
        // de valider() ci-dessus). Réactivé dans le "finally" : c'est le
        // dernier maillon de toutes les chaînes d'appel (valider,
        // confirmerExclusion, confirmerRemplacement).
        bouton.disabled = true;
        afficherChargement(conteneur, "Import en cours…");
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
                    nom_fichier: apercu.nom_fichier,
                    base_id: baseId ? Number(baseId) : null,
                    nom_table: document.getElementById("import-nom-table").value.trim(),
                    colonnes: Import.colonnesSaisies(),
                    encodage: apercu.encodage_detecte,
                    delimiteur: apercu.delimiteur_detecte,
                    valeur_manquante: document.getElementById("import-valeur-manquante").value,
                    avec_entete: apercu.avec_entete,
                    remplacer,
                    exclure_lignes: exclureLignes,
                    notifier_par_mail: notifier,
                    joindre_piece_jointe: pieceJointe,
                    ...(apercu.nom_documentation ? { nom_documentation: apercu.nom_documentation } : {}),
                }),
            });
            const resultat = await reponse.json().catch(() => ({}));

            if (reponse.status === 409 && resultat.statut === "collision") {
                Import.afficherCollision(resultat.table, exclureLignes);
                return;
            }
            if (!reponse.ok) throw new Error(resultat.erreur || `Erreur HTTP ${reponse.status}`);

            const suffixeExclusion = exclureLignes.length ? ` (${exclureLignes.length} ligne(s) exclue(s))` : "";
            const suffixeMail = notifier ? ", vous serez notifié par mail à la fin" : "";
            conteneur.innerHTML = resultat.statut === "termine"
                ? `<div class="fr-alert fr-alert--success fr-alert--sm">Table « ${echapper(resultat.table)} » créée avec succès${suffixeExclusion}.</div>`
                : `<div class="fr-alert fr-alert--info fr-alert--sm">Fichier volumineux : import mis en file d'attente (job n°${resultat.id_job}), suivez sa progression dans l'onglet Suivi${suffixeMail}.</div>`;
            document.getElementById("assistant-import").hidden = true;
            await Bases.charger();
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        } finally {
            bouton.disabled = false;
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
// IMPORT DEPUIS DATA.GOUV.FR (§5.1) - modale ouverte depuis l'onglet Import
// =============================================================================
// N'importe jamais directement : /import/datagouv/apercu prépare le fichier
// dans STAGING_DIR exactement comme /import/apercu (upload manuel), puis
// délègue à Import.afficherAssistant - tout le reste (relecture des types,
// contrôle de cohérence, Import.valider) est le pipeline existant, réutilisé
// tel quel, sans aucune modification.
const Datagouv = {
    async rechercher() {
        const motCle = document.getElementById("datagouv-recherche").value.trim();
        const conteneur = document.getElementById("datagouv-resultats");
        conteneur.innerHTML = "Recherche en cours…";
        try {
            const { resultats } = await appelJson(`/orchestrateur/datagouv/recherche?q=${encodeURIComponent(motCle)}`);
            Datagouv.afficherResultats(resultats);
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },

    afficherResultats(datasets) {
        const conteneur = document.getElementById("datagouv-resultats");
        if (datasets.length === 0) {
            conteneur.innerHTML = '<p class="fr-text--sm">Aucun jeu de données trouvé.</p>';
            return;
        }
        // Documentation (§5.1) : facultative et indépendante du choix de la
        // ressource de données - un menu déroulant par jeu de données
        // ("Aucune" par défaut), lu au moment du clic sur "Importer cette
        // ressource" plutôt que lié à une ressource précise, puisqu'un même
        // PDF peut légitimement documenter plusieurs fichiers d'un même jeu
        // (ex. DVF : 5 fichiers de données, 4 PDF de documentation).
        conteneur.innerHTML = datasets.map((jeu, i) => `
            <div class="fr-card fr-card--sm fr-mb-2w">
                <div class="fr-card__body">
                    <div class="fr-card__content">
                        <h3 class="fr-card__title">${echapper(jeu.titre || "(sans titre)")}</h3>
                        <p class="fr-card__desc fr-text--sm">
                            ${jeu.organisation ? `<strong>${echapper(jeu.organisation)}</strong> — ` : ""}
                            ${echapper(jeu.description || "")}
                        </p>
                        ${jeu.ressources_donnees.length === 0
                            ? '<p class="fr-text--sm fr-text--disabled">Aucun fichier de données exploitable (CSV/TXT/JSON/ZIP) pour ce jeu de données.</p>'
                            : `<ul class="fr-text--sm">${jeu.ressources_donnees.map((r, j) => `
                                <li class="fr-mb-1w">
                                    ${echapper(r.titre || "ressource")}
                                    ${r.taille ? ` (${Datagouv.formaterTaille(r.taille)})` : " (taille inconnue)"}
                                    <button class="fr-btn fr-btn--sm fr-btn--tertiary fr-ml-1w" onclick="Datagouv.importerRessource(${i}, ${j})">Importer cette ressource</button>
                                </li>`).join("")}</ul>`}
                        ${jeu.ressources_documentation.length > 0 ? `
                            <label class="fr-label fr-text--sm" for="datagouv-doc-${i}">
                                Documentation à joindre (facultatif)
                            </label>
                            <select class="fr-select" id="datagouv-doc-${i}">
                                <option value="-1" selected>Aucune</option>
                                ${jeu.ressources_documentation.map((r, j) => `
                                    <option value="${j}">${echapper(r.titre || "documentation.pdf")}</option>`).join("")}
                            </select>` : ""}
                    </div>
                </div>
            </div>`).join("");
        Etat.derniersResultatsDatagouv = datasets;
    },

    formaterTaille(octets) {
        if (octets >= 1024 * 1024 * 1024) return `${(octets / (1024 * 1024 * 1024)).toFixed(1)} Go`;
        if (octets >= 1024 * 1024) return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
        return `${Math.round(octets / 1024)} Ko`;
    },

    async importerRessource(indexJeu, indexRessource) {
        const jeu = Etat.derniersResultatsDatagouv[indexJeu];
        const ressource = jeu.ressources_donnees[indexRessource];
        const conteneur = document.getElementById("datagouv-resultats");

        const selecteurDoc = document.getElementById(`datagouv-doc-${indexJeu}`);
        const indexDoc = selecteurDoc ? Number(selecteurDoc.value) : -1;
        const documentation = indexDoc >= 0 ? jeu.ressources_documentation[indexDoc] : null;

        afficherChargement(conteneur, "Téléchargement de la ressource en cours…");
        try {
            const reponse = await appel("/orchestrateur/import/datagouv/apercu", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url_ressource: ressource.url,
                    nom_fichier: ressource.titre || "ressource.csv",
                    ...(documentation ? { url_documentation: documentation.url } : {}),
                }),
            });
            if (!reponse.ok) {
                // Erreur renvoyée avant l'entrée dans le flux (ex. URL
                // manquante, 400) : corps JSON classique, pas de ligne NDJSON.
                const corps = await reponse.json().catch(() => ({}));
                throw new Error(corps.erreur || `Erreur HTTP ${reponse.status}`);
            }

            // Lecture en flux (NDJSON : une ligne = un évènement JSON) plutôt
            // qu'un .json() unique en fin de requête - affiche la progression
            // du téléchargement au fur et à mesure (volume, vitesse), pas
            // seulement le résultat final une fois terminé.
            const lecteur = reponse.body.getReader();
            const decodeur = new TextDecoder();
            let tampon = "";
            while (true) {
                const { done, value } = await lecteur.read();
                if (done) break;
                tampon += decodeur.decode(value, { stream: true });
                let indexSaut;
                while ((indexSaut = tampon.indexOf("\n")) >= 0) {
                    const ligne = tampon.slice(0, indexSaut);
                    tampon = tampon.slice(indexSaut + 1);
                    if (!ligne.trim()) continue;
                    const evenement = JSON.parse(ligne);

                    if (evenement.type === "progression") {
                        Datagouv.afficherProgression(conteneur, evenement);
                    } else if (evenement.type === "etape") {
                        // Couvre les phases sans progression chiffrée
                        // (extraction ZIP, conversion JSON, analyse - §5.1) :
                        // sans cet évènement, le dernier message de
                        // progression du téléchargement (à 100%) restait
                        // affiché figé pendant potentiellement plusieurs
                        // minutes sur un gros fichier réel (ex. DVF, ~5 min
                        // constaté en pratique), indiscernable d'un blocage.
                        afficherChargement(conteneur, evenement.message);
                    } else if (evenement.type === "erreur") {
                        throw new Error(evenement.message);
                    } else if (evenement.type === "resultat") {
                        const { type, ...apercu } = evenement;
                        // Nom mémorisé ici (pas seulement documentation_disponible,
                        // déjà dans apercu) : /import/valider en a besoin pour
                        // l'attacher à la table lors de sa création.
                        if (apercu.documentation_disponible && documentation) {
                            apercu.nom_documentation = documentation.titre || "documentation.pdf";
                        }
                        Etat.dernierApercu = apercu;
                        Import.afficherAssistant(apercu, apercu.nom_fichier);
                        document.getElementById("resultat-import").innerHTML = "";
                        Modales.fermer(document.getElementById("modal-datagouv"));
                        // Fermer la modale ne réinitialise pas son contenu
                        // (Modales.fermer se contente de la masquer) : sans
                        // ceci, le dernier message affiché ("Analyse du
                        // fichier en cours…") restait visible à la prochaine
                        // ouverture de cette modale, avant toute nouvelle
                        // recherche - constaté en pratique, ressemblant à un
                        // blocage alors que l'import précédent avait bien
                        // abouti.
                        conteneur.innerHTML = "";
                        return;
                    }
                }
            }
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
    },

    afficherProgression(conteneur, { recu_octets, total_octets, vitesse_octets_s }) {
        const recu = Datagouv.formaterTaille(recu_octets);
        const vitesse = `${Datagouv.formaterTaille(vitesse_octets_s)}/s`;
        if (total_octets) {
            const pourcentage = Math.min(100, Math.round((recu_octets / total_octets) * 100));
            conteneur.innerHTML = `
                <p>Téléchargement de la ressource en cours… ${recu} / ${Datagouv.formaterTaille(total_octets)} (${pourcentage} %) — ${vitesse}</p>
                <progress value="${recu_octets}" max="${total_octets}" style="width:100%"></progress>`;
        } else {
            conteneur.innerHTML = `<p>Téléchargement de la ressource en cours… ${recu} — ${vitesse}</p>`;
        }
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

    // Squelette de connexion commun (même contrat d'exécution que le
    // tutoriel, §5.4 : SILLON_DSN/SILLON_RESULTATS) pré-rempli à l'ouverture
    // d'un nouveau script, pour ne jamais partir d'une page blanche sur la
    // partie identique d'un script à l'autre.
    _SQUELETTES: {
        py: `import os
import psycopg2
import pandas as pd

dsn = os.environ["SILLON_DSN"]
resultats = os.environ["SILLON_RESULTATS"]

connexion = psycopg2.connect(dsn)

# ... votre analyse, vos graphiques, vos exports ...

connexion.close()
`,
        R: `library(DBI)
library(RPostgreSQL)

# RPostgreSQL n'accepte pas directement la chaîne de connexion SILLON_DSN
# (format clé=valeur de libpq) : on l'analyse nous-mêmes.
analyser_dsn <- function(dsn) {
  valeurs <- list()
  for (paire in strsplit(trimws(dsn), "\\\\s+")[[1]]) {
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

# ... votre analyse, vos graphiques, vos exports ...

dbDisconnect(connexion)
`,
    },

    // Lit le fichier choisi en local (FileReader, jamais uploadé tel quel)
    // pour permettre de le visualiser et éventuellement le modifier avant
    // l'envoi réel. Sans fichier choisi : même modale, ouverte avec le
    // squelette de connexion Python plutôt qu'une page blanche.
    async ouvrirEditeur() {
        const fichier = document.getElementById("champ-fichier-script").files[0];
        if (!fichier) return Scripts.nouveauScript("py");
        document.getElementById("editeur-script-nom").value = fichier.name;
        document.getElementById("editeur-script-contenu").value = await fichier.text();
        Modales.ouvrir(document.getElementById("modal-editeur-script"));
    },

    nouveauScript(langage) {
        document.getElementById("editeur-script-nom").value = langage === "R" ? "script.R" : "script.py";
        document.getElementById("editeur-script-contenu").value = Scripts._SQUELETTES[langage];
        Modales.ouvrir(document.getElementById("modal-editeur-script"));
    },

    async lancerDepuisEditeur() {
        const conteneur = document.getElementById("resultat-scripts");
        const baseId = document.getElementById("scripts-base-cible").value;
        const nomFichier = document.getElementById("editeur-script-nom").value.trim();
        const contenu = document.getElementById("editeur-script-contenu").value;
        if (!baseId) return afficherErreur(conteneur, new Error("Choisissez une base cible."));
        if (!/\.(py|R)$/i.test(nomFichier)) {
            return afficherErreur(conteneur, new Error("Le nom du fichier doit se terminer par .py ou .R."));
        }

        Modales.fermer(document.getElementById("modal-editeur-script"));
        const { notifier, pieceJointe } = await ModaleNotification.demander();

        // Un Blob construit à partir du contenu (potentiellement modifié)
        // de la modale, jamais le File d'origine : c'est le texte affiché
        // à l'écran qui doit partir, pas le fichier initialement choisi.
        const donnees = new FormData();
        donnees.append("fichier", new Blob([contenu], { type: "text/plain" }), nomFichier);
        donnees.append("base_id", baseId);
        donnees.append("notifier_par_mail", notifier);
        donnees.append("joindre_piece_jointe", pieceJointe);

        afficherChargement(conteneur, "Envoi du script…");
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
    _intervalleAuto: null,
    _jobsCache: [],
    _jobsFiltres: [],
    _page: 0,
    _TAILLE_PAGE: 10,
    // Identifiants des jobs dont le panneau Journal/Aperçus est ouvert :
    // la table est entièrement reconstruite à chaque rafraîchissement
    // (manuel ou automatique toutes les 10s, §5.5) - sans ce suivi, un
    // panneau ouvert se refermerait tout seul au rafraîchissement suivant,
    // constaté en pratique.
    _journalOuverts: new Set(),
    _apercusOuverts: new Set(),

    // Actif uniquement pendant que l'onglet Suivi est affiché (démarré/
    // arrêté depuis basculerOnglet()) : jamais de requête périodique en
    // arrière-plan sur un autre onglet, pour rien.
    demarrerAutoRafraichissement() {
        Suivi.arreterAutoRafraichissement();
        Suivi._intervalleAuto = setInterval(() => Suivi.rafraichir(), 10000);
    },

    arreterAutoRafraichissement() {
        clearInterval(Suivi._intervalleAuto);
        Suivi._intervalleAuto = null;
    },

    // Vue consolidée, tous types confondus (§5.5) : le filtrage par type et
    // par statut se fait côté client sur ce cache plutôt que par un nouvel
    // appel serveur à chaque changement de filtre - la liste complète est
    // déjà rapatriée en un seul appel.
    async rafraichir() {
        // Un rafraîchissement (manuel ou périodique) reconstruit toute la
        // table : un intervalle de journal pointant vers une ligne que ce
        // rendu vient de recréer (hidden par défaut) tournerait pour rien
        // sans jamais s'arrêter de lui-même.
        Object.values(Suivi._intervallesJournal).forEach(clearInterval);
        Suivi._intervallesJournal = {};

        try {
            Suivi._jobsCache = await appelJson("/api/vue_mes_jobs?order=date_creation.desc");
        } catch (erreur) {
            Suivi._jobsCache = [];
        }
        // Page conservée (un rafraîchissement, manuel ou automatique toutes
        // les 10s, ne doit jamais ramener l'utilisateur à la page 1 s'il
        // consultait autre chose) - seul un changement de filtre en repart.
        Suivi.appliquerFiltres(false);
    },

    appliquerFiltres(reinitialiserPage = true) {
        const filtreType = document.getElementById("suivi-filtre-type").value;
        const filtreStatut = document.getElementById("suivi-filtre-statut").value;
        Suivi._jobsFiltres = Suivi._jobsCache.filter((job) =>
            (!filtreType || job.type === filtreType) && (!filtreStatut || job.statut === filtreStatut));
        if (reinitialiserPage) Suivi._page = 0;
        Suivi._afficherPage();
    },

    // Pagination purement cliente (§5.5) : la liste complète tient déjà en
    // mémoire (_jobsCache, un seul appel serveur par rafraîchissement),
    // pas besoin d'aller-retour supplémentaire juste pour changer de page.
    _afficherPage() {
        const nbPages = Math.max(1, Math.ceil(Suivi._jobsFiltres.length / Suivi._TAILLE_PAGE));
        Suivi._page = Math.min(Suivi._page, nbPages - 1);
        const debut = Suivi._page * Suivi._TAILLE_PAGE;
        Suivi._afficher(Suivi._jobsFiltres.slice(debut, debut + Suivi._TAILLE_PAGE));

        // Structure du composant "Pagination" du DSFR (nav + liste), pas de
        // simples boutons juxtaposés (RGAA) : regroupe explicitement les
        // contrôles pour les technologies d'assistance plutôt que de les
        // laisser flotter sans lien entre eux dans la page. <button>
        // plutôt que <a href="#"> : ce n'est jamais une vraie navigation
        // d'URL, seulement un changement d'état côté client.
        const pagination = document.getElementById("suivi-pagination");
        pagination.innerHTML = nbPages <= 1 ? "" : `
            <nav role="navigation" class="fr-pagination" aria-label="Pagination des traitements">
                <ul class="fr-pagination__list">
                    <li>
                        <button class="fr-pagination__link fr-pagination__link--prev fr-pagination__link--lg-label" ${Suivi._page === 0 ? "disabled" : ""} onclick="Suivi.pagePrecedente()">Page précédente</button>
                    </li>
                    <li><span class="fr-text--sm fr-mx-2w">Page ${Suivi._page + 1} / ${nbPages} (${Suivi._jobsFiltres.length} traitement(s))</span></li>
                    <li>
                        <button class="fr-pagination__link fr-pagination__link--next fr-pagination__link--lg-label" ${Suivi._page >= nbPages - 1 ? "disabled" : ""} onclick="Suivi.pageSuivante()">Page suivante</button>
                    </li>
                </ul>
            </nav>`;
    },

    pagePrecedente() {
        Suivi._page = Math.max(0, Suivi._page - 1);
        Suivi._afficherPage();
    },

    pageSuivante() {
        Suivi._page += 1;
        Suivi._afficherPage();
    },

    _LIBELLES_STATUT: {
        en_attente: "En attente", en_cours: "En cours", termine: "Terminé", erreur: "Erreur", annule: "Annulé",
    },

    _afficher(jobs) {
        const badges = { en_attente: "fr-badge--info", en_cours: "fr-badge--info", termine: "fr-badge--success", erreur: "fr-badge--error", annule: "" };
        const estScript = (type) => type === "script_python" || type === "script_r";

        document.getElementById("table-suivi").innerHTML = jobs.map((job) => `
            <tr>
                <td>${echapper(job.type)}</td>
                <td>
                    <span class="fr-badge fr-badge--sm ${badges[job.statut] || ""}">${echapper(Suivi._LIBELLES_STATUT[job.statut] || job.statut)}</span>
                    ${job.statut === "en_attente" && job.position_file != null ? `<br><span class="fr-text--xs">Position dans la file : ${job.position_file + 1}</span>` : ""}
                </td>
                <td>${new Date(job.date_creation).toLocaleString("fr-FR")}</td>
                <td>${Suivi._celluleDetail(job)}</td>
                <td>
                    ${["en_attente", "en_cours"].includes(job.statut) ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-close-line" onclick="Suivi.annuler(this, ${job.id})">Annuler</button>` : ""}
                    ${estScript(job.type) && job.statut !== "annule" ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-file-text-line" onclick="Suivi.afficherJournal(${job.id})">Journal</button>` : ""}
                    ${estScript(job.type) && job.statut === "termine" ? `<button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-image-line" onclick="Suivi.afficherApercus(${job.id})">Aperçus</button>` : ""}
                    ${job.statut === "termine" && job.chemin_resultat ? `<a class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-download-line" href="/orchestrateur/jobs/${job.id}/telecharger">Télécharger</a>` : ""}
                </td>
            </tr>
            ${estScript(job.type) ? `<tr class="ligne-journal" id="journal-${job.id}" hidden><td colspan="5"></td></tr>` : ""}
            ${estScript(job.type) ? `<tr class="ligne-apercu" id="apercu-${job.id}" hidden><td colspan="5"></td></tr>` : ""}`).join("")
            || `<tr><td colspan="5">Aucun traitement pour l'instant.</td></tr>`;

        // Rouvre les panneaux qui l'étaient avant cette reconstruction
        // (cf. commentaire sur _journalOuverts/_apercusOuverts) - la ligne
        // n'existe que si le job concerné apparaît sur la page actuellement
        // affichée, jamais supposée présente sans vérifier.
        for (const idJob of Suivi._journalOuverts) {
            if (document.getElementById(`journal-${idJob}`)) Suivi.afficherJournal(idJob);
        }
        for (const idJob of Suivi._apercusOuverts) {
            if (document.getElementById(`apercu-${idJob}`)) Suivi.afficherApercus(idJob);
        }
    },

    // Message utilisateur reformulé en avant, détail technique replié
    // derrière un <details> natif (§5.5 : les deux doivent coexister, le
    // second "pour investigation" seulement) - jamais un message Postgres
    // brut affiché en première lecture.
    _celluleDetail(job) {
        const nomFichier = job.nom_fichier ? `<span class="fr-text--sm">${echapper(job.nom_fichier)}</span>` : "";
        if (!job.message_erreur && !job.message_utilisateur) return nomFichier;
        const principal = echapper(job.message_utilisateur || job.message_erreur);
        const detail = job.message_utilisateur && job.message_erreur && job.message_erreur !== job.message_utilisateur
            ? `<details class="fr-mt-1w"><summary class="fr-text--xs">Détail technique</summary><code class="fr-text--xs">${echapper(job.message_erreur)}</code></details>`
            : "";
        return `${nomFichier}${nomFichier ? "<br>" : ""}${principal}${detail}`;
    },

    async annuler(bouton, idJob) {
        // Absence de try/catch constatée en pratique (§5.5) : un échec
        // réseau ne se voyait jusqu'ici d'aucune façon.
        const restaurer = verrouillerBouton(bouton);
        try {
            await appelJson("/api/rpc/annuler_job", { method: "POST", body: JSON.stringify({ _id_job: idJob }) });
            await Suivi.rafraichir();
        } catch (erreur) {
            restaurer();
            alert(erreur.message);
        }
    },

    // Journal consultable pendant l'exécution, pas seulement une fois le
    // job terminé (§5.4) : rafraîchi périodiquement tant que le job est
    // en_attente/en_cours, arrêté de lui-même dès qu'il ne l'est plus.
    async afficherJournal(idJob) {
        const ligne = document.getElementById(`journal-${idJob}`);
        ligne.hidden = !ligne.hidden;
        if (ligne.hidden) {
            Suivi._journalOuverts.delete(idJob);
            clearInterval(Suivi._intervallesJournal[idJob]);
            delete Suivi._intervallesJournal[idJob];
            return;
        }
        Suivi._journalOuverts.add(idJob);
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

    // Aperçus des résultats d'un script (diagrammes Mermaid, images,
    // tableaux CSV - cf. orchestrateur.py /jobs/<id>/apercus et
    // /jobs/<id>/apercu/<nom>) : rendu entièrement côté navigateur, sans
    // obliger l'utilisateur à télécharger l'archive complète pour
    // consulter un seul fichier. Les diagrammes Mermaid en particulier ne
    // peuvent pas être rendus par le bac à sable lui-même (§8.7 : pas de
    // Node/Chromium dans sillon-image-execution) - seul le texte .mmd y
    // est produit, rendu ici en SVG.
    async afficherApercus(idJob) {
        const ligne = document.getElementById(`apercu-${idJob}`);
        ligne.hidden = !ligne.hidden;
        if (ligne.hidden) {
            Suivi._apercusOuverts.delete(idJob);
            return;
        }
        Suivi._apercusOuverts.add(idJob);

        const cellule = document.querySelector(`#apercu-${idJob} td`);
        cellule.innerHTML = `<p class="fr-text--sm">Chargement…</p>`;
        try {
            const resultat = await appelJson(`/orchestrateur/jobs/${idJob}/apercus`);
            if (resultat.apercus.length === 0) {
                cellule.innerHTML = `<p class="fr-text--sm">Aucun fichier prévisualisable (diagramme Mermaid, image ou CSV) dans ce résultat.</p>`;
                return;
            }
            cellule.innerHTML = resultat.apercus.map((_, i) =>
                `<p class="fr-text--sm fr-mb-1w"><strong></strong></p><div class="apercu-fichier" id="apercu-contenu-${idJob}-${i}"></div>`).join("");
            for (const [i, apercu] of resultat.apercus.entries()) {
                const conteneur = document.getElementById(`apercu-contenu-${idJob}-${i}`);
                conteneur.previousElementSibling.querySelector("strong").textContent = apercu.nom;
                await Suivi._rendreApercu(idJob, apercu, conteneur, i);
            }
        } catch (erreur) {
            cellule.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message)}</div>`;
        }
    },

    async _rendreApercu(idJob, apercu, conteneur, indice) {
        const url = `/orchestrateur/jobs/${idJob}/apercu/${encodeURIComponent(apercu.nom)}`;
        if (apercu.type === "image") {
            conteneur.innerHTML = `<img src="${url}" alt="${echapper(apercu.nom)}" style="max-width:100%">`;
            return;
        }
        try {
            const reponse = await fetch(url, { credentials: "same-origin" });
            if (!reponse.ok) throw new Error(`Erreur HTTP ${reponse.status}`);
            const texte = await reponse.text();
            if (apercu.type === "mermaid") {
                const { svg } = await mermaid.render(`svg-${idJob}-${indice}`, texte);
                conteneur.innerHTML = svg;
                // Contrairement à l'aperçu de l'onglet Diagrammes (source
                // Mermaid déjà affichée en texte juste à côté), rien
                // d'autre ici ne représente ce diagramme en texte : un
                // aria-label franc (annonce sans prétendre décrire le
                // contenu) plutôt qu'un SVG totalement silencieux pour un
                // lecteur d'écran (RGAA §1), constaté par un audit
                // accessibilité.
                conteneur.querySelector("svg")?.setAttribute("aria-label", `Diagramme Mermaid : ${apercu.nom}`);
            } else if (apercu.type === "csv") {
                conteneur.innerHTML = Suivi._tableauDepuisCSV(texte);
            }
        } catch (erreur) {
            conteneur.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">Aperçu impossible : ${echapper(erreur.message)}</div>`;
        }
    },

    _LIMITE_LIGNES_CSV: 200,

    // Analyseur CSV minimal (virgule, guillemets doublés pour échapper un
    // guillemet - RFC 4180) : suffisant pour les fichiers produits par
    // csv.writer (Python) et write.csv (R), pas un analyseur généraliste.
    _analyserCSV(texte) {
        const lignes = [];
        let ligne = [], champ = "", dansGuillemets = false;
        for (let i = 0; i < texte.length; i++) {
            const c = texte[i];
            if (dansGuillemets) {
                if (c === '"' && texte[i + 1] === '"') { champ += '"'; i++; }
                else if (c === '"') { dansGuillemets = false; }
                else { champ += c; }
            } else if (c === '"') {
                dansGuillemets = true;
            } else if (c === ",") {
                ligne.push(champ); champ = "";
            } else if (c === "\n" || c === "\r") {
                if (c === "\r" && texte[i + 1] === "\n") i++;
                ligne.push(champ); champ = "";
                if (ligne.length > 1 || ligne[0] !== "") lignes.push(ligne);
                ligne = [];
            } else {
                champ += c;
            }
        }
        if (champ !== "" || ligne.length > 0) { ligne.push(champ); lignes.push(ligne); }
        return lignes;
    },

    _tableauDepuisCSV(texte) {
        const lignes = Suivi._analyserCSV(texte);
        if (lignes.length === 0) return `<p class="fr-text--sm">Fichier CSV vide.</p>`;
        const [entetes, ...donnees] = lignes;
        const tronque = donnees.length > Suivi._LIMITE_LIGNES_CSV;
        const affichees = tronque ? donnees.slice(0, Suivi._LIMITE_LIGNES_CSV) : donnees;
        return `
            <div style="max-height:400px; overflow:auto;">
            <table class="fr-table fr-table--sm"><thead><tr>${entetes.map((c) => `<th>${echapper(c)}</th>`).join("")}</tr></thead>
            <tbody>${affichees.map((l) => `<tr>${l.map((v) => `<td>${echapper(v)}</td>`).join("")}</tr>`).join("")}</tbody></table>
            </div>
            ${tronque ? `<p class="fr-text--xs">${donnees.length} lignes au total, aperçu tronqué aux ${Suivi._LIMITE_LIGNES_CSV} premières — téléchargez l'archive pour le fichier complet.</p>` : ""}`;
    },
};

// =============================================================================
// SOURCE DE DONNÉES PARTAGÉE (Carto, Graphiques)
// =============================================================================
// Un fichier CSV déposé localement (analysé avec PapaParse, en-tête
// obligatoire) ou le résultat de la dernière requête de lecture exécutée
// dans l'onglet Travaux (Travaux._dernierResultat) - les deux sont ramenés
// à la même forme {colonnes, lignes} avant d'être transmis à l'onglet
// appelant, qui n'a donc jamais à distinguer les deux origines.
const DonneesVisu = {
    creerSelecteur(idConteneur, callback) {
        const conteneur = document.getElementById(idConteneur);
        if (!conteneur) return;
        const idFichier = `${idConteneur}-fichier`;
        const idBoutonSql = `${idConteneur}-btn-sql`;
        const idStatut = `${idConteneur}-statut`;
        conteneur.innerHTML = `
            <div class="sillon-source-donnees">
                <div class="fr-upload-group" style="flex:1 1 260px; margin-bottom:0;">
                    <label class="fr-label" for="${idFichier}">Déposer un fichier CSV (avec en-tête)</label>
                    <input class="fr-upload" type="file" accept=".csv" id="${idFichier}">
                </div>
                <button class="fr-btn fr-btn--secondary fr-icon-database-line fr-btn--icon-left" id="${idBoutonSql}" type="button">
                    Utiliser le résultat de la dernière requête SQL
                </button>
                <span id="${idStatut}" class="fr-text--sm" role="status"></span>
            </div>`;
        const statut = document.getElementById(idStatut);

        document.getElementById(idFichier).addEventListener("change", async (evenement) => {
            const fichier = evenement.target.files[0];
            if (!fichier) return;
            statut.textContent = "Analyse du fichier…";
            try {
                const donnees = await DonneesVisu._analyserCsv(fichier);
                statut.textContent = `${fichier.name} : ${donnees.lignes.length} ligne(s), ${donnees.colonnes.length} colonne(s).`;
                callback(donnees);
            } catch (erreur) {
                statut.textContent = "";
                afficherToast("Fichier illisible", erreur.message || String(erreur), "error");
            }
        });

        document.getElementById(idBoutonSql).addEventListener("click", () => {
            const resultat = Travaux._dernierResultat;
            if (!resultat) {
                afficherToast("Aucun résultat disponible", "Exécutez d'abord une requête de lecture dans l'onglet Travaux.", "warning");
                return;
            }
            statut.textContent = `Résultat de la requête : ${resultat.lignes.length} ligne(s), ${resultat.colonnes.length} colonne(s).`;
            callback({ colonnes: resultat.colonnes, lignes: resultat.lignes });
        });
    },

    _analyserCsv(fichier) {
        return new Promise((resoudre, rejeter) => {
            Papa.parse(fichier, {
                header: true,
                skipEmptyLines: true,
                dynamicTyping: true,
                complete(resultat) {
                    const colonnes = resultat.meta.fields || [];
                    if (!colonnes.length) {
                        rejeter(new Error("Aucune colonne détectée (le fichier a-t-il une ligne d'en-tête ?)."));
                        return;
                    }
                    const lignes = resultat.data.map((objet) => colonnes.map((c) => objet[c]));
                    resoudre({ colonnes, lignes });
                },
                error(erreur) { rejeter(erreur); },
            });
        });
    },
};

// =============================================================================
// ONGLET CARTO
// =============================================================================
// Port du module cartographique de PLUME (même auteur, /var/www/html/PLUME,
// js/map.js) : rendu choroplèthe D3/TopoJSON sur fonds de carte français
// vendorisés (donnees-geo/), avec agrégation par code INSEE et anti-
// collision des étiquettes. Adapté en panneau d'onglet inline (au lieu
// d'une modale insérant une image dans un document) et alimenté par
// DonneesVisu au lieu d'un dépôt CSV dédié.
const Carto = {
    _initialise: false,
    _donnees: null,
    _geo: { charge: false, communes: [], epci: [], regionsMonde: [], comVersDep: new Map(), comVersReg: new Map(), comVersEpci: new Map() },
    _regToDeps: new Map(),
    _dernierConfig: null,
    _derniereCarteDonnees: null,
    _couleurDepart: null,
    _couleurArrivee: null,
    _formatNombre: new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }),

    PALETTE_SCALES: {
        divergentDescending: d3.interpolateRgbBasis(["#298641", "#EFB900", "#E91719"]),
        divergentAscending: d3.interpolateRgbBasis(["#E91719", "#EFB900", "#298641"]),
    },

    REGIONS_DICT: {
        "11": "Île-de-France", "24": "Centre-Val de Loire", "27": "Bourgogne-Franche-Comté",
        "28": "Normandie", "32": "Hauts-de-France", "44": "Grand Est", "52": "Pays de la Loire",
        "53": "Bretagne", "75": "Nouvelle-Aquitaine", "76": "Occitanie", "84": "Auvergne-Rhône-Alpes",
        "93": "Provence-Alpes-Côte d'Azur", "94": "Corse", "01": "Guadeloupe", "02": "Martinique",
        "03": "Guyane", "04": "La Réunion", "06": "Mayotte",
    },

    DEPARTEMENTS_DICT: {
        "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes", "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône", "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime", "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud", "2B": "Haute-Corse", "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne", "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère", "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault", "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère", "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire", "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne", "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne", "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse", "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise", "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques", "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin", "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire", "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris", "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres", "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse", "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne", "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis", "94": "Val-de-Marne", "95": "Val-d'Oise", "971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion", "976": "Mayotte",
    },

    async init() {
        if (Carto._initialise) return;
        Carto._initialise = true;
        DonneesVisu.creerSelecteur("carto-source-donnees", (donnees) => Carto._chargerDonnees(donnees));
        Carto._construireNuanciers();
        // Les 18 teintes DSFR comme dégradés continus, en plus des options
        // déjà présentes en dur dans le HTML (divergent x2, personnalisée) -
        // même motif que Graphiques.init() (PALETTE_LABELS_DSFR), "marianne"
        // présélectionnée pour rester cohérent avec l'ancien comportement
        // par défaut ("Bleu France").
        const optionsDsfr = Object.entries(PALETTE_LABELS_DSFR)
            .map(([cle, libelle]) => `<option value="${cle}"${cle === "marianne" ? " selected" : ""}>${echapper(libelle)}</option>`)
            .join("");
        document.getElementById("carto-palette").insertAdjacentHTML("afterbegin", optionsDsfr);
        await Carto._chargerReferentiels();
        Carto.actualiserCadrage();
    },

    async _chargerReferentiels() {
        if (Carto._geo.charge) return;
        try {
            const [communes, epci, mondes] = await Promise.all([
                Carto._chargerCsv("./donnees-geo/v_commune_2025.csv", ","),
                Carto._chargerCsv("./donnees-geo/EPCI_2025.csv", ";"),
                fetch("./donnees-geo/world_region_list.json").then((r) => r.json()),
            ]);
            Carto._geo.communes = communes;
            Carto._geo.epci = epci;
            Carto._geo.regionsMonde = mondes || [];
            communes.forEach((c) => {
                const com = Carto._colonneSure(c, "COM");
                Carto._geo.comVersDep.set(com, Carto._colonneSure(c, "DEP"));
                Carto._geo.comVersReg.set(com, Carto._colonneSure(c, "REG"));
            });
            // Table commune -> EPCI (agrégation des données utilisateur par
            // EPCI, §détail EPCI) : distincte de comVersDep/comVersReg, tirée
            // de EPCI_2025.csv (déjà chargé pour le filtre géographique de
            // l'échelle EPCI) plutôt que de v_commune_2025.csv, qui ne porte
            // pas cette information.
            epci.forEach((e) => {
                const com = Carto._colonneSure(e, "CODGEO");
                const codeEpci = Carto._colonneSure(e, "EPCI");
                if (com && codeEpci) Carto._geo.comVersEpci.set(com, codeEpci);
            });
            communes.forEach((c) => {
                const reg = Carto._colonneSure(c, "REG"), dep = Carto._colonneSure(c, "DEP");
                if (reg && dep) {
                    if (!Carto._regToDeps.has(reg)) Carto._regToDeps.set(reg, new Set());
                    Carto._regToDeps.get(reg).add(dep);
                }
            });
            Carto._geo.charge = true;
        } catch (erreur) {
            afficherToast("Référentiels géographiques indisponibles", erreur.message || String(erreur), "error");
        }
    },

    _chargerCsv(url, delimiteur) {
        return new Promise((resoudre, rejeter) => {
            Papa.parse(url, {
                download: true, header: true, delimiter: delimiteur, skipEmptyLines: true,
                complete: (r) => resoudre(r.data), error: rejeter,
            });
        });
    },

    // Certains référentiels ont des en-têtes de casse/variante différentes
    // (COM/com_2025, DEP/dep...) selon le millésime - port de getSafeCol.
    _colonneSure(ligne, cleAttendue) {
        if (!ligne) return "";
        if (ligne[cleAttendue] !== undefined) return String(ligne[cleAttendue]).trim();
        const cles = Object.keys(ligne);
        const cleTrouvee = cles.find((k) => k.includes(cleAttendue));
        return cleTrouvee ? String(ligne[cleTrouvee]).trim() : String(Object.values(ligne)[0] || "").trim();
    },

    // La colonne "code INSEE" (par défaut la 1re colonne, comme dans PLUME
    // où codeCol = Object.keys(rawCsvData[0])[0] est fixe) n'est jamais une
    // valeur à cartographier - elle est exclue des colonnes "valeur"
    // proposées, pour éviter de calculer une carte à partir du code lui-même.
    _chargerDonnees(donnees) {
        Carto._donnees = donnees;
        document.getElementById("carto-col-code").innerHTML = donnees.colonnes
            .map((c) => `<option value="${echapper(c)}">${echapper(c)}</option>`).join("");
        document.getElementById("carto-colonnes").hidden = false;
        Carto.actualiserColonnesValeur();
        const optionsFiltre = donnees.colonnes.map((c) => `<option value="${echapper(c)}">${echapper(c)}</option>`).join("");
        document.getElementById("carto-filtre-colonne").innerHTML =
            `<option value="">-- Champ à filtrer (optionnel) --</option>${optionsFiltre}`;
        document.getElementById("carto-filtre-avance").hidden = false;
    },

    // Reconstruit les listes "Colonne valeur"/"Colonne valeur 2" en excluant
    // la colonne actuellement choisie comme code INSEE - appelé au
    // chargement des données et à chaque changement de cette colonne.
    actualiserColonnesValeur() {
        if (!Carto._donnees) return;
        const colonneCode = document.getElementById("carto-col-code").value;
        const options = Carto._donnees.colonnes
            .filter((c) => c !== colonneCode)
            .map((c) => `<option value="${echapper(c)}">${echapper(c)}</option>`).join("");
        document.getElementById("carto-col-1").innerHTML = options;
        document.getElementById("carto-col-2").innerHTML = options;
    },

    // Affiche/masque le réglage fin des étiquettes (taille, filtres, forces
    // d'anti-collision), port du panneau #label-toolkit de PLUME.
    actualiserOutilsEtiquettes() {
        document.getElementById("carto-outils-etiquettes").hidden = document.getElementById("carto-etiquettes").value === "none";
    },

    _lignesEnObjets() {
        if (!Carto._donnees) return [];
        return Carto._donnees.lignes.map((ligne) => {
            const objet = {};
            Carto._donnees.colonnes.forEach((c, i) => { objet[c] = ligne[i]; });
            return objet;
        });
    },

    actualiserModeCalcul() {
        const mode = document.getElementById("carto-mode-calcul").value;
        document.getElementById("carto-col-2-groupe").hidden = !["ratio", "growth"].includes(mode);
    },

    actualiserPalette() {
        document.getElementById("carto-palette-personnalisee").hidden = document.getElementById("carto-palette").value !== "custom";
    },

    _construireNuanciers() {
        Carto._couleurDepart = PALETTES_DSFR.marianne.bg;
        Carto._couleurArrivee = PALETTES_DSFR.marianne.sun;
        Carto._remplirNuancier("carto-nuancier-depart", (couleur) => { Carto._couleurDepart = couleur; });
        Carto._remplirNuancier("carto-nuancier-arrivee", (couleur) => { Carto._couleurArrivee = couleur; });
    },

    // Nuancier à 2 niveaux : une teinte (19 couleurs illustratives DSFR),
    // puis une nuance de cette teinte (5-6 déclinaisons, de la plus claire
    // à la plus soutenue, cf. NUANCES_DSFR) - permet de vraiment jouer sur
    // la nuance d'une couleur plutôt que de se limiter à sa seule teinte
    // "principale", conformément à la refonte du système de couleur DSFR.
    _remplirNuancier(idConteneur, surChoix) {
        const conteneur = document.getElementById(idConteneur);
        const idNuances = `${idConteneur}-nuances`;
        conteneur.innerHTML = `
            <div class="sillon-nuancier" role="group" aria-label="Teinte">
                ${Object.entries(NUANCES_DSFR).map(([cle, nuances]) => `
                    <button type="button" style="background:${nuances.find((n) => n.code.startsWith("main")).hex};"
                        title="${echapper(PALETTE_LABELS_DSFR[cle] || cle)}"
                        data-teinte="${cle}" aria-pressed="false"></button>`).join("")}
            </div>
            <div class="sillon-nuancier sillon-nuancier-nuances" id="${idNuances}" role="group" aria-label="Nuance"></div>`;
        const zoneNuances = document.getElementById(idNuances);
        conteneur.querySelectorAll(".sillon-nuancier:first-child button").forEach((boutonTeinte) => {
            boutonTeinte.addEventListener("click", () => {
                conteneur.querySelectorAll(".sillon-nuancier:first-child button").forEach((b) => b.setAttribute("aria-pressed", "false"));
                boutonTeinte.setAttribute("aria-pressed", "true");
                const nuances = NUANCES_DSFR[boutonTeinte.dataset.teinte] || [];
                zoneNuances.innerHTML = nuances.map((n) => `
                    <button type="button" style="background:${n.hex};" title="${echapper(NUANCE_LABELS_DSFR[n.code] || n.code)} — ${n.hex}"
                        data-couleur="${n.hex}" data-code="${n.code}" aria-pressed="false"></button>`).join("");
                zoneNuances.querySelectorAll("button").forEach((boutonNuance) => {
                    boutonNuance.addEventListener("click", () => {
                        zoneNuances.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", "false"));
                        boutonNuance.setAttribute("aria-pressed", "true");
                        surChoix(boutonNuance.dataset.couleur);
                    });
                });
                // Sélectionne par défaut la nuance "principale" de la teinte.
                zoneNuances.querySelector('button[data-code^="main"]')?.click();
            });
        });
    },

    // Cascade région → département → EPCI/commune (§ports depuis
    // insertCarte()/updateUI() de PLUME) : reconstruite à chaque
    // changement de cadrage (zone affichée - distincte du détail, la maille
    // dessinée : §Carto cadrage/détail).
    actualiserCascade() {
        const cadrage = document.getElementById("carto-cadrage").value;
        const cascade = document.getElementById("carto-cascade");
        cascade.innerHTML = "";

        const creerSelect = (id, texte) => {
            const s = document.createElement("select");
            s.className = "fr-select fr-mb-1w";
            s.id = id;
            s.innerHTML = `<option value="">${texte}</option>`;
            // Pas de <label> visible pour ces menus de cascade générés
            // dynamiquement (le premier <option>, ex. "1. Choisir la
            // région", en joue déjà le rôle visuel) - aria-label indispensable
            // pour un nom accessible malgré tout (RGAA §11.1), constaté
            // manquant par un audit accessibilité.
            s.setAttribute("aria-label", texte);
            return s;
        };

        if (cadrage === "world") {
            const sel = creerSelect("carto-sel-monde", "Monde entier");
            sel.innerHTML = `<option value="all">Monde entier</option><option value="auto">Cadrage automatique sur les données</option>`;
            const categories = [...new Set(Carto._geo.regionsMonde.map((r) => r.category))];
            categories.forEach((cat) => {
                const groupe = document.createElement("optgroup");
                groupe.label = cat;
                Carto._geo.regionsMonde.filter((r) => r.category === cat).forEach((r) => {
                    const opt = document.createElement("option");
                    opt.value = r.code; opt.textContent = r.name;
                    groupe.appendChild(opt);
                });
                sel.appendChild(groupe);
            });
            cascade.appendChild(sel);
        } else if (cadrage !== "national") {
            const selRegion = creerSelect("carto-sel-region", "1. Choisir la région");
            Object.entries(Carto.REGIONS_DICT).forEach(([code, nom]) => {
                const opt = document.createElement("option");
                opt.value = code; opt.textContent = nom;
                selRegion.appendChild(opt);
            });
            cascade.appendChild(selRegion);

            let selDept, selEpci, selCommune;
            if (["departement", "epci", "commune"].includes(cadrage)) {
                selDept = creerSelect("carto-sel-departement", "2. Choisir le département");
                selDept.disabled = true;
                cascade.appendChild(selDept);
            }
            if (cadrage === "epci") {
                selEpci = creerSelect("carto-sel-epci", "3. Choisir l'EPCI");
                selEpci.disabled = true;
                cascade.appendChild(selEpci);
            }
            if (cadrage === "commune") {
                selCommune = creerSelect("carto-sel-commune", "3. Choisir la commune");
                selCommune.disabled = true;
                cascade.appendChild(selCommune);
            }

            selRegion.onchange = () => {
                if (!selDept) return;
                selDept.innerHTML = '<option value="">2. Choisir le département</option>';
                selDept.disabled = !selRegion.value;
                if (selRegion.value && Carto._regToDeps.has(selRegion.value)) {
                    Array.from(Carto._regToDeps.get(selRegion.value)).sort().forEach((d) => {
                        const opt = document.createElement("option");
                        opt.value = d; opt.textContent = `${d} - ${Carto.DEPARTEMENTS_DICT[d] || ""}`;
                        selDept.appendChild(opt);
                    });
                }
                if (selEpci) { selEpci.innerHTML = '<option value="">3. Choisir l\'EPCI</option>'; selEpci.disabled = true; }
                if (selCommune) { selCommune.innerHTML = '<option value="">3. Choisir la commune</option>'; selCommune.disabled = true; }
            };

            if (selDept) {
                selDept.onchange = () => {
                    const depVal = selDept.value;
                    if (selEpci) {
                        selEpci.innerHTML = '<option value="">3. Choisir l\'EPCI</option>';
                        selEpci.disabled = !depVal;
                        if (depVal) {
                            const epciUniques = new Map();
                            Carto._geo.epci.forEach((r) => {
                                if (Carto._colonneSure(r, "DEP") === depVal || Carto._colonneSure(r, "DEP").includes(depVal)) {
                                    const code = Carto._colonneSure(r, "EPCI");
                                    const nom = r["LIBEPCI"] || r["libepci"] || r["nom"] || `EPCI ${code}`;
                                    if (code && !epciUniques.has(code)) epciUniques.set(code, nom);
                                }
                            });
                            Array.from(epciUniques.entries()).sort((a, b) => a[1].localeCompare(b[1])).forEach(([code, nom]) => {
                                const opt = document.createElement("option");
                                opt.value = code; opt.textContent = `${nom} (${code})`;
                                selEpci.appendChild(opt);
                            });
                        }
                    }
                    if (selCommune) {
                        selCommune.innerHTML = '<option value="">3. Choisir la commune</option>';
                        selCommune.disabled = !depVal;
                        if (depVal) {
                            const communesUniques = new Map();
                            Carto._geo.communes.forEach((r) => {
                                if (Carto._colonneSure(r, "DEP") === depVal) {
                                    const code = Carto._colonneSure(r, "COM");
                                    const nom = Carto._colonneSure(r, "LIBELLE") || Carto._colonneSure(r, "NCC") || `Commune ${code}`;
                                    if (code && !communesUniques.has(code)) communesUniques.set(code, nom);
                                }
                            });
                            Array.from(communesUniques.entries()).sort((a, b) => a[1].localeCompare(b[1])).forEach(([code, nom]) => {
                                const opt = document.createElement("option");
                                opt.value = code; opt.textContent = `${nom} (${code})`;
                                selCommune.appendChild(opt);
                            });
                        }
                    }
                };
            }
        }
    },

    // Options de détail (maille dessinée et coloriée) valables pour chaque
    // cadrage (zone affichée) - matrice actée avec l'utilisateur : un
    // "détail EPCI" dessine des communes coloriées par leur EPCI plutôt que
    // des contours d'EPCI fusionnés (pas de topojson.merge, choix assumé
    // pour rester simple).
    DETAILS_PAR_CADRAGE: {
        national: [["departement", "Département"], ["region", "Région"], ["epci", "EPCI"], ["commune", "Commune"]],
        region: [["departement", "Département"], ["commune", "Commune"]],
        departement: [["commune", "Commune"], ["epci", "EPCI"]],
        epci: [["commune", "Commune"]],
        commune: [["commune", "Commune"]],
        world: [],
    },

    actualiserOptionsDetail() {
        const cadrage = document.getElementById("carto-cadrage").value;
        const options = Carto.DETAILS_PAR_CADRAGE[cadrage] || [];
        const groupe = document.getElementById("carto-detail-groupe");
        groupe.hidden = options.length <= 1;
        document.getElementById("carto-detail").innerHTML = options
            .map(([valeur, libelle]) => `<option value="${valeur}">${libelle}</option>`).join("");
    },

    // Point d'entrée du <select> Cadrage (index.html) : reconstruit à la
    // fois la cascade géographique (région/département/EPCI/commune, pour
    // choisir la zone précise) et les options de détail disponibles pour ce
    // cadrage - deux aspects indépendants, mais tous deux déclenchés par le
    // même changement de cadrage.
    actualiserCadrage() {
        Carto.actualiserCascade();
        Carto.actualiserOptionsDetail();
    },

    // Port de computeValorAggregation (map.js) : agrège les lignes de
    // données par code INSEE, jusqu'au détail cible (la maille dessinée -
    // §Carto cadrage/détail, distincte du cadrage qui ne filtre qu'une zone
    // sans changer la maille d'agrégation).
    _calculerAgregation(donneesBrutes, detailCible, modeCalcul, colCode, col1, col2) {
        const agregees = new Map();
        let totalGlobalCol1 = 0;
        donneesBrutes.forEach((ligne) => {
            let codeSource = String(ligne[colCode] ?? "").trim();
            if (!codeSource) return;
            if (codeSource.length === 1 || codeSource.length === 4) codeSource = "0" + codeSource;
            let codeCible = codeSource;
            if (detailCible === "departement") {
                codeCible = codeSource.length >= 4 ? Carto._geo.comVersDep.get(codeSource) : codeSource;
            } else if (detailCible === "region") {
                codeCible = codeSource.length >= 4 ? Carto._geo.comVersReg.get(codeSource) : codeSource;
            } else if (detailCible === "epci") {
                codeCible = codeSource.length >= 4 ? Carto._geo.comVersEpci.get(codeSource) : codeSource;
            }
            // detailCible === "commune" : codeCible reste codeSource, déjà à
            // la bonne maille (aucune remontée à faire).
            if (!codeCible) return;
            if (!agregees.has(codeCible)) agregees.set(codeCible, { val1: 0, val2: 0 });
            const acc = agregees.get(codeCible);
            const v1 = parseFloat(String(ligne[col1]).replace(",", ".")) || 0;
            const v2 = col2 ? (parseFloat(String(ligne[col2]).replace(",", ".")) || 0) : 0;
            acc.val1 += v1; acc.val2 += v2; totalGlobalCol1 += v1;
        });
        const resultat = new Map();
        agregees.forEach((acc, code) => {
            let val = 0;
            if (modeCalcul === "simple" || modeCalcul === "sum") val = acc.val1;
            else if (modeCalcul === "ratio") val = acc.val2 !== 0 ? acc.val1 / acc.val2 : 0;
            else if (modeCalcul === "growth") val = acc.val1 !== 0 ? ((acc.val2 - acc.val1) / acc.val1) * 100 : 0;
            else if (modeCalcul === "share") val = totalGlobalCol1 !== 0 ? (acc.val1 / totalGlobalCol1) * 100 : 0;
            resultat.set(String(code), val);
        });
        return resultat;
    },

    // Port de forceRectCollide (map.js) : force D3 d'anti-collision
    // rectangulaire pour l'étalement des étiquettes de carte.
    _forceRectCollide(padding) {
        let noeuds;
        function force(alpha) {
            const quad = d3.quadtree().x((d) => d.x).y((d) => d.y).addAll(noeuds);
            for (const d of noeuds) {
                quad.visit((q, x1, y1, x2, y2) => {
                    if (!q.length && q.data !== d) {
                        const d2 = q.data;
                        const w = (d.width + d2.width) / 2 + padding, h = (d.height + d2.height) / 2 + padding;
                        let x = d.x - d2.x, y = d.y - d2.y;
                        const absX = Math.abs(x), absY = Math.abs(y);
                        if (absX < w && absY < h) {
                            const lx = (w - absX) / w, ly = (h - absY) / h;
                            if (lx < ly) { x *= lx * alpha; d.x += x; d2.x -= x; }
                            else { y *= ly * alpha; d.y += y; d2.y -= y; }
                        }
                    }
                    return x1 > d.x + d.width / 2 || x2 < d.x - d.width / 2 || y1 > d.y + d.height / 2 || y2 < d.y - d.height / 2;
                });
            }
        }
        force.initialize = (n) => { noeuds = n; };
        return force;
    },

    // Port de drawD3Map (map.js) : la seule adaptation notable est la
    // couleur par défaut, fixée sur la palette "marianne" (pas de
    // --theme-sun/--theme-bg dynamiques comme dans PLUME, qui n'existent
    // pas dans SILLON).
    async _dessinerCarte(conteneur, config, dataMap) {
        const largeur = conteneur.clientWidth, hauteur = conteneur.clientHeight;
        const forcePhysique = config.physStrength ?? 0.15, paddingPhysique = config.physPadding ?? 4;
        const ratioPhysique = 0.62, tailleEtiquette = config.labelSize ?? 10;

        // Le fond de carte dépend du détail (maille dessinée), jamais du
        // cadrage (zone affichée) : une carte "France entière" peut aussi
        // bien dessiner des départements, des régions ou des communes.
        let fichierJson;
        if (config.cadrage === "world") fichierJson = "./donnees-geo/world_2025.json";
        else if (config.detail === "departement") fichierJson = "./donnees-geo/departement_2025.json";
        else if (config.detail === "region") fichierJson = "./donnees-geo/region_2025.json";
        else fichierJson = "./donnees-geo/commune_2025.json"; // détail "commune" ou "epci" (communes coloriées par leur EPCI)

        let geoJSON;
        try {
            geoJSON = await fetch(fichierJson).then((r) => r.json());
        } catch (erreur) { return false; }

        conteneur.innerHTML = "";
        let features = [];
        if (geoJSON.type === "Topology") {
            const cle = Object.keys(geoJSON.objects)[0];
            features = topojson.feature(geoJSON, geoJSON.objects[cle]).features;
        } else {
            features = geoJSON.features || [];
        }

        const obtenirIso = (d) => String(d.id || d.properties.iso_a3 || d.properties.ISO3 || d.properties.ADM0_A3 || "");

        // Filtre de ciblage : piloté par le cadrage (zone affichée), jamais
        // par le détail - les propriétés nécessaires (région, département,
        // EPCI d'appartenance) sont déjà présentes sur chaque feature du
        // fond de carte communal/départemental, pas besoin d'une table de
        // correspondance côté client ici (contrairement à l'agrégation des
        // données utilisateur, cf. _calculerAgregation).
        //
        // Une sélection de zone incomplète (région/département/EPCI/commune
        // pas encore choisie dans la cascade) renvoie false ci-dessous,
        // jamais true par défaut : featuresCiblees reste alors vide et la
        // fonction s'arrête au "return false" qui suit, déclenchant le
        // message "Sélection incomplète" (actualiserApercu). Avant ce
        // correctif, un cadrage "commune" sans commune choisie retombait
        // silencieusement sur "aucune restriction" et dessinait la France
        // entière au niveau communal - constaté en pratique.
        let featuresCiblees = features.filter((f) => {
            const p = f.properties;

            if (config.cadrage === "world") {
                if (!config.worldRegion || config.worldRegion === "all") return true;
                if (config.worldRegion === "auto" && dataMap) return dataMap.has(obtenirIso(f));
                const reg = Carto._geo.regionsMonde.find((r) => r.code === config.worldRegion);
                return reg ? reg.countries.includes(obtenirIso(f)) : true;
            }
            if (config.cadrage === "national") return true;

            const codeReg = String(p.code_insee_de_la_region || "");
            const codeDep = String(p.code_insee_du_departement || "");
            const codeCom = String(p.code_insee || "");
            const codeEpci = String(p.codes_siren_des_epci || "");

            if (config.cadrage === "region") return config.region ? codeReg === String(config.region) : false;
            if (config.cadrage === "departement") return config.dept ? codeDep === String(config.dept) : false;
            if (config.cadrage === "epci") return config.epci ? codeEpci === String(config.epci) : false;
            if (config.cadrage === "commune") return config.commune ? codeCom === String(config.commune) : false;
            return false;
        });

        if (featuresCiblees.length === 0) return false;

        const svg = d3.select(conteneur).append("svg").attr("width", largeur).attr("height", hauteur);
        let projection = config.cadrage === "world"
            ? d3.geoMercator().scale(1).translate([0, 0])
            : d3.geoConicConformal().center([2.45, 46.2]).scale(1).translate([0, 0]);
        const chemin = d3.geoPath().projection(projection);

        let featuresCamera = featuresCiblees;
        if (config.cadrage === "world") {
            const geants = ["FRA", "RUS", "USA", "ATA"];
            const camerasFiltrees = featuresCiblees.filter((f) => !geants.includes(obtenirIso(f)));
            if (camerasFiltrees.length > 0) featuresCamera = camerasFiltrees;
        } else if (config.cadrage === "national") {
            // Limite connue : n'exclut du cadrage caméra que les départements
            // et communes ultramarins (code_insee préfixé "97") - un détail
            // "région" n'est pas concerné, les régions d'outre-mer étant
            // codées "01"-"06" (Carto.REGIONS_DICT), sans préfixe commun
            // avec la métropole à filtrer aussi simplement.
            featuresCamera = featuresCiblees.filter((f) => !String(f.properties.code_insee || "").startsWith("97"));
        }

        // Bandeau de titre réservé (§Carto, titre superposé à la carte pour
        // un titre long, constaté en usage réel) : la carte est bornée pour
        // tenir entièrement sous cette hauteur, jamais juste approximée par
        // une translation comme auparavant (qui ne garantissait rien - une
        // forme pouvait déjà toucher le haut du cadre selon son ratio
        // largeur/hauteur). Le débordement horizontal d'un titre trop long
        // est traité séparément, cf. taille de police adaptative plus bas.
        const hauteurBandeauTitre = 40;
        const hauteurDisponible = hauteur - hauteurBandeauTitre;
        const limites = chemin.bounds({ type: "FeatureCollection", features: featuresCamera });
        const echelleCarte = 0.85 / Math.max((limites[1][0] - limites[0][0]) / largeur, (limites[1][1] - limites[0][1]) / hauteurDisponible);
        const translation = [
            (largeur - echelleCarte * (limites[1][0] + limites[0][0])) / 2,
            hauteurBandeauTitre + (hauteurDisponible - echelleCarte * (limites[1][1] + limites[0][1])) / 2,
        ];
        projection.scale(echelleCarte).translate(translation);

        const couleurPrincipale = PALETTES_DSFR.marianne.sun;
        const couleurFond = PALETTES_DSFR.marianne.bg;

        const valeurs = dataMap && dataMap.size > 0 ? Array.from(dataMap.values()) : [0];
        let valMin = d3.min(valeurs) || 0, valMax = d3.max(valeurs) || 0;
        if (valMin === valMax) { valMin = 0; valMax = valMax || 100; }

        let echelleCouleur;
        if (config.palette === "custom" && config.customColors && config.customColors.length >= 2) {
            echelleCouleur = d3.scaleSequential(d3.interpolateRgbBasis(config.customColors)).domain([valMin, valMax]);
        } else if (config.palette && Carto.PALETTE_SCALES[config.palette]) {
            echelleCouleur = d3.scaleSequential(Carto.PALETTE_SCALES[config.palette]).domain([valMin, valMax]);
        } else if (config.palette && PALETTES_DSFR[config.palette]) {
            // Une des 18 teintes DSFR choisies directement dans la liste
            // (§Carto palettes DSFR) : dégradé continu clair (bg) -> soutenu
            // (sun) de cette seule teinte, même principe que le repli
            // ci-dessous (jusqu'ici câblé en dur sur "marianne" uniquement).
            const p = PALETTES_DSFR[config.palette];
            echelleCouleur = d3.scaleLinear().domain([valMin, valMax]).range([p.bg, p.sun]);
        } else {
            echelleCouleur = d3.scaleLinear().domain([valMin, valMax]).range([couleurFond, couleurPrincipale]);
        }

        let featuresRendues = features;
        if (config.cadrage !== "national" && config.cadrage !== "world") featuresRendues = featuresCiblees;

        // Clé de jointure avec les données agrégées : le seul cas où cadrage
        // et détail divergent est le détail "epci", qui dessine des communes
        // (fond de carte communal) mais doit chercher la couleur avec le
        // code EPCI de la commune, pas son propre code commune - dataMap est
        // alors indexée par EPCI (_calculerAgregation appelée avec detail
        // "epci").
        const codeDonnees = (d) => {
            if (config.cadrage === "world") return obtenirIso(d);
            if (config.detail === "epci") return String(d.properties.codes_siren_des_epci || "");
            return String(d.properties.code_insee || "");
        };

        const g = svg.append("g");

        g.selectAll("path").data(featuresRendues).enter().append("path")
            .attr("d", chemin)
            .attr("fill", (d) => {
                const code = codeDonnees(d);
                if (!featuresCiblees.includes(d)) return "#f8f9fa";
                return dataMap?.has(code) ? echelleCouleur(dataMap.get(code)) : "#e5e5e5";
            })
            .attr("stroke", (d) => (featuresCiblees.includes(d) ? "#ffffff" : "#f0f0f0"))
            .attr("stroke-width", (d) => (featuresCiblees.includes(d) ? 0.5 : 0.2));

        if (config.labelType !== "none") {
            const noeudsEtiquette = [];
            const filtreNoms = config.labelFilterNames ? config.labelFilterNames.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean) : [];
            featuresCiblees.forEach((d) => {
                const centroide = chemin.centroid(d);
                if (isNaN(centroide[0])) return;
                const code = codeDonnees(d);
                const nom = config.cadrage === "world"
                    ? (d.properties.name_fr || d.properties.name || d.properties.NAME || "")
                    : (d.properties.nom_officiel || d.properties.nom || d.properties.NOM || d.properties.libgeo || d.properties.LIBGEO || d.properties.nom_com || d.properties.nom_commune || d.properties.nom_dept || d.properties.nom_reg || d.properties.libelle || "");
                const valeurBrute = dataMap?.has(code) ? dataMap.get(code) : 0;
                const texteValeur = dataMap?.has(code) ? Carto._formatNombre.format(valeurBrute) : "";

                // Filtre avancé (sur une autre colonne agrégée) puis filtre
                // par nom/code, port des 2 filtres du panneau d'étiquettes
                // de PLUME (map.js).
                let doitAfficher = true;
                if (config.filterDataMap && !isNaN(config.filterThreshold)) {
                    const valeurFiltre = config.filterDataMap.get(code) || 0;
                    const operateur = config.filterOperator;
                    if (operateur === ">") doitAfficher = valeurFiltre > config.filterThreshold;
                    else if (operateur === ">=") doitAfficher = valeurFiltre >= config.filterThreshold;
                    else if (operateur === "=") doitAfficher = valeurFiltre === config.filterThreshold;
                    else if (operateur === "<=") doitAfficher = valeurFiltre <= config.filterThreshold;
                    else if (operateur === "<") doitAfficher = valeurFiltre < config.filterThreshold;
                }
                if (doitAfficher && filtreNoms.length > 0) {
                    doitAfficher = filtreNoms.some((f) => nom.toLowerCase().includes(f) || code.toLowerCase() === f);
                }
                if (!doitAfficher) return;

                const longueurTexte = config.labelType === "both" ? Math.max(nom.length, texteValeur.length) : (config.labelType === "name" ? nom.length : texteValeur.length);
                if (longueurTexte === 0) return;
                noeudsEtiquette.push({
                    cx: centroide[0], cy: centroide[1], x: centroide[0], y: centroide[1],
                    nom, val: texteValeur, width: longueurTexte * (tailleEtiquette * ratioPhysique), height: tailleEtiquette * (config.labelType === "both" ? 2.4 : 1.2),
                });
            });
            const simulation = d3.forceSimulation(noeudsEtiquette)
                .force("x", d3.forceX((d) => d.cx).strength(forcePhysique))
                .force("y", d3.forceY((d) => d.cy).strength(forcePhysique))
                .force("collide", Carto._forceRectCollide(paddingPhysique))
                .stop();
            for (let i = 0; i < 200; ++i) simulation.tick();

            g.selectAll("text.label").data(noeudsEtiquette).enter().append("text")
                .attr("class", "label")
                .attr("x", (d) => d.x).attr("y", (d) => d.y).attr("text-anchor", "middle")
                .style("font-size", `${tailleEtiquette}px`)
                .style("font-family", "Marianne, sans-serif")
                .style("font-weight", "700")
                .style("fill", couleurPrincipale)
                .attr("stroke", "#ffffff")
                .attr("stroke-width", tailleEtiquette * 0.25)
                .attr("stroke-linejoin", "round")
                .style("paint-order", "stroke fill")
                .each(function (d) {
                    const el = d3.select(this);
                    if (config.labelType !== "value") el.append("tspan").attr("x", d.x).attr("dy", config.labelType === "both" ? "-0.2em" : "0.3em").text(d.nom);
                    if (config.labelType !== "name") el.append("tspan").attr("x", d.x).attr("dy", config.labelType === "both" ? "1.1em" : "0.3em").text(d.val);
                });
        }

        // Taille de police adaptative (§Carto, titre superposé à la carte) :
        // réduite si nécessaire pour tenir dans la largeur disponible (marge
        // de 20px de chaque côté), jamais agrandie au-delà de la taille de
        // base pour un titre court. getComputedTextLength() mesure le texte
        // une fois posé au DOM à la taille de base, pour en déduire le
        // facteur d'échelle exact plutôt que d'estimer une largeur de
        // caractère moyenne.
        const TAILLE_TITRE_BASE_REM = 1.1;
        const TAILLE_TITRE_MIN_REM = 0.7;
        const texteTitre = svg.append("text").attr("x", 20).attr("y", 35)
            .style("font-weight", "bold").style("font-size", `${TAILLE_TITRE_BASE_REM}rem`)
            .style("fill", couleurPrincipale).text(config.title);
        const largeurDisponibleTitre = largeur - 40;
        const largeurTitreMesuree = texteTitre.node().getComputedTextLength();
        if (largeurTitreMesuree > largeurDisponibleTitre) {
            const tailleAdaptee = Math.max(
                TAILLE_TITRE_MIN_REM,
                TAILLE_TITRE_BASE_REM * (largeurDisponibleTitre / largeurTitreMesuree),
            );
            texteTitre.style("font-size", `${tailleAdaptee}rem`);
        }

        if (dataMap && dataMap.size > 0 && valMin !== valMax && config.showLegend !== false) {
            // Position/orientation choisies par l'utilisateur (§Carto
            // position de la légende) : horizontale en bas (droite ou
            // gauche), ou verticale centrée sur la hauteur (droite ou
            // gauche) - la barre et le dégradé pivotent ensemble, min en
            // bas / max en haut pour la variante verticale (lecture
            // ascendante, convention usuelle des légendes de carte).
            const position = config.legendPosition || "bas-droite";
            const vertical = position === "droite" || position === "gauche";
            const largeurLegende = vertical ? 12 : 200;
            const hauteurLegende = vertical ? 200 : 12;
            const marge = 30;
            let xLegende, yLegende;
            if (position === "bas-gauche") { xLegende = marge; yLegende = hauteur - marge; }
            else if (position === "droite") { xLegende = largeur - largeurLegende - marge; yLegende = (hauteur - hauteurLegende) / 2; }
            else if (position === "gauche") { xLegende = marge; yLegende = (hauteur - hauteurLegende) / 2; }
            else { xLegende = largeur - largeurLegende - marge; yLegende = hauteur - marge; } // "bas-droite", repli par défaut

            const defs = svg.append("defs");
            const degrade = defs.append("linearGradient").attr("id", "carto-degrade")
                .attr("x1", "0%").attr("y1", vertical ? "100%" : "0%")
                .attr("x2", vertical ? "0%" : "100%").attr("y2", "0%");

            if (config.palette === "custom" && config.customColors && config.customColors.length >= 2) {
                const interpolateur = d3.interpolateRgbBasis(config.customColors);
                for (let i = 0; i <= 10; i++) degrade.append("stop").attr("offset", `${i * 10}%`).attr("stop-color", interpolateur(i / 10));
            } else if (config.palette && Carto.PALETTE_SCALES[config.palette]) {
                const interpolateur = Carto.PALETTE_SCALES[config.palette];
                for (let i = 0; i <= 10; i++) degrade.append("stop").attr("offset", `${i * 10}%`).attr("stop-color", interpolateur(i / 10));
            } else if (config.palette && PALETTES_DSFR[config.palette]) {
                // Une des 18 teintes DSFR (§Carto palettes DSFR) : même
                // dégradé bg->sun que celui réellement appliqué aux formes
                // de la carte (echelleCouleur ci-dessus) - oublié à l'ajout
                // des palettes DSFR, la légende gardait le dégradé "Bleu
                // France" par défaut quelle que soit la teinte choisie,
                // constaté en usage réel.
                const p = PALETTES_DSFR[config.palette];
                degrade.append("stop").attr("offset", "0%").attr("stop-color", p.bg);
                degrade.append("stop").attr("offset", "100%").attr("stop-color", p.sun);
            } else {
                degrade.append("stop").attr("offset", "0%").attr("stop-color", couleurFond);
                degrade.append("stop").attr("offset", "100%").attr("stop-color", couleurPrincipale);
            }

            const legende = svg.append("g").attr("transform", `translate(${xLegende}, ${yLegende})`);
            legende.append("rect").attr("width", largeurLegende).attr("height", hauteurLegende).style("fill", "url(#carto-degrade)").style("stroke", "#ccc");
            if (vertical) {
                legende.append("text").attr("x", largeurLegende / 2).attr("y", hauteurLegende + 14).attr("text-anchor", "middle").style("font-size", "0.75rem").text(Carto._formatNombre.format(valMin));
                legende.append("text").attr("x", largeurLegende / 2).attr("y", -6).attr("text-anchor", "middle").style("font-size", "0.75rem").text(Carto._formatNombre.format(valMax));
            } else {
                legende.append("text").attr("x", 0).attr("y", -6).style("font-size", "0.75rem").text(Carto._formatNombre.format(valMin));
                legende.append("text").attr("x", largeurLegende).attr("y", -6).attr("text-anchor", "end").style("font-size", "0.75rem").text(Carto._formatNombre.format(valMax));
            }
        }
        return true;
    },

    async actualiserApercu() {
        const conteneur = document.getElementById("carto-apercu");
        const boutonActualiser = document.getElementById("carto-bouton-actualiser");
        const boutonTelecharger = document.getElementById("carto-bouton-telecharger");
        // Génération potentiellement longue (fond de carte communal, ~22 Mo,
        // §détail commune/EPCI) : indicateur de chargement et boutons
        // désactivés le temps du traitement, pour ne jamais laisser
        // l'utilisateur relancer un second calcul par-dessus le premier
        // (constaté en pratique : une course entre deux appels concurrents
        // peut afficher un message d'erreur périmé après un rendu pourtant
        // réussi, cf. correctif du sélecteur Détail).
        boutonActualiser.disabled = true;
        boutonTelecharger.disabled = true;
        afficherChargement(conteneur, "Génération de la carte en cours…");
        try {
            const cadrage = document.getElementById("carto-cadrage").value;
            // "commune" par défaut (cadrage Monde/Commune, #carto-detail-groupe
            // masqué et donc vide) : c'est la maille déjà correcte dans ces deux
            // cas (aucune agrégation à faire, cf. _calculerAgregation).
            const detail = document.getElementById("carto-detail").value || "commune";
            let dataMap = null;
            let filterDataMap = null;
            const colonneFiltre = document.getElementById("carto-filtre-colonne")?.value;
            if (Carto._donnees) {
                const colCode = document.getElementById("carto-col-code").value;
                const modeCalcul = document.getElementById("carto-mode-calcul").value;
                const col1 = document.getElementById("carto-col-1").value;
                const col2 = document.getElementById("carto-col-2").value;
                const lignesObjets = Carto._lignesEnObjets();
                dataMap = Carto._calculerAgregation(lignesObjets, detail, modeCalcul, colCode, col1, col2);
                if (colonneFiltre) filterDataMap = Carto._calculerAgregation(lignesObjets, detail, "simple", colCode, colonneFiltre);
            }
            const paletteVal = document.getElementById("carto-palette").value;
            const config = {
                cadrage,
                detail,
                worldRegion: document.getElementById("carto-sel-monde")?.value,
                region: document.getElementById("carto-sel-region")?.value,
                dept: document.getElementById("carto-sel-departement")?.value,
                epci: document.getElementById("carto-sel-epci")?.value,
                commune: document.getElementById("carto-sel-commune")?.value,
                title: document.getElementById("carto-titre").value,
                labelType: document.getElementById("carto-etiquettes").value,
                showLegend: document.getElementById("carto-legende").checked,
                legendPosition: document.getElementById("carto-legende-position")?.value || "bas-droite",
                palette: paletteVal,
                customColors: paletteVal === "custom" ? [Carto._couleurDepart, Carto._couleurArrivee] : null,
                labelSize: parseFloat(document.getElementById("carto-etiquettes-taille")?.value) || 10,
                labelFilterNames: document.getElementById("carto-etiquettes-filtre-noms")?.value,
                physPadding: parseFloat(document.getElementById("carto-etiquettes-aeration")?.value) || 4,
                physStrength: parseFloat(document.getElementById("carto-etiquettes-repulsion")?.value) || 0.15,
                filterOperator: document.getElementById("carto-filtre-operateur")?.value,
                filterThreshold: parseFloat(document.getElementById("carto-filtre-valeur")?.value),
                filterDataMap,
            };
            Carto._dernierConfig = config;
            Carto._derniereCarteDonnees = dataMap;
            const succes = await Carto._dessinerCarte(conteneur, config, dataMap);
            if (!succes) {
                // _dessinerCarte a déjà vidé le conteneur avant son propre
                // retour anticipé (sélection incomplète) - sauf en cas
                // d'échec du fetch du fond de carte (erreur réseau), seul
                // chemin où l'indicateur de chargement resterait sinon
                // affiché indéfiniment.
                conteneur.innerHTML = "";
                afficherToast("Sélection incomplète", "Précisez la zone géographique à cartographier.", "warning");
            }
        } finally {
            boutonActualiser.disabled = false;
            boutonTelecharger.disabled = false;
        }
    },

    async telechargerPng() {
        const conteneur = document.getElementById("carto-apercu");
        if (!conteneur.querySelector("svg")) {
            afficherToast("Aucune carte", "Actualisez d'abord la carte avant de la télécharger.", "warning");
            return;
        }
        try {
            const canvas = await html2canvas(conteneur, { scale: 2, backgroundColor: "#ffffff", useCORS: true, logging: false });
            const lien = document.createElement("a");
            lien.download = "carte.png";
            lien.href = canvas.toDataURL("image/png");
            lien.click();
        } catch (erreur) {
            afficherToast("Erreur", "Impossible de générer l'image de la carte.", "error");
        }
    },
};

// =============================================================================
// ONGLET GRAPHIQUES
// =============================================================================
// Port du module graphiques de PLUME (js/chart.js, wrapper autour de
// Chart.js) : adapté en panneau d'onglet inline, alimenté par DonneesVisu.
const Graphiques = {
    _initialise: false,
    _donnees: null,
    _graphique: null,

    init() {
        if (Graphiques._initialise) return;
        Graphiques._initialise = true;
        DonneesVisu.creerSelecteur("graphiques-source-donnees", (donnees) => { Graphiques._donnees = donnees; });
        const selPalette = document.getElementById("graphiques-palette");
        selPalette.innerHTML = Object.entries(PALETTE_LABELS_DSFR)
            .map(([cle, libelle]) => `<option value="${cle}"${cle === "marianne" ? " selected" : ""}>${echapper(libelle)}</option>`)
            .join("");
    },

    // Port de dynamicPalette (chart.js), mais construite à partir d'une
    // palette DSFR choisie explicitement (PALETTES_DSFR) plutôt que de
    // variables CSS --theme-* dynamiques (absentes dans SILLON).
    _construirePalette() {
        const cle = document.getElementById("graphiques-palette").value || "marianne";
        const p = PALETTES_DSFR[cle] || PALETTES_DSFR.marianne;
        return [
            p.main, p.sun,
            `color-mix(in srgb, ${p.main}, white 25%)`,
            `color-mix(in srgb, ${p.main}, white 55%)`,
            `color-mix(in srgb, ${p.main}, white 80%)`,
            `color-mix(in srgb, ${p.sun}, black 20%)`,
            `color-mix(in srgb, ${p.sun}, black 45%)`,
            "#666666",
        ];
    },

    actualiserApercu() {
        if (!Graphiques._donnees) {
            afficherToast("Aucune donnée", "Déposez un CSV ou utilisez le résultat d'une requête SQL.", "warning");
            return;
        }
        let { colonnes, lignes } = Graphiques._donnees;
        // CSV à une seule ligne de données (chaque colonne est en réalité
        // une catégorie) - port de la détection/transposition 2-lignes de
        // generateChartFromCSV (chart.js).
        if (lignes.length === 1 && colonnes.length > 2) {
            const etiquettesSource = colonnes;
            const valeursSource = lignes[0];
            colonnes = ["Libellés", "Valeurs"];
            lignes = etiquettesSource.map((e, i) => [e, valeursSource[i]]);
        }
        if (colonnes.length < 2 || lignes.length === 0) {
            afficherToast("Données invalides", "Il faut au moins une colonne d'étiquettes et une colonne de valeurs.", "warning");
            return;
        }

        const type = document.getElementById("graphiques-type").value;
        const titre = document.getElementById("graphiques-titre").value || "Graphique";
        const palette = Graphiques._construirePalette();

        const datasets = colonnes.slice(1).map((nomColonne, c) => {
            const couleur = palette[c % palette.length];
            return {
                label: String(nomColonne),
                data: lignes.map((ligne) => {
                    const brut = String(ligne[c + 1] ?? "0").replace(",", ".");
                    const val = parseFloat(brut);
                    return isNaN(val) ? 0 : val;
                }),
                backgroundColor: ["doughnut", "polarArea"].includes(type)
                    ? palette
                    : (["line", "radar"].includes(type) ? `color-mix(in srgb, ${couleur}, transparent 80%)` : couleur),
                borderColor: ["doughnut", "polarArea"].includes(type) ? "#ffffff" : couleur,
                borderWidth: 2,
                borderRadius: type === "bar" || type === "horizontalBar" ? 4 : 0,
                fill: type === "line" ? "origin" : true,
                tension: 0.4,
            };
        });
        const etiquettes = lignes.map((ligne) => String(ligne[0]));

        const typeReel = type === "horizontalBar" ? "bar" : type;
        const estHorizontal = type === "horizontalBar";
        const estCirculaire = ["doughnut", "radar", "polarArea"].includes(typeReel);

        if (Graphiques._graphique) Graphiques._graphique.destroy();
        const canevas = document.getElementById("graphiques-canvas");
        Graphiques._graphique = new Chart(canevas, {
            type: typeReel,
            data: { labels: etiquettes, datasets },
            plugins: [ChartDataLabels],
            options: {
                indexAxis: estHorizontal ? "y" : "x",
                responsive: true,
                animation: false,
                layout: { padding: { top: 30, bottom: 10, left: 10, right: 10 } },
                plugins: {
                    title: { display: true, text: titre, font: { size: 16, weight: "bold" }, padding: { bottom: 10 } },
                    legend: { display: true, position: "bottom", labels: { usePointStyle: true, padding: 20 } },
                    datalabels: {
                        display: "auto",
                        backgroundColor: estCirculaire ? "transparent" : "rgba(255,255,255,0.8)",
                        borderRadius: 3, padding: 2,
                        color: estCirculaire ? "#ffffff" : PALETTES_DSFR.marianne.sun,
                        font: { weight: "bold", size: 11 },
                        anchor: estCirculaire ? "center" : "end",
                        align: estCirculaire ? "center" : (estHorizontal ? "right" : "top"),
                        offset: 4,
                        formatter: (v) => (!v || isNaN(v)) ? "" : new Intl.NumberFormat("fr-FR").format(v),
                    },
                },
                // Axe catégorie (l'étiquette, pas la valeur numérique) : le
                // callback reçoit l'index du tick, pas le libellé - il faut
                // this.getLabelForValue(v) pour le résoudre, donc une
                // fonction classique (pas fléchée, qui perdrait le "this"
                // lié par Chart.js à l'échelle).
                scales: estCirculaire ? {} : {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: function (v) { return estHorizontal ? this.getLabelForValue(v) : new Intl.NumberFormat("fr-FR").format(v); } },
                    },
                    x: {
                        ticks: { callback: function (v) { return estHorizontal ? new Intl.NumberFormat("fr-FR").format(v) : this.getLabelForValue(v); } },
                    },
                },
            },
        });

        document.getElementById("graphiques-table-accessible").innerHTML =
            Graphiques._construireTableAccessible(etiquettes, datasets, titre);
    },

    // Port de buildAccessibleChartTable (chart.js) : tableau caché
    // visuellement (fr-sr-only) équivalent au graphique pour les
    // technologies d'assistance (RGAA).
    _construireTableAccessible(etiquettes, datasets, titre) {
        let html = `<table class="fr-sr-only"><caption>Données du graphique : ${echapper(titre)}</caption>`;
        html += `<thead><tr><th scope="col">Catégorie</th>${datasets.map((ds) => `<th scope="col">${echapper(ds.label)}</th>`).join("")}</tr></thead><tbody>`;
        etiquettes.forEach((etiquette, i) => {
            html += `<tr><th scope="row">${echapper(etiquette)}</th>${datasets.map((ds) => `<td>${echapper(ds.data[i])}</td>`).join("")}</tr>`;
        });
        html += "</tbody></table>";
        return html;
    },

    telechargerPng() {
        if (!Graphiques._graphique) {
            afficherToast("Aucun graphique", "Générez d'abord un graphique avant de le télécharger.", "warning");
            return;
        }
        const lien = document.createElement("a");
        lien.download = "graphique.png";
        lien.href = Graphiques._graphique.toBase64Image();
        lien.click();
    },
};

// =============================================================================
// ONGLET DIAGRAMMES (Mermaid)
// =============================================================================
// Port du module Mermaid de PLUME (js/mermaid.js) : éditeur de texte avec
// aperçu en direct et modèles pré-remplis, sans lien CSV (Mermaid ne s'y
// prête pas nativement). Adapté en panneau d'onglet inline (au lieu d'une
// modale DSFR pilotée par window.dsfr, non vendorisé côté JS dans SILLON),
// et réutilise mermaid.render() déjà employé pour l'aperçu des jobs dans
// l'onglet Suivi.
const MERMAID_SAMPLES = {
    flowchart: "%%{init: {\"flowchart\": {\"htmlLabels\": false}} }%%\ngraph TD\n    A[Réception du dossier] --> B{Dossier complet ?}\n    B -- Oui --> C[Instruction]\n    B -- Non --> D[Demande de pièces complémentaires]\n    C --> E([Notification à l'usager])",
    sequence: "sequenceDiagram\n    participant U as Usager\n    participant A as Agent\n    participant S as Système\n    U->>A: Dépôt de demande\n    A->>S: Saisie des données\n    S-->>A: Validation technique\n    A-->>U: Remise du récépissé",
    mindmap: "mindmap\n  root((Action Publique))\n    Transition Écologique\n      Énergies renouvelables\n      Rénovation thermique\n    Numérique\n      Démarches en ligne\n      Inclusion numérique\n    Sécurité\n      Prévention\n      Intervention",
    state: "stateDiagram-v2\n    [*] --> Brouillon\n    Brouillon --> Relecture : Demande d'avis\n    Relecture --> Brouillon : Corrections requises\n    Relecture --> Valide : Avis favorable\n    Valide --> Publie : Mise en ligne\n    Publie --> [*]\n\n    state \"Validé\" as Valide\n    state \"Publié\" as Publie",
    architecture: "architecture-beta\n    group si(cloud)[Zone SI]\n    service parefeu(cloud)[Pare Feu]\n    service web(server)[Serveur Web] in si\n    service bdd(database)[Base Donnees] in si\n\n    parefeu:R -- L:web\n    web:R -- L:bdd",
    c4: "C4Context\n    title Cartographie du Système\n    UpdateLayoutConfig($c4ShapeInRow=\"1\")\n    Person(agent, \"Agent Public\", \"Utilise la plateforme\")\n    System(sillon, \"Plateforme SILLON\", \"Requêtage et traitement de données\")\n    System_Ext(sso, \"Authentification\", \"Authentification de l'État\")\n    Rel(agent, sillon, \"Interroge des données\", \"HTTPS\")\n    Rel(sillon, sso, \"Authentifie l'utilisateur via\", \"OIDC\")",
    block: "block-beta\n    columns 3\n    Frontend[\"Interface Utilisateur\"]\n    Middleware[\"API (Flask)\"]\n    Backend[\"Base de données (PostgreSQL)\"]\n    Frontend --> Middleware\n    Middleware --> Backend",
    packet: "packet-beta\n    title En-tête IPv4\n    0-3: \"Version\"\n    4-7: \"IHL\"\n    8-15: \"TOS\"\n    16-31: \"Longueur Totale\"\n    32-47: \"Identification\"\n    48-50: \"Flags\"\n    51-63: \"Fragment Offset\"\n    64-71: \"TTL\"\n    72-79: \"Protocole\"\n    80-95: \"Header Checksum\"\n    96-127: \"IP Source\"\n    128-159: \"IP Destination\"",
    classDiagram: "classDiagram\n    class AgentPublic {\n        +String matricule\n        +String nom\n        +traiterDossier()\n    }\n    class Dossier {\n        +int numero\n        +String statut\n        +valider()\n    }\n    AgentPublic \"1\" -- \"*\" Dossier : instruit",
    er: "erDiagram\n    USAGER ||--o{ DEMANDE : soumet\n    USAGER {\n        string numero_secu\n        string nom\n        string email\n    }\n    DEMANDE ||--|{ DOCUMENT : contient\n    DEMANDE {\n        int numero_dossier\n        date date_depot\n        string statut\n    }",
    requirement: "requirementDiagram\n    requirement \"Hébergement Sécurisé\" {\n      id: \"REQ-001\"\n      text: \"L'application doit être hébergée sur une infrastructure qualifiée.\"\n      risk: high\n      verifymethod: inspection\n    }\n    element \"Serveur Dédié\" {\n      type: \"Infrastructure\"\n    }\n    \"Serveur Dédié\" - satisfies -> \"Hébergement Sécurisé\"",
    kanban: "kanban\n    A Faire\n      [Rédiger le cahier des charges]\n      [Valider le budget]\n    En Cours\n      [Développement]\n    Terminé\n      [POC]",
    gantt: "gantt\n    title Planning de Déploiement\n    dateFormat  YYYY-MM-DD\n    section Phase 1\n    Conception           :a1, 2026-01-01, 30d\n    Développement        :after a1, 20d\n    section Phase 2\n    Tests et Recette     :a2, 2026-03-01, 15d\n    Mise en production   :after a2, 5d",
    timeline: "timeline\n    title Historique du projet\n    2024 : Lancement de la concertation\n         : Rapport préliminaire\n    2025 : Cadrage\n         : Développement\n    2026 : Déploiement\n         : Mise en place",
    wardley: "wardley-beta\n    title Stratégie de plateforme logicielle\n\n    anchor \"Usager\" [0.90, 0.95]\n    component \"Application web\" [0.75, 0.80]\n    component \"API\" [0.70, 0.65]\n    component \"Authentification\" [0.60, 0.55]\n    component \"Base de données\" [0.50, 0.45]\n    component \"Serveur\" [0.30, 0.95]\n\n    \"Usager\" -> \"Application web\"\n    \"Application web\" -> \"API\"\n    \"API\" -> \"Authentification\"\n    \"API\" -> \"Base de données\"\n    \"Base de données\" -> \"Serveur\"",
    journey: "journey\n    title Parcours usager : Demande de subvention\n    section Préparation\n      Recherche d'information: 5: Usager\n      Création du compte: 4: Usager, Système\n    section Dépôt\n      Formulaire en ligne: 3: Usager\n      Ajout des pièces justificatives: 2: Usager\n    section Instruction\n      Vérification du dossier: 4: Agent\n      Validation finale: 5: Directeur",
    treemap: "treemap-beta\n\"Budget (K€)\"\n    \"Transition Écologique\"\n        \"Rénovation\": 300\n        \"Mobilité\": 200\n    \"Santé Publique\"\n        \"Hôpitaux\": 350\n        \"Prévention\": 50",
    venn: "venn-beta\n  title \"Croisement des Compétences\"\n  set Dev[\"Développement\"]:50\n  set Sec[\"Sécurité\"]:50\n  set Res[\"Réseau\"]:50\n  union Dev,Sec[\"DevSec\"]:20\n  union Sec,Res[\"SecRes\"]:15\n  union Dev,Res[\"DevRes\"]:10\n  union Dev,Sec,Res[\"DevSecOps\"]:5",
    sankey: "sankey-beta\n\nBudget,Santé Publique,400\nBudget,Transition Écologique,350\nSanté Publique,Hôpitaux,250\nSanté Publique,Prévention,150\nTransition Écologique,Rénovation,200\nTransition Écologique,Mobilité,150",
    xychart: "xychart-beta\n    title \"Évolution mensuelle des dossiers\"\n    x-axis [\"Jan\", \"Fév\", \"Mar\", \"Avr\", \"Mai\", \"Juin\"]\n    y-axis \"Volume traité\" 0 --> 500\n    bar [150, 200, 350, 400, 280, 450]\n    line [150, 200, 350, 400, 280, 450]",
    quadrant: "quadrantChart\n    title Matrice Eisenhower\n    x-axis Moins urgent --> Plus urgent\n    y-axis Moins important --> Plus important\n    quadrant-1 A faire immédiatement\n    quadrant-2 A planifier\n    quadrant-3 A abandonner\n    quadrant-4 A déléguer\n    \"Urgence sécurité\": [0.9, 0.9]\n    \"Dossier de fond\": [0.3, 0.8]\n    \"Réunion mineure\": [0.2, 0.3]\n    \"Appel téléphonique\": [0.8, 0.4]",
    pie: "pie showData\n    title Répartition du budget alloué (en K€)\n    \"Subventions\" : 450\n    \"Fonctionnement\" : 250\n    \"Investissement\" : 200\n    \"Communication\" : 100",
    gitgraph: "gitGraph\n    commit id: \"v1\" tag: \"Lancement\"\n    branch developpement\n    checkout developpement\n    commit id: \"dev1\" msg: \"Nouvel outil\"\n    checkout main\n    merge developpement\n    commit id: \"v2\" tag: \"Validation finale\"",
};

const Diagrammes = {
    _initialise: false,
    _minuteurApercu: null,

    init() {
        if (Diagrammes._initialise) return;
        Diagrammes._initialise = true;
        document.getElementById("diagrammes-modele").innerHTML = Object.keys(MERMAID_SAMPLES)
            .map((cle) => `<option value="${cle}"${cle === "flowchart" ? " selected" : ""}>${echapper(cle)}</option>`).join("");
        const zone = document.getElementById("diagrammes-code");
        zone.value = MERMAID_SAMPLES.flowchart;
        zone.addEventListener("input", () => Diagrammes._planifierApercu());
        Diagrammes._actualiserApercu();
    },

    chargerModele(cle) {
        if (!MERMAID_SAMPLES[cle]) return;
        document.getElementById("diagrammes-code").value = MERMAID_SAMPLES[cle];
        Diagrammes._actualiserApercu();
    },

    // Aperçu débouncé (300 ms), port de updateMermaidPreview (mermaid.js).
    _planifierApercu() {
        clearTimeout(Diagrammes._minuteurApercu);
        Diagrammes._minuteurApercu = setTimeout(() => Diagrammes._actualiserApercu(), 300);
    },

    async _actualiserApercu() {
        const conteneur = document.getElementById("diagrammes-apercu");
        const code = document.getElementById("diagrammes-code").value.trim();
        if (!code) { conteneur.innerHTML = ""; return; }
        try {
            const id = `diagramme-apercu-${Math.floor(Math.random() * 100000)}`;
            const { svg } = await mermaid.render(id, code);
            conteneur.innerHTML = svg;
        } catch (erreur) {
            conteneur.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message || String(erreur))}</div>`;
        }
    },

    async telecharger() {
        const code = document.getElementById("diagrammes-code").value.trim();
        if (!code) return;
        try {
            const id = `diagramme-export-${Math.floor(Math.random() * 100000)}`;
            const { svg } = await mermaid.render(id, code);
            const pngDataUrl = await Diagrammes._convertirSvgEnPng(svg);
            const lien = document.createElement("a");
            lien.download = "diagramme.png";
            lien.href = pngDataUrl;
            lien.click();
        } catch (erreurPng) {
            try {
                const id = `diagramme-export-${Math.floor(Math.random() * 100000)}`;
                const { svg } = await mermaid.render(id, code);
                const lien = document.createElement("a");
                lien.download = "diagramme.svg";
                lien.href = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
                lien.click();
            } catch (erreurSvg) {
                afficherToast("Erreur", "Impossible de générer le diagramme.", "error");
            }
        }
    },

    // Port de convertMermaidSvgToPng (mermaid.js) : réécriture de la
    // balise <svg> (dimensions extraites du viewBox, namespace, CDATA sur
    // les <style>) pour un rendu fiable sur <canvas>, puis conversion PNG.
    _convertirSvgEnPng(svgString) {
        return new Promise((resoudre, rejeter) => {
            const canevas = document.createElement("canvas");
            const ctx = canevas.getContext("2d");
            const image = new Image();

            const divTemp = document.createElement("div");
            divTemp.innerHTML = svgString.trim();
            const noeudSvg = divTemp.querySelector("svg");
            if (!noeudSvg) { rejeter(new Error("Aucun nœud SVG généré.")); return; }

            let largeurReelle = 800, hauteurReelle = 600;
            const viewBox = noeudSvg.getAttribute("viewBox");
            if (viewBox) {
                const parties = viewBox.split(/[\s,]+/);
                if (parties.length >= 4) {
                    largeurReelle = parseFloat(parties[2]);
                    hauteurReelle = parseFloat(parties[3]);
                }
            }

            noeudSvg.removeAttribute("width");
            noeudSvg.removeAttribute("height");
            noeudSvg.removeAttribute("style");
            noeudSvg.setAttribute("width", `${largeurReelle}px`);
            noeudSvg.setAttribute("height", `${hauteurReelle}px`);
            if (!noeudSvg.getAttribute("xmlns")) noeudSvg.setAttribute("xmlns", "http://www.w3.org/2000/svg");

            let svgStrict = new XMLSerializer().serializeToString(noeudSvg);
            svgStrict = svgStrict.replace(/<style[^>]*>([\s\S]*?)<\/style>/gi, (correspondance, contenu) => {
                if (contenu.includes("<![CDATA[")) return correspondance;
                return `<style><![CDATA[\n${contenu}\n]]></style>`;
            });

            const dataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgStrict)}`;

            image.onload = () => {
                const echelle = 2;
                canevas.width = largeurReelle * echelle;
                canevas.height = hauteurReelle * echelle;
                ctx.fillStyle = "#ffffff";
                ctx.fillRect(0, 0, canevas.width, canevas.height);
                ctx.scale(echelle, echelle);
                ctx.drawImage(image, 0, 0, largeurReelle, hauteurReelle);
                resoudre(canevas.toDataURL("image/png"));
            };
            image.onerror = () => rejeter(new Error("Génération PNG échouée."));
            image.src = dataUrl;
        });
    },
};

// =============================================================================
// ONGLET REPRÉSENTATIONS DSFR (§5.10)
// =============================================================================
// Port de cinq blocs "projections" DSFR de PLUME (js/components.js) : mise
// en exergue, chiffre clé, citation, tableau, frise chronologique. Dans
// PLUME, ces blocs sont insérés dans un document contenteditable plus large
// et édités en place (clic + frappe) - seule la Frise y a déjà un vrai
// "Studio" (formulaire + aperçu live). SILLON n'a pas de document éditable
// dans lequel insérer ces blocs : les cinq types sont donc uniformément
// pilotés par formulaire (texte simple, pas de mise en forme riche) plutôt
// que par édition en place, sur le modèle déjà établi par Carto/Graphiques/
// Diagrammes (formulaire + aperçu + téléchargement).
const Representations = {
    _initialise: false,
    // Avatar par défaut de la Citation (SVG gris, repris tel quel de PLUME)
    // si aucun portrait n'est chargé.
    _avatarParDefaut: "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 24 24' fill='none' stroke='%23ccc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='8' r='5'/%3E%3Cpath d='M20 21a8 8 0 0 0-16 0'/%3E%3C/svg%3E",
    _photoCitation: null,
    _valeursTableau: [],
    _donneesFrise: null,
    _colonnesFrise: null,

    init() {
        if (Representations._initialise) return;
        Representations._initialise = true;

        const selPalette = document.getElementById("repr-palette");
        selPalette.innerHTML = Object.entries(PALETTE_LABELS_DSFR)
            .map(([cle, libelle]) => `<option value="${cle}"${cle === "marianne" ? " selected" : ""}>${echapper(libelle)}</option>`)
            .join("");
        selPalette.addEventListener("change", Representations.actualiserApercu);

        // Écoute "live" sur les champs texte (pas de bouton Actualiser
        // séparé : ces rendus sont légers, contrairement à Carto qui charge
        // un fond de carte volumineux) - cohérent avec les Studios déjà
        // réactifs de PLUME (Citation/Tableau/Frise).
        [
            "repr-exergue-titre", "repr-exergue-texte",
            "repr-chiffre-valeur", "repr-chiffre-texte",
            "repr-citation-texte", "repr-citation-auteur", "repr-citation-fonction",
            "repr-frise-titre", "repr-frise-orientation",
        ].forEach((id) => document.getElementById(id).addEventListener("input", Representations.actualiserApercu));

        document.getElementById("repr-tableau-entete").addEventListener("change", Representations.actualiserApercu);
        document.getElementById("repr-tableau-colonnes").addEventListener("input", Representations.regenererGrilleTableau);
        document.getElementById("repr-tableau-lignes").addEventListener("input", Representations.regenererGrilleTableau);
        document.getElementById("repr-citation-fichier").addEventListener("change", Representations._chargerPhotoCitation);
        document.getElementById("repr-frise-fichier").addEventListener("change", Representations.importerCsvFrise);
        DonneesVisu.creerSelecteur("repr-tableau-source-donnees", (donnees) => Representations._chargerDonneesTableau(donnees));

        Representations.regenererGrilleTableau();
        Representations.actualiserChampsVisibles();
    },

    actualiserChampsVisibles() {
        const type = document.getElementById("repr-type").value;
        ["exergue", "chiffre", "citation", "tableau", "frise"].forEach((t) => {
            document.getElementById(`repr-champs-${t}`).hidden = t !== type;
        });
        Representations.actualiserApercu();
    },

    actualiserAffichagePhoto() {
        const style = document.getElementById("repr-citation-photo").value;
        document.getElementById("repr-citation-upload-groupe").hidden = style === "none";
        Representations.actualiserApercu();
    },

    _chargerPhotoCitation(evenement) {
        const fichier = evenement.target.files[0];
        if (!fichier) return;
        // Même limite que PLUME (components.js) : un portrait n'a pas
        // besoin d'être plus lourd, et une image trop grande ralentirait
        // inutilement la rasterisation html2canvas au téléchargement.
        if (fichier.size > 2 * 1024 * 1024) {
            afficherToast("Image trop lourde", "Veuillez choisir un portrait de moins de 2 Mo.", "error");
            evenement.target.value = "";
            return;
        }
        const lecteur = new FileReader();
        lecteur.onload = (evt) => {
            Representations._photoCitation = evt.target.result;
            Representations.actualiserApercu();
        };
        lecteur.readAsDataURL(fichier);
    },

    // Redimensionne la grille de cellules en conservant les valeurs déjà
    // saisies (jamais de remise à zéro complète) : contrairement à PLUME,
    // qui édite les cellules d'un tableau HTML directement en place
    // (contenteditable), SILLON n'a pas de document éditable - cette grille
    // de champs <input> en est l'équivalent formulaire.
    regenererGrilleTableau() {
        const nbColonnes = Math.max(1, Math.min(15, parseInt(document.getElementById("repr-tableau-colonnes").value) || 1));
        const nbLignes = Math.max(1, Math.min(50, parseInt(document.getElementById("repr-tableau-lignes").value) || 1));
        const anciennes = Representations._valeursTableau;
        const valeurs = [];
        for (let i = 0; i < nbLignes; i++) {
            const ligne = [];
            for (let j = 0; j < nbColonnes; j++) ligne.push(anciennes[i]?.[j] ?? "");
            valeurs.push(ligne);
        }
        Representations._valeursTableau = valeurs;
        Representations._construireGrilleTableau();
    },

    // Alimente la grille depuis le sélecteur commun CSV/SQL (DonneesVisu,
    // même comportement que Carto/Graphiques) : la 1re ligne insérée est
    // l'en-tête (noms de colonnes), le style d'en-tête est présélectionné
    // en conséquence.
    _chargerDonneesTableau(donnees) {
        const nbColonnes = Math.max(1, Math.min(15, donnees.colonnes.length));
        const nbLignes = Math.max(1, Math.min(50, donnees.lignes.length + 1));
        document.getElementById("repr-tableau-colonnes").value = nbColonnes;
        document.getElementById("repr-tableau-lignes").value = nbLignes;
        document.getElementById("repr-tableau-entete").value = "colonnes";

        const toutesLesLignes = [donnees.colonnes, ...donnees.lignes];
        Representations._valeursTableau = toutesLesLignes
            .slice(0, nbLignes)
            .map((ligne) => ligne.slice(0, nbColonnes).map((val) => (val === null || val === undefined) ? "" : String(val)));
        Representations._construireGrilleTableau();
    },

    _construireGrilleTableau() {
        const valeurs = Representations._valeursTableau;
        const grille = document.getElementById("repr-tableau-grille");
        grille.innerHTML = `<table style="border-collapse:collapse;">${valeurs.map((ligne, i) => `
            <tr>${ligne.map((val, j) => `
                <td style="padding:2px;"><input class="fr-input fr-input--sm" style="width:6rem;" data-ligne="${i}" data-colonne="${j}" value="${echapper(val)}"></td>`).join("")}</tr>`).join("")}</table>`;
        grille.querySelectorAll("input").forEach((champ) => {
            champ.addEventListener("input", () => {
                Representations._valeursTableau[Number(champ.dataset.ligne)][Number(champ.dataset.colonne)] = champ.value;
                Representations.actualiserApercu();
            });
        });
        Representations.actualiserApercu();
    },

    async importerCsvFrise(evenement) {
        const fichier = evenement.target.files[0];
        if (!fichier) return;
        try {
            // 3 premières colonnes = date / titre / description (optionnelle),
            // même déduction que insertTimelineFromCSV() de PLUME.
            const { colonnes, lignes } = await DonneesVisu._analyserCsv(fichier);
            if (colonnes.length < 2) {
                afficherToast("Fichier incomplet", "Le CSV doit contenir au moins 2 colonnes (date, titre).", "error");
                return;
            }
            Representations._colonnesFrise = { date: colonnes[0], titre: colonnes[1], description: colonnes[2] || null };
            Representations._donneesFrise = lignes.map((ligne) => {
                const objet = {};
                colonnes.forEach((c, i) => { objet[c] = ligne[i]; });
                return objet;
            });

            const filtres = document.getElementById("repr-frise-filtres");
            filtres.innerHTML = Representations._donneesFrise.map((ligne, i) => `
                <div class="fr-checkbox-group fr-checkbox-group--sm">
                    <input type="checkbox" id="repr-frise-filtre-${i}" checked>
                    <label class="fr-label" for="repr-frise-filtre-${i}">${echapper(String(ligne[Representations._colonnesFrise.date] ?? `Étape ${i + 1}`))}</label>
                </div>`).join("");
            filtres.querySelectorAll("input").forEach((c) => c.addEventListener("change", Representations.actualiserApercu));

            Representations.actualiserApercu();
        } catch (erreur) {
            afficherToast("Fichier illisible", erreur.message || String(erreur), "error");
        }
    },

    // Équivalent de color-mix(in srgb, hex1, hex2 poidsHex2*100%) mais
    // calculé en JS (voir actualiserApercu()) plutôt qu'en CSS.
    _melangerHex(hex1, hex2, poidsHex2) {
        const versRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
        const [r1, g1, b1] = versRgb(hex1);
        const [r2, g2, b2] = versRgb(hex2);
        const melanger = (a, b) => Math.round(a * (1 - poidsHex2) + b * poidsHex2);
        return `rgb(${melanger(r1, r2)}, ${melanger(g1, g2)}, ${melanger(b1, b2)})`;
    },

    // Couleurs posées en variables CSS locales au conteneur d'aperçu
    // (jamais globales, contrairement à PLUME) : évite tout effet de bord
    // sur le reste de l'interface SILLON si plusieurs représentations aux
    // palettes différentes étaient un jour affichées simultanément.
    actualiserApercu() {
        const conteneur = document.getElementById("representations-apercu");
        const type = document.getElementById("repr-type").value;
        const palette = PALETTES_DSFR[document.getElementById("repr-palette").value] || PALETTES_DSFR.marianne;
        conteneur.style.setProperty("--theme-main", palette.main);
        conteneur.style.setProperty("--theme-sun", palette.sun);
        conteneur.style.setProperty("--theme-bg", palette.bg);
        // Mélange précalculé ici plutôt qu'avec color-mix() en CSS :
        // html2canvas 1.4.1 ne sait pas parser cette fonction et fait
        // échouer le téléchargement PNG du Tableau (constaté en pratique).
        conteneur.style.setProperty("--theme-sun-80", Representations._melangerHex(palette.sun, "#ffffff", 0.2));

        if (type === "exergue") conteneur.innerHTML = Representations._rendreExergue();
        else if (type === "chiffre") conteneur.innerHTML = Representations._rendreChiffre();
        else if (type === "citation") conteneur.innerHTML = Representations._rendreCitation();
        else if (type === "tableau") conteneur.innerHTML = Representations._rendreTableau();
        else if (type === "frise") conteneur.innerHTML = Representations._rendreFrise();
    },

    // Fidèle à insertCallout() de PLUME (components.js) - classe DSFR
    // officielle .fr-callout, style porté dans styles.css.
    _rendreExergue() {
        const titre = document.getElementById("repr-exergue-titre").value;
        const texte = document.getElementById("repr-exergue-texte").value;
        return `<div class="fr-callout"><h3 class="fr-callout__title">${echapper(titre)}</h3><p class="fr-callout__text">${echapper(texte)}</p></div>`;
    },

    // Fidèle à insertChiffreCle() de PLUME - tout le style est inline dans
    // le bloc lui-même côté PLUME, reproduit tel quel ici (pas de règle
    // dédiée dans styles.css).
    _rendreChiffre() {
        const valeur = document.getElementById("repr-chiffre-valeur").value;
        const texte = document.getElementById("repr-chiffre-texte").value;
        return `
            <div class="plume-chiffre" style="display:flex; align-items:center; gap:1.5rem; padding:1.5rem; background-color:var(--theme-bg); border-radius:4px; border-left:4px solid var(--theme-sun);">
                <div style="font-size:3.5rem; font-weight:800; color:var(--theme-sun); line-height:1; min-width:max-content;">${echapper(valeur)}</div>
                <div style="font-size:1.1rem; font-weight:500; color:#1e1e1e; line-height:1.4;"><p style="margin:0;">${echapper(texte)}</p></div>
            </div>`;
    },

    // Fidèle à renderPreview() de insertCitation() (PLUME) - classe custom
    // .plume-citation + <blockquote>, style porté dans styles.css.
    _rendreCitation() {
        const texte = document.getElementById("repr-citation-texte").value;
        const auteur = document.getElementById("repr-citation-auteur").value;
        const fonction = document.getElementById("repr-citation-fonction").value;
        const stylePhoto = document.getElementById("repr-citation-photo").value;
        const avecPhoto = stylePhoto !== "none";
        const photoADroite = stylePhoto === "right";

        const blocTexte = `
            <blockquote class="plume-citation-bloc${photoADroite ? " plume-citation-bloc--droite" : ""}">
                <p>« ${echapper(texte)} »</p>
                <footer>— ${echapper(auteur)}, <span>${echapper(fonction)}</span></footer>
            </blockquote>`;

        if (!avecPhoto) return `<div class="plume-citation">${blocTexte}</div>`;

        const img = `<img src="${Representations._photoCitation || Representations._avatarParDefaut}" alt="Portrait de ${echapper(auteur)}" class="plume-citation-photo">`;
        return `<div class="plume-citation plume-citation--avec-photo">${photoADroite ? blocTexte + img : img + blocTexte}</div>`;
    },

    // Fidèle à la structure générée par insertTable() de PLUME - classe
    // DSFR officielle .fr-table, style porté dans styles.css. <caption>
    // ajoutée (RGAA §5.6/§5.7, absente de la version PLUME) : cohérent avec
    // l'audit accessibilité déjà mené sur SILLON.
    _rendreTableau() {
        const entete = document.getElementById("repr-tableau-entete").value;
        const enteteColonnes = entete === "colonnes" || entete === "colonnes-lignes";
        const enteteLignes = entete === "lignes" || entete === "colonnes-lignes";
        const valeurs = Representations._valeursTableau;

        const rangees = valeurs.map((ligne, i) => {
            const cellules = ligne.map((val, j) => {
                if (i === 0 && enteteColonnes) return `<th scope="col">${echapper(val)}</th>`;
                if (j === 0 && enteteLignes) return `<th scope="row">${echapper(val)}</th>`;
                return `<td>${echapper(val)}</td>`;
            }).join("");
            return `<tr>${cellules}</tr>`;
        });

        const corps = enteteColonnes ? rangees.slice(1) : rangees;
        const theadHtml = enteteColonnes ? `<thead>${rangees[0]}</thead>` : "";
        return `
            <div class="fr-table">
                <table>
                    <caption class="fr-sr-only">Tableau</caption>
                    ${theadHtml}
                    <tbody>${corps.join("")}</tbody>
                </table>
            </div>`;
    },

    // Fidèle à buildTimelineHTML() de PLUME - classes custom
    // .plume-timeline-*, style porté dans styles.css (ligne continue en
    // pseudo-élément, pastilles). Pas de liste accessible cachée façon
    // buildAccessibleTimelineList() de PLUME : elle y sert à rendre
    // accessible une image déjà insérée dans un document ; ici, l'aperçu
    // reste du HTML natif accessible tant qu'il n'est pas téléchargé (même
    // logique que Carto/Diagrammes, sans alternative texte pour le PNG
    // téléchargé).
    _rendreFrise() {
        if (!Representations._donneesFrise) {
            return '<p class="fr-text--sm fr-text--disabled">Importez un fichier CSV pour générer la frise.</p>';
        }
        const titre = document.getElementById("repr-frise-titre").value;
        const orientation = document.getElementById("repr-frise-orientation").value;
        const { date: colDate, titre: colTitre, description: colDesc } = Representations._colonnesFrise;

        const indices = [...document.querySelectorAll("#repr-frise-filtres input:checked")]
            .map((c) => Number(c.id.replace("repr-frise-filtre-", "")));
        const donnees = indices.map((i) => Representations._donneesFrise[i]);
        if (donnees.length === 0) return '<p class="fr-text--sm fr-text--disabled">Aucune étape sélectionnée.</p>';

        const classeListe = orientation === "horizontal" ? "plume-timeline-horizontal" : "plume-timeline-vertical";
        const items = donnees.map((ligne) => `
            <li>
                <strong class="plume-timeline-title">${echapper(String(ligne[colDate] ?? ""))}</strong>
                <div class="plume-timeline-event">${echapper(String(ligne[colTitre] ?? ""))}</div>
                ${colDesc && ligne[colDesc] ? `<div class="plume-timeline-desc">${echapper(String(ligne[colDesc]))}</div>` : ""}
            </li>`).join("");
        const titreHtml = titre ? `<h3 class="plume-timeline-titre-general">${echapper(titre)}</h3>` : "";
        return `<div>${titreHtml}<ul class="${classeListe}">${items}</ul></div>`;
    },

    // Même motif exact que Carto.telechargerPng()/Diagrammes.telecharger().
    async telechargerImage() {
        const conteneur = document.getElementById("representations-apercu");
        if (!conteneur.firstElementChild) {
            afficherToast("Aucun contenu", "Renseignez les champs avant de télécharger.", "warning");
            return;
        }
        const type = document.getElementById("repr-type").value;
        const noms = { exergue: "mise-en-exergue", chiffre: "chiffre-cle", citation: "citation", tableau: "tableau", frise: "frise-chronologique" };

        // Capture du contenu réel (pas du conteneur d'aperçu lui-même : celui-ci
        // a un min-height:400px, index.html, pour garder une hauteur confortable
        // à l'écran même avec un contenu court comme le Tableau, ce qui ajoutait
        // un grand bandeau blanc dans l'image téléchargée). Largeur de
        // l'enveloppe figée à la largeur RÉELLEMENT mesurée avant tout
        // déplacement (et non "display:inline-block" livré à lui-même) :
        // reproduit fidèlement le rendu déjà visible à l'écran, qu'il occupe
        // toute la largeur du conteneur (Mise en exergue, Chiffre, Citation,
        // Frise) ou soit déjà ajusté à son contenu (Tableau, cf. styles.css)
        // - un display:inline-block sans largeur explicite recalcule sa
        // propre largeur une fois déplacé, ce qui rétrécit à tort un contenu
        // court comme "Exergue"/"Contenu important." au lieu de conserver la
        // pleine largeur affichée à l'écran (constaté en pratique). Une
        // enveloppe temporaire (jamais visible à l'écran) ajoute une marge
        // régulière de 10px autour, plutôt qu'un contenu collé aux bords de
        // l'image. Marge propre de .fr-table (margin-top:1rem/margin-
        // bottom:2.5rem, dsfr.min.css) neutralisée le temps de la capture :
        // sans padding sur le parent direct, ces marges se seraient
        // effondrées avec les bords de l'aperçu à l'écran (invisibles) - avec
        // le padding de l'enveloppe, elles s'ajoutent au lieu de se résorber
        // et gonflent l'image d'un grand vide (constaté en pratique, hauteur
        // presque doublée).
        const contenu = conteneur.firstElementChild;
        const largeurContenu = contenu.getBoundingClientRect().width;
        const margeOriginale = contenu.style.margin;
        const enveloppe = document.createElement("div");
        enveloppe.style.cssText = `width:${largeurContenu}px; box-sizing:content-box; padding:10px; background-color:#ffffff;`;
        contenu.replaceWith(enveloppe);
        contenu.style.margin = "0";
        enveloppe.appendChild(contenu);
        try {
            const canvas = await html2canvas(enveloppe, { scale: 2, backgroundColor: "#ffffff", useCORS: true, logging: false });
            const lien = document.createElement("a");
            lien.download = `${noms[type] || "representation"}.png`;
            lien.href = canvas.toDataURL("image/png");
            lien.click();
        } catch (erreur) {
            afficherToast("Erreur", "Impossible de générer l'image.", "error");
        } finally {
            contenu.style.margin = margeOriginale;
            enveloppe.replaceWith(contenu);
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
        Administration.chargerProxyDatagouv();
        Administration.chargerSmtp();
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
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-lock-unlock-line" onclick="Administration.reinitialiserMdp(this, '${u.email}')">Réinitialiser mdp</button>
                    <button class="fr-btn fr-btn--sm fr-btn--tertiary-no-outline fr-icon-${u.actif ? "close-circle-line" : "check-line"}" onclick="Administration.basculerActivation(this, '${u.email}', ${u.actif})">${u.actif ? "Désactiver" : "Réactiver"}</button>
                </td>
            </tr>`).join("");
    },

    async creerUtilisateur(evenement) {
        evenement.preventDefault();
        const restaurer = verrouillerBouton(evenement.submitter);
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
            await Administration.chargerUtilisateurs();
        } catch (erreur) {
            alert(erreur.message);
        } finally {
            restaurer();
        }
    },

    reinitialiserMdp(bouton, email) {
        const modale = document.getElementById("modal-reinitialiser-mdp");
        modale.dataset.email = email;
        document.getElementById("modal-reinitialiser-mdp-email").textContent = email;
        document.getElementById("modal-reinitialiser-mdp-valeur").value = "";
        Administration._masquerErreurMdp();
        Modales.ouvrir(modale, bouton);
    },

    // Retour DSFR inline (fr-input-group--error), jamais alert() : une
    // boîte de dialogue JS native bloque le fil d'exécution de la page
    // (gênant pour l'automatisation de tests, et une expérience utilisateur
    // dégradée par rapport au reste de la modale).
    _masquerErreurMdp() {
        document.getElementById("modal-reinitialiser-mdp-groupe").classList.remove("fr-input-group--error");
        const erreur = document.getElementById("modal-reinitialiser-mdp-erreur");
        erreur.hidden = true;
        erreur.textContent = "";
    },

    _afficherErreurMdp(message) {
        document.getElementById("modal-reinitialiser-mdp-groupe").classList.add("fr-input-group--error");
        const erreur = document.getElementById("modal-reinitialiser-mdp-erreur");
        erreur.hidden = false;
        erreur.textContent = message;
    },

    async confirmerReinitialisationMdp() {
        const email = document.getElementById("modal-reinitialiser-mdp").dataset.email;
        const champ = document.getElementById("modal-reinitialiser-mdp-valeur");
        if (champ.value.length < 12) return Administration._afficherErreurMdp("Le mot de passe doit comporter au moins 12 caractères.");
        Administration._masquerErreurMdp();

        const bouton = document.getElementById("modal-reinitialiser-mdp-bouton");
        const restaurer = verrouillerBouton(bouton);
        try {
            await appelJson("/api/rpc/reinitialiser_mdp", { method: "POST", body: JSON.stringify({ _email: email, _nouveau_mdp: champ.value }) });
            Modales.fermer(document.getElementById("modal-reinitialiser-mdp"));
            afficherToast("Réinitialisé", `Mot de passe de ${email} réinitialisé.`, "success");
        } catch (erreur) {
            Administration._afficherErreurMdp(erreur.message);
        } finally {
            restaurer();
        }
    },

    async basculerActivation(bouton, email, actifActuellement) {
        // Absence de try/catch constatée en pratique (§5.6) : un échec réseau
        // ou un refus serveur ne se voyait jusqu'ici d'aucune façon, le
        // bouton restait affiché tel quel sans aucun retour à l'administrateur.
        const fonction = actifActuellement ? "desactiver_utilisateur" : "reactiver_utilisateur";
        const restaurer = verrouillerBouton(bouton);
        try {
            await appelJson(`/api/rpc/${fonction}`, { method: "POST", body: JSON.stringify({ _email: email }) });
            await Administration.chargerUtilisateurs();
        } catch (erreur) {
            restaurer();
            alert(erreur.message);
        }
    },

    async chargerQuotas() {
        const parametres = await appelJson("/api/parametres?order=cle.asc").catch(() => []);
        document.getElementById("conteneur-quotas").innerHTML = parametres.map((p) => `
            <div class="fr-input-group fr-input-group--sm" style="display:inline-block; margin-right:1rem;">
                <label class="fr-label" for="quota-${p.cle}">${echapper(p.cle)}</label>
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

    // Champ séparé de la boucle générique des quotas ci-dessus (pour porter
    // le bouton de test) : "datagouv_proxy_url" continue de toute façon à
    // apparaître aussi, automatiquement, dans le tableau générique - sans
    // conséquence, la modification y est équivalente (même endpoint).
    async chargerProxyDatagouv() {
        const parametres = await appelJson("/api/parametres?cle=eq.datagouv_proxy_url").catch(() => []);
        document.getElementById("admin-proxy-datagouv").value = parametres[0]?.valeur || "";
    },

    async enregistrerProxyDatagouv() {
        const valeur = document.getElementById("admin-proxy-datagouv").value.trim();
        await appelJson("/api/parametres?cle=eq.datagouv_proxy_url", {
            method: "PATCH",
            body: JSON.stringify({ valeur }),
        }).catch((erreur) => alert(erreur.message));
    },

    // Champs dédiés du même principe que le proxy data.gouv.fr ci-dessus :
    // smtp_hote/smtp_port/smtp_expediteur continuent aussi d'apparaître
    // dans le tableau générique des quotas, sans conséquence (même
    // endpoint /api/parametres).
    async chargerSmtp() {
        const parametres = await appelJson(
            "/api/parametres?cle=in.(smtp_hote,smtp_port,smtp_expediteur)"
        ).catch(() => []);
        const valeur = (cle, defaut) => parametres.find((p) => p.cle === cle)?.valeur ?? defaut;
        document.getElementById("admin-smtp-hote").value = valeur("smtp_hote", "");
        document.getElementById("admin-smtp-port").value = valeur("smtp_port", "");
        document.getElementById("admin-smtp-expediteur").value = valeur("smtp_expediteur", "");
    },

    async enregistrerSmtp() {
        const champs = {
            smtp_hote: document.getElementById("admin-smtp-hote").value.trim(),
            smtp_port: document.getElementById("admin-smtp-port").value.trim(),
            smtp_expediteur: document.getElementById("admin-smtp-expediteur").value.trim(),
        };
        try {
            await Promise.all(Object.entries(champs).map(([cle, valeur]) =>
                appelJson(`/api/parametres?cle=eq.${cle}`, { method: "PATCH", body: JSON.stringify({ valeur }) })
            ));
            afficherToast("Enregistré", "Réglage du serveur de mail sortant mis à jour.", "success");
        } catch (erreur) {
            alert(erreur.message);
        }
    },

    async testerSmtp() {
        const conteneur = document.getElementById("admin-smtp-resultat");
        conteneur.innerHTML = "Envoi en cours…";
        try {
            const resultat = await appelJson("/orchestrateur/mail/tester", {
                method: "POST",
                body: JSON.stringify({
                    smtp_hote: document.getElementById("admin-smtp-hote").value.trim(),
                    smtp_port: document.getElementById("admin-smtp-port").value.trim(),
                    smtp_expediteur: document.getElementById("admin-smtp-expediteur").value.trim(),
                }),
            });
            conteneur.innerHTML = resultat.ok
                ? `<div class="fr-alert fr-alert--success fr-alert--sm">Mail de test envoyé à ${echapper(Etat.utilisateur.email)}.</div>`
                : `<div class="fr-alert fr-alert--error fr-alert--sm">Échec : ${echapper(resultat.erreur)}</div>`;
        } catch (erreur) {
            conteneur.innerHTML = `<div class="fr-alert fr-alert--error fr-alert--sm">${echapper(erreur.message)}</div>`;
        }
    },

    async testerProxyDatagouv() {
        const conteneur = document.getElementById("admin-proxy-datagouv-resultat");
        conteneur.innerHTML = "Test en cours…";
        try {
            const resultat = await appelJson("/orchestrateur/datagouv/tester-proxy", {
                method: "POST",
                body: JSON.stringify({ proxy_url: document.getElementById("admin-proxy-datagouv").value.trim() }),
            });
            conteneur.innerHTML = resultat.ok
                ? `<div class="fr-alert fr-alert--success fr-alert--sm">Connexion réussie (${resultat.duree_ms} ms).</div>`
                : `<div class="fr-alert fr-alert--error fr-alert--sm">Échec : ${echapper(resultat.erreur)}</div>`;
        } catch (erreur) {
            afficherErreur(conteneur, erreur);
        }
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
