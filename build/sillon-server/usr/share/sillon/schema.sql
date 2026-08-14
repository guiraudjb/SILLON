-- =============================================================================
-- SCHEMA DU CATALOGUE APPLICATIF - SILLON
-- Base : sillon_catalog
-- Implemente le cahier des charges §3, §4.3, §6, §7.3, §8, §9, §11.
-- A deployer par un role disposant des privileges CREATEROLE/CREATEDB
-- (compte d'installation invoque depuis postinst, cf. §12.3).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. EXTENSIONS
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- hachage des mots de passe (bcrypt), HMAC des jetons
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- recherche approchee (§5.6 : recherche de compte)

-- -----------------------------------------------------------------------------
-- 1. SECRETS ET PRIMITIVES D'AUTHENTIFICATION (§4.3, §8.1, §8.11)
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE auth.secrets (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
-- Valeur generee aleatoirement a l'installation (§12.3), jamais commitee.
INSERT INTO auth.secrets (cle, valeur) VALUES ('jwt_secret', '__JWT_SECRET__');

CREATE OR REPLACE FUNCTION auth.url_encode(donnees bytea) RETURNS text AS $$
    SELECT translate(encode(donnees, 'base64'), E'+/=\n', '-_');
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION auth.sign_jwt(payload json, secret text) RETURNS text AS $$
DECLARE
    entete_b64  text;
    payload_b64 text;
    signature   text;
BEGIN
    entete_b64  := auth.url_encode(convert_to('{"alg":"HS256","typ":"JWT"}', 'utf8'));
    payload_b64 := auth.url_encode(convert_to(payload::text, 'utf8'));
    signature   := auth.url_encode(hmac(convert_to(entete_b64 || '.' || payload_b64, 'utf8'), convert_to(secret, 'utf8'), 'sha256'));
    RETURN entete_b64 || '.' || payload_b64 || '.' || signature;
END;
$$ LANGUAGE plpgsql;

-- Normalise un email en identifiant PostgreSQL valide pour nommer le role
-- personnel (§4.3). Le suffixe derive du hachage garantit l'unicite meme si
-- deux emails se reduisent a la meme partie locale une fois assainis.
CREATE OR REPLACE FUNCTION auth.nom_role_personnel(email text) RETURNS text AS $$
    SELECT 'u_' || left(regexp_replace(lower(split_part(email, '@', 1)), '[^a-z0-9_]', '_', 'g'), 40)
           || '_' || substr(md5(email), 1, 6);
$$ LANGUAGE sql IMMUTABLE;

-- -----------------------------------------------------------------------------
-- 2. TYPES (§3, §6, §9)
-- -----------------------------------------------------------------------------
CREATE TYPE public.profil_utilisateur AS ENUM ('lecteur', 'agent', 'administrateur');
CREATE TYPE public.type_job          AS ENUM ('import_csv', 'requete_sql', 'script_python', 'script_r', 'creation_base', 'suppression_base');
CREATE TYPE public.statut_job        AS ENUM ('en_attente', 'en_cours', 'termine', 'erreur', 'annule');
CREATE TYPE public.jwt_token         AS (token text);

-- -----------------------------------------------------------------------------
-- 3. TABLES DU CATALOGUE (§6)
-- -----------------------------------------------------------------------------

CREATE TABLE public.utilisateurs (
    id                SERIAL PRIMARY KEY,
    email             TEXT UNIQUE NOT NULL,
    mot_de_passe_hash TEXT NOT NULL,
    nom_complet       TEXT NOT NULL,
    profil            public.profil_utilisateur NOT NULL DEFAULT 'lecteur',
    role_pg           TEXT UNIQUE NOT NULL,
    actif             BOOLEAN NOT NULL DEFAULT true,
    date_creation     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.bases (
    id                SERIAL PRIMARY KEY,
    nom_pg            TEXT UNIQUE NOT NULL,
    proprietaire_id   INTEGER NOT NULL REFERENCES public.utilisateurs(id),
    date_creation     TIMESTAMPTZ NOT NULL DEFAULT now(),
    taille_estimee_mo NUMERIC DEFAULT 0
);
-- Une seule base par agent (§3, choix retenu au cahier des charges).
CREATE UNIQUE INDEX idx_bases_un_proprietaire ON public.bases(proprietaire_id);

CREATE TABLE public.partages (
    id               SERIAL PRIMARY KEY,
    base_id          INTEGER NOT NULL REFERENCES public.bases(id) ON DELETE CASCADE,
    beneficiaire_id  INTEGER NOT NULL REFERENCES public.utilisateurs(id),
    accorde_par_id   INTEGER NOT NULL REFERENCES public.utilisateurs(id),
    autorise_scripts BOOLEAN NOT NULL DEFAULT false,
    date_octroi      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (base_id, beneficiaire_id)
);

CREATE TABLE public.jobs (
    id              SERIAL PRIMARY KEY,
    utilisateur_id  INTEGER NOT NULL REFERENCES public.utilisateurs(id),
    type            public.type_job NOT NULL,
    statut          public.statut_job NOT NULL DEFAULT 'en_attente',
    -- ON DELETE SET NULL (constaté en pratique, §5.2/§9) : sans ça, la
    -- suppression d'une base échoue systématiquement dès qu'un job lui a
    -- fait référence (import, requête longue, ou la suppression elle-même
    -- une fois en cours) - retirer_base() ne peut alors jamais aboutir.
    -- L'historique du job (§5.5, §8.12) est conservé, seule la référence
    -- à une base désormais inexistante est effacée.
    base_id         INTEGER REFERENCES public.bases(id) ON DELETE SET NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    chemin_resultat TEXT,
    date_creation   TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_debut      TIMESTAMPTZ,
    date_fin        TIMESTAMPTZ,
    -- message_erreur : détail technique brut (exception Postgres, code
    -- retour...), pour investigation. message_utilisateur : reformulation
    -- compréhensible affichée en avant côté interface (§5.5) - distincts
    -- pour ne jamais exposer un message Postgres brut en première lecture.
    message_erreur     TEXT,
    message_utilisateur TEXT
);
CREATE INDEX idx_jobs_utilisateur ON public.jobs(utilisateur_id);
CREATE INDEX idx_jobs_statut ON public.jobs(statut);

CREATE TABLE public.audit_logs (
    id          SERIAL PRIMARY KEY,
    date_action TIMESTAMPTZ NOT NULL DEFAULT now(),
    utilisateur TEXT,
    action      TEXT NOT NULL,
    cible       TEXT,
    details     TEXT
);
CREATE INDEX idx_audit_logs_utilisateur ON public.audit_logs(utilisateur);
CREATE INDEX idx_audit_logs_date ON public.audit_logs(date_action);

CREATE TABLE public.parametres (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

-- Recherche approchee sur le panneau d'administration (§5.6).
CREATE INDEX idx_utilisateurs_recherche_trgm
    ON public.utilisateurs USING gin ((email || ' ' || nom_complet) gin_trgm_ops);

-- Quotas et reglages par defaut (§7.3, §11).
INSERT INTO public.parametres (cle, valeur) VALUES
    ('duree_max_job_minutes',            '30'),
    ('cpu_max_conteneur_vcpu',           '2'),
    ('ram_max_conteneur_mo',             '4096'),
    ('taille_max_csv_mo',                '2048'),
    ('jobs_simultanes_par_utilisateur',  '1'),
    ('quota_disque_base_mo',             '20480'),
    ('work_mem_defaut_mo',               '64'),
    -- Mémoire de travail dédiée à la construction des index (CREATE INDEX,
    -- appelé automatiquement à chaque import CSV, §7.4) - distincte de
    -- work_mem (tri/hash des requêtes) : une valeur trop basse (64 Mo,
    -- valeur d'installation par défaut de PostgreSQL) ralentit nettement
    -- la construction des index GIN trigram sur les colonnes Texte, en
    -- particulier pour un import volumineux - constaté en pratique sur un
    -- import de plusieurs dizaines de millions de lignes.
    ('maintenance_work_mem_defaut_mo',   '256'),
    ('connexions_max_par_utilisateur',   '5'),
    -- Seuil en-deca duquel un import CSV est charge immediatement plutot
    -- que differe par la file d'attente (§5.1, etape 7) ; distinct de
    -- taille_max_csv_mo qui est la limite absolue au-dela de laquelle
    -- l'import est refuse.
    ('seuil_import_synchrone_mo',        '10'),
    ('taille_max_script_mo',             '10');

-- -----------------------------------------------------------------------------
-- 4. ROLES POSTGRESQL (§3, §4.3, §8.3)
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    -- Role utilise par l'API de requetage (PostgREST) pour basculer, via
    -- "SET ROLE", vers le role personnel indique par le jeton (§4.3).
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sillon_service') THEN
        CREATE ROLE sillon_service WITH LOGIN PASSWORD '__SERVICE_PASS__';
    ELSE
        ALTER ROLE sillon_service WITH PASSWORD '__SERVICE_PASS__';
    END IF;

    -- Role utilise par l'orchestrateur et le travailleur de la file d'attente
    -- (meme niveau de confiance, deux processus systeme distincts - §4.2,
    -- §12.2). CREATEDB pour les creations/suppressions de base mediees (§4.4).
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sillon_orchestrateur') THEN
        CREATE ROLE sillon_orchestrateur WITH LOGIN CREATEDB PASSWORD '__ORCHESTRATEUR_PASS__';
    ELSE
        ALTER ROLE sillon_orchestrateur WITH CREATEDB PASSWORD '__ORCHESTRATEUR_PASS__';
    END IF;

    -- Roles "gabarits" de profil : portent les droits communs a chaque profil.
    -- Chaque role personnel devient membre du gabarit correspondant a la
    -- creation de son compte (§3, §8.3).
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'lecteur') THEN CREATE ROLE lecteur NOLOGIN; END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'agent') THEN CREATE ROLE agent NOLOGIN; END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'administrateur') THEN CREATE ROLE administrateur NOLOGIN; END IF;
END $$;

GRANT USAGE ON SCHEMA public TO sillon_service, sillon_orchestrateur, lecteur, agent, administrateur;

-- -----------------------------------------------------------------------------
-- 5. GESTION DES COMPTES ET DES ROLES PERSONNELS (§3, §4.3, §5.6)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.creer_utilisateur(_email TEXT, _password TEXT, _nom_complet TEXT, _profil public.profil_utilisateur)
RETURNS void AS $$
DECLARE
    _role_pg        TEXT;
    _work_mem_mo    TEXT;
    _maintenance_mo TEXT;
    _connexions_max INTEGER;
BEGIN
    _role_pg := auth.nom_role_personnel(_email);

    SELECT valeur INTO _work_mem_mo FROM public.parametres WHERE cle = 'work_mem_defaut_mo';
    SELECT valeur INTO _maintenance_mo FROM public.parametres WHERE cle = 'maintenance_work_mem_defaut_mo';
    SELECT valeur::INTEGER INTO _connexions_max FROM public.parametres WHERE cle = 'connexions_max_par_utilisateur';

    -- 1. Role PostgreSQL personnel : ne sert qu'a porter des permissions,
    --    jamais de connexion directe (§4.3). Limites de charge par role (§7.3).
    -- work_mem stocke en kilo-octets, SANS suffixe d'unite : PostgREST
    -- reapplique cette config a chaque "SET ROLE" (simulation d'une vraie
    -- connexion) et le fait en minuscules ("64mb"), que le parseur d'unite
    -- de PostgreSQL rejette ("MB" attendu en majuscules) - constate en
    -- pratique. Un nombre nu (kB par defaut pour work_mem) contourne le
    -- probleme sans dependre de la casse. Meme raisonnement pour
    -- maintenance_work_mem (construction des index a l'import, §7.4).
    EXECUTE format('CREATE ROLE %I NOLOGIN CONNECTION LIMIT %s', _role_pg, _connexions_max);
    EXECUTE format('ALTER ROLE %I SET work_mem = %L', _role_pg, (_work_mem_mo::integer * 1024)::text);
    EXECUTE format('ALTER ROLE %I SET maintenance_work_mem = %L', _role_pg, (_maintenance_mo::integer * 1024)::text);

    -- 2. Rattachement aux roles de service (bascule "SET ROLE", §4.3) et au
    --    gabarit de profil (§8.3).
    EXECUTE format('GRANT %I TO sillon_service', _role_pg);
    EXECUTE format('GRANT %I TO sillon_orchestrateur', _role_pg);
    EXECUTE format('GRANT %I TO %I', _profil::text, _role_pg);

    -- 3. Enregistrement dans le catalogue.
    INSERT INTO public.utilisateurs (email, mot_de_passe_hash, nom_complet, profil, role_pg)
    VALUES (_email, crypt(_password, gen_salt('bf')), _nom_complet, _profil, _role_pg);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.creer_utilisateur(text, text, text, public.profil_utilisateur) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.creer_utilisateur(text, text, text, public.profil_utilisateur) TO administrateur;


CREATE OR REPLACE FUNCTION public.reinitialiser_mdp(_email TEXT, _nouveau_mdp TEXT) RETURNS void AS $$
BEGIN
    UPDATE public.utilisateurs SET mot_de_passe_hash = crypt(_nouveau_mdp, gen_salt('bf')) WHERE email = _email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.reinitialiser_mdp(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.reinitialiser_mdp(text, text) TO administrateur;


-- Desactivation / reactivation : revoque ou restaure l'appartenance du role
-- personnel aux roles de service. Le jeton d'un utilisateur desactive devient
-- inutilisable des la requete suivante, meme s'il n'est pas expire (§8.2) :
-- ni l'API de requetage ni l'orchestrateur ne peuvent plus executer
-- "SET ROLE" vers un role dont ils ne sont plus membres.
CREATE OR REPLACE FUNCTION public.desactiver_utilisateur(_email TEXT) RETURNS void AS $$
DECLARE
    _role_pg TEXT;
BEGIN
    SELECT role_pg INTO _role_pg FROM public.utilisateurs WHERE email = _email;
    IF NOT FOUND THEN RAISE EXCEPTION 'Utilisateur introuvable : %', _email; END IF;

    EXECUTE format('REVOKE %I FROM sillon_service', _role_pg);
    EXECUTE format('REVOKE %I FROM sillon_orchestrateur', _role_pg);
    UPDATE public.utilisateurs SET actif = false WHERE email = _email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.desactiver_utilisateur(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.desactiver_utilisateur(text) TO administrateur;


CREATE OR REPLACE FUNCTION public.reactiver_utilisateur(_email TEXT) RETURNS void AS $$
DECLARE
    _role_pg TEXT;
BEGIN
    SELECT role_pg INTO _role_pg FROM public.utilisateurs WHERE email = _email;
    IF NOT FOUND THEN RAISE EXCEPTION 'Utilisateur introuvable : %', _email; END IF;

    EXECUTE format('GRANT %I TO sillon_service', _role_pg);
    EXECUTE format('GRANT %I TO sillon_orchestrateur', _role_pg);
    UPDATE public.utilisateurs SET actif = true WHERE email = _email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.reactiver_utilisateur(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.reactiver_utilisateur(text) TO administrateur;


-- Identifiants ephemeres pour l'execution de scripts (§7.7, §8.7).
-- Les roles personnels restent NOLOGIN en permanence (§4.3) : un script
-- s'execute dans un conteneur, processus totalement exterieur a l'API de
-- requetage, qui n'a donc aucun moyen de basculer via "SET ROLE" comme le
-- fait PostgREST. Le temps de la seule execution du conteneur, ces deux
-- fonctions ouvrent puis referment une fenetre de connexion directe,
-- plutot que d'accorder a sillon_orchestrateur un CREATEROLE general qui
-- lui permettrait de modifier n'importe quel role sans controle.
CREATE OR REPLACE FUNCTION public.preparer_execution_script(_role_pg TEXT) RETURNS TEXT AS $$
DECLARE
    _mot_de_passe TEXT;
BEGIN
    _mot_de_passe := encode(gen_random_bytes(24), 'base64');
    EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', _role_pg, _mot_de_passe);
    RETURN _mot_de_passe;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.preparer_execution_script(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.preparer_execution_script(text) TO sillon_orchestrateur;


CREATE OR REPLACE FUNCTION public.cloturer_execution_script(_role_pg TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER ROLE %I WITH NOLOGIN PASSWORD NULL', _role_pg);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.cloturer_execution_script(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.cloturer_execution_script(text) TO sillon_orchestrateur;

-- -----------------------------------------------------------------------------
-- 6. AUTHENTIFICATION (§4.3, §8.1, §8.2)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.login(email TEXT, password TEXT) RETURNS public.jwt_token AS $$
DECLARE
    _utilisateur public.utilisateurs%ROWTYPE;
    _jeton       TEXT;
    _resultat    public.jwt_token;
BEGIN
    SELECT * INTO _utilisateur FROM public.utilisateurs u
        WHERE u.email = login.email AND u.mot_de_passe_hash = crypt(login.password, u.mot_de_passe_hash);

    IF NOT FOUND OR NOT _utilisateur.actif THEN
        RAISE EXCEPTION 'Identifiants incorrects';
    END IF;

    _jeton := auth.sign_jwt(
        json_build_object(
            'role',    _utilisateur.role_pg,
            'profil',  _utilisateur.profil,
            'user_id', _utilisateur.id,
            'email',   _utilisateur.email,
            'exp',     extract(epoch from now())::integer + 28800
        ),
        (SELECT valeur FROM auth.secrets WHERE cle = 'jwt_secret')
    );

    PERFORM set_config('response.headers',
        '[{"Set-Cookie": "sillon_token=' || _jeton || '; Path=/; HttpOnly; Secure; SameSite=Strict"}]', true);

    _resultat.token := 'Session demarree';
    RETURN _resultat;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.login(text, text) TO sillon_service;


CREATE OR REPLACE FUNCTION public.logout() RETURNS void AS $$
BEGIN
    PERFORM set_config('response.headers',
        '[{"Set-Cookie": "sillon_token=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0"}]', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.logout() TO lecteur, agent, administrateur;


-- Identite de l'appelant courant, telle que posee par l'API de requetage a
-- partir du jeton (§4.3). Utilisee par les vues et fonctions ci-dessous pour
-- borner chaque acces a "ce qui concerne l'appelant" (§8.4).
CREATE OR REPLACE FUNCTION public._id_courant() RETURNS INTEGER AS $$
    SELECT (current_setting('request.jwt.claims', true)::json ->> 'user_id')::INTEGER;
$$ LANGUAGE sql STABLE;

GRANT EXECUTE ON FUNCTION public._id_courant() TO sillon_service, lecteur, agent, administrateur;


CREATE OR REPLACE FUNCTION public.me() RETURNS json AS $$
DECLARE
    _email  TEXT;
    _profil TEXT;
    _actif  BOOLEAN;
BEGIN
    _email := current_setting('request.jwt.claims', true)::json ->> 'email';
    IF _email IS NULL THEN RETURN NULL; END IF;

    SELECT profil::text, actif INTO _profil, _actif FROM public.utilisateurs WHERE email = _email;

    -- Verification independante de la duree de vie du jeton (§8.2) : un
    -- compte desactive ne doit jamais se voir confirme comme authentifie,
    -- meme dans l'hypothese ou son jeton resterait valide.
    IF NOT FOUND OR NOT _actif THEN RETURN NULL; END IF;

    RETURN json_build_object('email', _email, 'profil', _profil);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.me() TO sillon_service, lecteur, agent, administrateur;

-- -----------------------------------------------------------------------------
-- 7. BASES ET PARTAGES (§4.4, §5.2, §7.2)
-- -----------------------------------------------------------------------------

-- "Mes bases" : celle que je possede, et celles qui m'ont ete partagees (§5.2).
CREATE OR REPLACE VIEW public.vue_mes_bases AS
SELECT
    b.id, b.nom_pg, b.date_creation, b.taille_estimee_mo,
    (b.proprietaire_id = public._id_courant()) AS je_suis_proprietaire,
    up.email AS proprietaire_email,
    p.autorise_scripts
FROM public.bases b
JOIN public.utilisateurs up ON up.id = b.proprietaire_id
LEFT JOIN public.partages p ON p.base_id = b.id AND p.beneficiaire_id = public._id_courant()
WHERE b.proprietaire_id = public._id_courant() OR p.beneficiaire_id = public._id_courant();

GRANT SELECT ON public.vue_mes_bases TO agent, lecteur, administrateur;


-- Liste des partages accordes par l'appelant sur ses propres bases (§5.2,
-- onglet Bases - "gerer le partage" suppose de voir a qui l'acces a deja
-- ete accorde, pas seulement d'en accorder de nouveaux).
CREATE OR REPLACE VIEW public.vue_partages_de_mes_bases AS
SELECT p.id, p.base_id, u.email AS beneficiaire_email, p.autorise_scripts, p.date_octroi
FROM public.partages p
JOIN public.bases b ON b.id = p.base_id
JOIN public.utilisateurs u ON u.id = p.beneficiaire_id
WHERE b.proprietaire_id = public._id_courant();

GRANT SELECT ON public.vue_partages_de_mes_bases TO agent;


CREATE OR REPLACE FUNCTION public.partager_base(_base_id INTEGER, _email_beneficiaire TEXT, _autorise_scripts BOOLEAN DEFAULT false)
RETURNS void AS $$
DECLARE
    _beneficiaire_id INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.bases WHERE id = _base_id AND proprietaire_id = public._id_courant()) THEN
        RAISE EXCEPTION 'Seul le proprietaire de la base peut la partager';
    END IF;

    SELECT id INTO _beneficiaire_id FROM public.utilisateurs WHERE email = _email_beneficiaire AND actif;
    IF NOT FOUND THEN RAISE EXCEPTION 'Utilisateur beneficiaire introuvable ou inactif'; END IF;

    INSERT INTO public.partages (base_id, beneficiaire_id, accorde_par_id, autorise_scripts)
    VALUES (_base_id, _beneficiaire_id, public._id_courant(), _autorise_scripts)
    ON CONFLICT (base_id, beneficiaire_id) DO UPDATE SET autorise_scripts = EXCLUDED.autorise_scripts;

    -- Le droit de connexion a la base cible se pose depuis le catalogue, car
    -- CONNECT est un privilege de niveau cluster (§7.4, catalogue partage).
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO %I',
        (SELECT nom_pg FROM public.bases WHERE id = _base_id),
        (SELECT role_pg FROM public.utilisateurs WHERE id = _beneficiaire_id));

    -- Les GRANT USAGE/SELECT et ALTER DEFAULT PRIVILEGES sur le schema public
    -- de la base cible (tables presentes ET futures, §5.2) exigent une
    -- connexion a cette base precise : ils sont executes par l'orchestrateur,
    -- avec le role personnel du proprietaire (§4.4), a la suite de cet appel.
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- REVOKE FROM PUBLIC (constaté en pratique, §8.4) : PostgreSQL accorde
-- EXECUTE à PUBLIC par défaut à la création d'une fonction - sans ce
-- REVOKE explicite, le GRANT ci-dessous ne restreint rien du tout, malgré
-- les apparences. Manquait sur toutes les fonctions de cette section
-- (§4.4, §5.2, §9) jusqu'à ce que ce soit vérifié en conditions réelles :
-- un compte lecteur pouvait alors appeler enregistrer_base/retirer_base/
-- maj_statut_job directement (aucune ne vérifie l'appelant en interne,
-- contrairement à partager_base/revoquer_partage), au point de pouvoir
-- pointer le chemin_resultat de n'importe quel job vers un fichier
-- arbitraire du serveur puis le récupérer via /jobs/<id>/telecharger.
REVOKE EXECUTE ON FUNCTION public.partager_base(integer, text, boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.partager_base(integer, text, boolean) TO agent;


CREATE OR REPLACE FUNCTION public.revoquer_partage(_base_id INTEGER, _email_beneficiaire TEXT) RETURNS void AS $$
DECLARE
    _beneficiaire_id INTEGER;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM public.bases WHERE id = _base_id AND proprietaire_id = public._id_courant()) THEN
        RAISE EXCEPTION 'Seul le proprietaire de la base peut revoquer un partage';
    END IF;

    SELECT id INTO _beneficiaire_id FROM public.utilisateurs WHERE email = _email_beneficiaire;
    IF NOT FOUND THEN RAISE EXCEPTION 'Utilisateur beneficiaire introuvable'; END IF;

    DELETE FROM public.partages WHERE base_id = _base_id AND beneficiaire_id = _beneficiaire_id;

    EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM %I',
        (SELECT nom_pg FROM public.bases WHERE id = _base_id),
        (SELECT role_pg FROM public.utilisateurs WHERE id = _beneficiaire_id));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.revoquer_partage(integer, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.revoquer_partage(integer, text) TO agent;


-- Bascule "orchestrateur -> catalogue" : enregistrement d'une base une fois
-- le CREATE DATABASE physique effectue (§4.4), jamais l'inverse.
CREATE OR REPLACE FUNCTION public.enregistrer_base(_nom_pg TEXT, _proprietaire_id INTEGER) RETURNS INTEGER AS $$
DECLARE
    _id_base INTEGER;
BEGIN
    INSERT INTO public.bases (nom_pg, proprietaire_id) VALUES (_nom_pg, _proprietaire_id)
    RETURNING id INTO _id_base;
    RETURN _id_base;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.enregistrer_base(text, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.enregistrer_base(text, integer) TO sillon_orchestrateur;


CREATE OR REPLACE FUNCTION public.retirer_base(_base_id INTEGER) RETURNS void AS $$
BEGIN
    DELETE FROM public.bases WHERE id = _base_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.retirer_base(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.retirer_base(integer) TO sillon_orchestrateur;


CREATE OR REPLACE FUNCTION public.maj_taille_base(_base_id INTEGER, _taille_mo NUMERIC) RETURNS void AS $$
BEGIN
    UPDATE public.bases SET taille_estimee_mo = _taille_mo WHERE id = _base_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.maj_taille_base(integer, numeric) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.maj_taille_base(integer, numeric) TO sillon_orchestrateur;

-- -----------------------------------------------------------------------------
-- 7bis. HISTORIQUE ET REQUETES ENREGISTREES (§5.3)
-- -----------------------------------------------------------------------------
-- Distinct des jobs (§9) : une requête exécutée depuis l'onglet Travaux
-- s'exécute de façon synchrone (ou, pour les plus longues, comme job
-- "requete_sql" - cf. plus bas), mais dans les deux cas son historique est
-- propre à ce module, pas mélangé à la file d'attente des imports/scripts.

CREATE TABLE public.requetes_historique (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER NOT NULL REFERENCES public.utilisateurs(id),
    base_id        INTEGER REFERENCES public.bases(id) ON DELETE SET NULL,
    requete        TEXT NOT NULL,
    type           TEXT NOT NULL,
    succes         BOOLEAN NOT NULL,
    duree_ms       INTEGER,
    message_erreur TEXT,
    date_execution TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_requetes_historique_utilisateur ON public.requetes_historique(utilisateur_id, date_execution DESC);

CREATE OR REPLACE VIEW public.vue_mon_historique AS
SELECT id, base_id, requete, type, succes, duree_ms, message_erreur, date_execution
FROM public.requetes_historique
WHERE utilisateur_id = public._id_courant()
ORDER BY date_execution DESC
LIMIT 200;

GRANT SELECT ON public.vue_mon_historique TO agent, lecteur;


CREATE OR REPLACE FUNCTION public.enregistrer_historique(
    _base_id INTEGER, _requete TEXT, _type TEXT, _succes BOOLEAN, _duree_ms INTEGER, _message_erreur TEXT DEFAULT NULL
) RETURNS void AS $$
BEGIN
    INSERT INTO public.requetes_historique (utilisateur_id, base_id, requete, type, succes, duree_ms, message_erreur)
    VALUES (public._id_courant(), _base_id, _requete, _type, _succes, _duree_ms, _message_erreur);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.enregistrer_historique(integer, text, text, boolean, integer, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.enregistrer_historique(integer, text, text, boolean, integer, text) TO agent, lecteur;


CREATE TABLE public.requetes_enregistrees (
    id             SERIAL PRIMARY KEY,
    utilisateur_id INTEGER NOT NULL REFERENCES public.utilisateurs(id),
    nom            TEXT NOT NULL,
    requete        TEXT NOT NULL,
    date_creation  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (utilisateur_id, nom)
);

CREATE OR REPLACE VIEW public.vue_mes_requetes_enregistrees AS
SELECT id, nom, requete, date_creation
FROM public.requetes_enregistrees
WHERE utilisateur_id = public._id_courant()
ORDER BY nom;

GRANT SELECT ON public.vue_mes_requetes_enregistrees TO agent, lecteur;


-- ON CONFLICT ... DO UPDATE (plutôt qu'un simple INSERT) : enregistrer sous
-- un nom déjà utilisé remplace la requête associée, cohérent avec l'usage
-- attendu d'un "favori" nommé (§5.3) plutôt que de forcer l'utilisateur à
-- supprimer l'ancienne version avant d'en écrire une nouvelle du même nom.
CREATE OR REPLACE FUNCTION public.enregistrer_requete(_nom TEXT, _requete TEXT) RETURNS INTEGER AS $$
DECLARE
    _id INTEGER;
BEGIN
    INSERT INTO public.requetes_enregistrees (utilisateur_id, nom, requete)
    VALUES (public._id_courant(), _nom, _requete)
    ON CONFLICT (utilisateur_id, nom) DO UPDATE SET requete = EXCLUDED.requete
    RETURNING id INTO _id;
    RETURN _id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.enregistrer_requete(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.enregistrer_requete(text, text) TO agent, lecteur;


CREATE OR REPLACE FUNCTION public.supprimer_requete_enregistree(_id INTEGER) RETURNS void AS $$
BEGIN
    DELETE FROM public.requetes_enregistrees WHERE id = _id AND utilisateur_id = public._id_courant();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.supprimer_requete_enregistree(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.supprimer_requete_enregistree(integer) TO agent, lecteur;

-- -----------------------------------------------------------------------------
-- 8. FILE D'ATTENTE (§9, §5.5)
-- -----------------------------------------------------------------------------

-- Un seul travailleur à la fois par "groupe de file" (§9 : orchestrateur
-- pour creation_base/suppression_base/import_csv/requete_sql, sillon-worker
-- pour script_python/script_r, cf. TYPES_GERES de chacun) : la position
-- dans la file (§5.5) se compte donc au sein du même groupe uniquement, pas
-- tous types confondus.
CREATE OR REPLACE FUNCTION auth.groupe_file(_type public.type_job) RETURNS boolean AS $$
    SELECT _type = ANY(ARRAY['script_python', 'script_r']::public.type_job[]);
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE VIEW public.vue_mes_jobs AS
SELECT
    j.id, j.type, j.statut, j.base_id, j.date_creation, j.date_debut, j.date_fin,
    j.message_erreur, j.message_utilisateur, j.chemin_resultat,
    -- Nom du script déposé ou du fichier CSV importé (§5.5), jamais le
    -- reste de "payload" (chemin serveur, rôle PostgreSQL personnel...) -
    -- seule cette valeur a un sens à afficher à l'utilisateur.
    j.payload->>'nom_fichier' AS nom_fichier,
    CASE WHEN j.statut = 'en_attente' THEN (
        SELECT count(*) FROM public.jobs j2
        WHERE j2.statut IN ('en_attente', 'en_cours')
          AND auth.groupe_file(j2.type) = auth.groupe_file(j.type)
          AND j2.date_creation < j.date_creation
    ) END AS position_file
FROM public.jobs j
WHERE j.utilisateur_id = public._id_courant();

GRANT SELECT ON public.vue_mes_jobs TO agent, lecteur, administrateur;


CREATE OR REPLACE FUNCTION public.creer_job(_type public.type_job, _base_id INTEGER, _payload JSONB DEFAULT '{}'::jsonb)
RETURNS INTEGER AS $$
DECLARE
    _id_job         INTEGER;
    _max_simultanes INTEGER;
    _en_cours       INTEGER;
BEGIN
    SELECT valeur::INTEGER INTO _max_simultanes FROM public.parametres WHERE cle = 'jobs_simultanes_par_utilisateur';
    SELECT count(*) INTO _en_cours FROM public.jobs
        WHERE utilisateur_id = public._id_courant() AND statut IN ('en_attente', 'en_cours');

    IF _en_cours >= _max_simultanes THEN
        RAISE EXCEPTION 'Quota de jobs simultanes atteint (%). Voir §11.', _max_simultanes;
    END IF;

    INSERT INTO public.jobs (utilisateur_id, type, base_id, payload)
    VALUES (public._id_courant(), _type, _base_id, _payload)
    RETURNING id INTO _id_job;

    -- Reveil des travailleurs asynchrones en attente (§9).
    PERFORM pg_notify('sillon_jobs', _id_job::text);

    RETURN _id_job;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Agent uniquement (§3) : creer_job porte tous les traitements réservés à
-- l'agent (import CSV, création/suppression de base, scripts) - un lecteur
-- n'a légitimement besoin d'aucun d'entre eux, seulement d'interroger les
-- bases qui lui sont accessibles (via l'API de requêtage, pas cette
-- fonction). Un GRANT incluant "lecteur" ici viderait de son sens toute
-- restriction "Propriétaire uniquement" du §5.2 : un compte lecteur
-- pourrait alors devenir propriétaire d'une base en appelant directement
-- /orchestrateur/import/valider, malgré l'interdiction explicite du §3.
-- Le REVOKE FROM PUBLIC est indispensable (cf. note détaillée plus haut,
-- au premier REVOKE de cette section) : sans lui, ce GRANT ne restreint
-- rien du tout.
REVOKE EXECUTE ON FUNCTION public.creer_job(public.type_job, integer, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.creer_job(public.type_job, integer, jsonb) TO agent;


CREATE OR REPLACE FUNCTION public.annuler_job(_id_job INTEGER) RETURNS void AS $$
BEGIN
    -- date_fin (constaté en pratique) : "annule" est un statut terminal au
    -- même titre que "termine"/"erreur" (maj_statut_job le traite ainsi),
    -- mais ce chemin-ci ne passait pas par maj_statut_job et laissait
    -- date_fin NULL indéfiniment pour un job annulé.
    UPDATE public.jobs SET statut = 'annule', date_fin = now()
    WHERE id = _id_job AND utilisateur_id = public._id_courant() AND statut IN ('en_attente', 'en_cours');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.annuler_job(integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.annuler_job(integer) TO agent, lecteur;


CREATE OR REPLACE FUNCTION public.maj_statut_job(
    _id_job INTEGER, _statut public.statut_job, _chemin_resultat TEXT DEFAULT NULL,
    _message_erreur TEXT DEFAULT NULL, _message_utilisateur TEXT DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE public.jobs SET
        statut              = _statut,
        date_debut          = CASE WHEN _statut = 'en_cours' AND date_debut IS NULL THEN now() ELSE date_debut END,
        date_fin            = CASE WHEN _statut IN ('termine', 'erreur', 'annule') THEN now() ELSE date_fin END,
        chemin_resultat     = COALESCE(_chemin_resultat, chemin_resultat),
        message_erreur      = COALESCE(_message_erreur, message_erreur),
        message_utilisateur = COALESCE(_message_utilisateur, message_utilisateur)
    -- "AND statut <> 'annule'" (§5.5) : une annulation posée par
    -- l'utilisateur pendant qu'un job est "en_cours" (§9, traitement déjà
    -- entamé côté orchestrateur/worker) doit rester définitive - sans
    -- cette garde, la mise à jour finale du traitement en cours (déclenchée
    -- par le code qui ne sait pas encore que l'annulation a eu lieu)
    -- écrasait silencieusement "annule" par "termine"/"erreur", contraire
    -- au §5.5 ("annulation possible tant que le job est en attente ou en
    -- cours").
    WHERE id = _id_job AND statut <> 'annule';
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Le REVOKE FROM PUBLIC est particulièrement critique ici (§8.10) : sans
-- lui, n'importe quel compte authentifié peut faire pointer
-- chemin_resultat d'un job vers un chemin arbitraire du serveur, puis le
-- récupérer via /jobs/<id>/telecharger - démontré en conditions réelles.
REVOKE EXECUTE ON FUNCTION public.maj_statut_job(integer, public.statut_job, text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.maj_statut_job(integer, public.statut_job, text, text, text) TO sillon_orchestrateur;

-- -----------------------------------------------------------------------------
-- 9. JOURNALISATION IMMUABLE (§8.12)
-- -----------------------------------------------------------------------------

-- Un UPDATE sur le journal reussit sans effet : aucune modification
-- retroactive n'est possible, y compris par un compte administrateur.
CREATE RULE regle_audit_immuable AS ON UPDATE TO public.audit_logs DO INSTEAD NOTHING;

-- La suppression n'est possible que par le compte systeme (purge planifiee,
-- cf. etc/cron.d/sillon_purge_logs, executee en tant que role "postgres").
CREATE OR REPLACE FUNCTION public.proteger_audit_suppression() RETURNS TRIGGER AS $$
BEGIN
    IF current_user <> 'postgres' THEN
        RAISE EXCEPTION 'audit_logs : suppression non autorisee (utilisateur : %)', current_user;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trig_proteger_audit_suppression
    BEFORE DELETE ON public.audit_logs
    FOR EACH ROW EXECUTE FUNCTION public.proteger_audit_suppression();


CREATE OR REPLACE FUNCTION public.journaliser_action() RETURNS TRIGGER AS $$
DECLARE
    _utilisateur TEXT;
    _action      TEXT;
    _cible       TEXT;
    _ligne       JSONB;
BEGIN
    BEGIN
        _utilisateur := current_setting('request.jwt.claims', true)::json ->> 'email';
    EXCEPTION WHEN OTHERS THEN
        _utilisateur := NULL;
    END;
    IF _utilisateur IS NULL THEN _utilisateur := 'Systeme'; END IF;

    IF TG_OP = 'INSERT' THEN _action := 'CREATION';
    ELSIF TG_OP = 'UPDATE' THEN _action := 'MODIFICATION';
    ELSE _action := 'SUPPRESSION';
    END IF;

    -- Acces dynamique aux champs de NEW/OLD : une meme fonction trigger est
    -- partagee par plusieurs tables aux structures differentes, et
    -- PL/pgSQL resout statiquement tout champ nomme directement (NEW.xxx),
    -- y compris dans une branche CASE non retenue a l'execution.
    IF TG_OP = 'DELETE' THEN
        _ligne := to_jsonb(OLD);
    ELSE
        _ligne := to_jsonb(NEW);
    END IF;

    _cible := CASE TG_TABLE_NAME
        WHEN 'utilisateurs' THEN _ligne ->> 'email'
        WHEN 'bases'        THEN _ligne ->> 'nom_pg'
        WHEN 'partages'     THEN 'base #' || (_ligne ->> 'base_id')
        ELSE NULL
    END;

    INSERT INTO public.audit_logs (utilisateur, action, cible, details)
    VALUES (_utilisateur, _action, _cible, TG_TABLE_NAME || ' : ' || _action);

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER trig_audit_utilisateurs AFTER INSERT OR UPDATE OR DELETE ON public.utilisateurs FOR EACH ROW EXECUTE FUNCTION public.journaliser_action();
CREATE TRIGGER trig_audit_bases        AFTER INSERT OR UPDATE OR DELETE ON public.bases        FOR EACH ROW EXECUTE FUNCTION public.journaliser_action();
CREATE TRIGGER trig_audit_partages     AFTER INSERT OR UPDATE OR DELETE ON public.partages     FOR EACH ROW EXECUTE FUNCTION public.journaliser_action();

-- Journalisation manuelle (§8.12) : la création/suppression d'une table
-- (§5.2) se produit dans la base physique de l'agent, jamais dans
-- sillon_catalog - aucun trigger sur une table système ne peut donc la
-- capturer comme le fait journaliser_action() pour utilisateurs/bases/
-- partages. L'orchestrateur appelle cette fonction explicitement après
-- coup, une fois l'opération elle-même confirmée réussie.
CREATE OR REPLACE FUNCTION public.consigner_audit(_action TEXT, _cible TEXT, _details TEXT) RETURNS void AS $$
DECLARE
    _utilisateur TEXT;
BEGIN
    _utilisateur := current_setting('request.jwt.claims', true)::json ->> 'email';
    IF _utilisateur IS NULL THEN _utilisateur := 'Systeme'; END IF;
    INSERT INTO public.audit_logs (utilisateur, action, cible, details) VALUES (_utilisateur, _action, _cible, _details);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION public.consigner_audit(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.consigner_audit(text, text, text) TO agent;

-- -----------------------------------------------------------------------------
-- 10. DROITS D'ACCES AU CATALOGUE (§8.3, §8.4, §8.9)
-- -----------------------------------------------------------------------------
-- Le catalogue n'est jamais accessible en table brute par un profil non
-- administrateur : uniquement via les vues filtrees et les fonctions
-- ci-dessus, qui bornent chaque acces a "ce qui concerne l'appelant" (§8.4).

GRANT SELECT ON public.parametres TO lecteur, agent, administrateur;
GRANT UPDATE ON public.parametres TO administrateur;

-- L'administrateur seul a une vue complete du catalogue (panneau
-- d'administration, §5.6).
GRANT SELECT ON public.utilisateurs, public.bases, public.partages, public.jobs TO administrateur;
GRANT SELECT ON public.audit_logs TO administrateur;

-- La table utilisateurs et le journal d'audit ne doivent jamais etre lisibles
-- par un profil standard, meme via un heritage de droits involontaire (§8.9).
REVOKE ALL ON public.utilisateurs FROM PUBLIC, lecteur, agent;
REVOKE ALL ON public.audit_logs FROM PUBLIC, lecteur, agent;

-- L'orchestrateur a besoin, pour son propre compte (hors bascule "SET ROLE"
-- vers un role personnel), de lire ces tables afin de completer les
-- operations multi-bases qu'il est seul a pouvoir executer (§4.4) : retrouver
-- le nom physique d'une base ou l'email d'un utilisateur, lire les quotas,
-- et consommer la file d'attente ("FOR UPDATE SKIP LOCKED" exige UPDATE,
-- pas seulement SELECT).
GRANT SELECT ON public.parametres, public.utilisateurs, public.bases TO sillon_orchestrateur;
GRANT SELECT, UPDATE ON public.jobs TO sillon_orchestrateur;

-- -----------------------------------------------------------------------------
-- 11. COMPTE ADMINISTRATEUR INITIAL (§12.3)
-- -----------------------------------------------------------------------------
-- Execute par le compte d'installation (superutilisateur), qui n'est pas
-- soumis aux GRANT/REVOKE ci-dessus.
SELECT public.creer_utilisateur('__ADMIN_EMAIL__', '__ADMIN_PASS__', 'Administrateur', 'administrateur');
