"""
Génération du document PDF : Guide d'assistance — SILLON
Destiné aux équipes de support N1/N2/N3

Même style et même classe PDF que le générateur équivalent de mobiTrace
(TRACE/build/generate_guide_support_pdf.py) — gabarit repris à l'identique,
seul le contenu change.
"""
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from datetime import date

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

BLUE_DARK    = (0,   0,  145)
BLUE_MED     = (0,  91, 187)
BLUE_LIGHT   = (224, 232, 255)
GREEN_OK     = ( 24, 128,  56)
GREEN_LIGHT  = (220, 255, 220)
ORANGE_WARN  = (200, 110,  10)
ORANGE_LIGHT = (255, 245, 215)
RED_CRIT     = (180,  20,  20)
RED_LIGHT    = (255, 225, 225)
PURPLE       = (100,  50, 150)
PURPLE_LIGHT = (240, 225, 255)
GREY_LIGHT   = (246, 246, 246)
GREY_BORDER  = (204, 204, 204)
BLACK        = (  0,   0,   0)
WHITE        = (255, 255, 255)

MARGIN_L  = 18
MARGIN_R  = 18
PAGE_W    = 210
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

TODAY = date.today().strftime("%d/%m/%Y")


class PDF(FPDF):

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(MARGIN_L, 22, MARGIN_R)
        self.set_auto_page_break(auto=True, margin=18)
        self.add_font("Sans",  "",   FONT_DIR + "DejaVuSans.ttf")
        self.add_font("Sans",  "B",  FONT_DIR + "DejaVuSans-Bold.ttf")
        self.add_font("Sans",  "I",  FONT_DIR + "DejaVuSans-Oblique.ttf")
        self.add_font("Sans",  "BI", FONT_DIR + "DejaVuSans-BoldOblique.ttf")
        self.add_font("Mono",  "",   FONT_DIR + "DejaVuSansMono.ttf")
        self.add_font("Mono",  "B",  FONT_DIR + "DejaVuSansMono-Bold.ttf")

    def header(self):
        self.set_fill_color(*BLUE_DARK)
        self.rect(0, 0, PAGE_W, 13, "F")
        self.set_y(2)
        self.set_font("Sans", "B", 8.5)
        self.set_text_color(*WHITE)
        self.cell(0, 9, "SILLON — Guide d'assistance — Usage interne équipes support", align="C")
        self.set_text_color(*BLACK)
        self.set_y(20)

    def footer(self):
        self.set_y(-13)
        self.set_fill_color(*BLUE_DARK)
        self.rect(0, self.get_y(), PAGE_W, 14, "F")
        self.set_font("Sans", "I", 7.5)
        self.set_text_color(*WHITE)
        self.cell(
            0, 13,
            f"Guide d'assistance SILLON  |  Édité le {TODAY}  |  Page {self.page_no()}",
            align="C",
        )
        self.set_text_color(*BLACK)

    def h1(self, text):
        self.ln(4)
        self.set_fill_color(*BLUE_DARK)
        self.set_text_color(*WHITE)
        self.set_font("Sans", "B", 12.5)
        self.cell(CONTENT_W, 9, f"  {text}", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BLACK)
        self.ln(2)

    def h2(self, text):
        self.ln(3)
        self.set_fill_color(*BLUE_LIGHT)
        self.set_text_color(*BLUE_DARK)
        self.set_font("Sans", "B", 10.5)
        self.set_draw_color(*BLUE_MED)
        self.set_line_width(0.4)
        self.cell(CONTENT_W, 7.5, f"  {text}", border="L", fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BLACK)
        self.set_draw_color(*BLACK)
        self.ln(1)

    def h3(self, text):
        self.ln(2)
        self.set_font("Sans", "B", 9.5)
        self.set_text_color(*BLUE_MED)
        self.cell(CONTENT_W, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BLACK)

    def body(self, text, size=9):
        self.set_font("Sans", "", size)
        self.multi_cell(CONTENT_W, 5.2, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def bullet(self, text, level=1, bold_prefix=None):
        indent = 4 * level
        self.set_x(MARGIN_L + indent)
        self.set_font("Sans", "", 8.8)
        prefix_char = "•" if level == 1 else "–"
        if bold_prefix:
            self.set_font("Sans", "B", 8.8)
            bw = self.get_string_width(bold_prefix) + 1
            self.cell(bw, 5.2, bold_prefix, new_x=XPos.RIGHT, new_y=YPos.LAST)
            self.set_font("Sans", "", 8.8)
            self.multi_cell(CONTENT_W - indent - bw, 5.2, text,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.multi_cell(CONTENT_W - indent, 5.2,
                            f"{prefix_char}  {text}",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def note(self, text, color=(240, 248, 255)):
        self.ln(1)
        self.set_fill_color(*color)
        self.set_draw_color(*GREY_BORDER)
        self.set_line_width(0.3)
        self.set_font("Sans", "I", 8.2)
        self.set_x(MARGIN_L)
        self.multi_cell(CONTENT_W, 4.8, f"  {text}", border=1, fill=True,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*BLACK)
        self.ln(1)

    def code(self, text):
        self.ln(1)
        self.set_fill_color(28, 28, 35)
        self.set_text_color(160, 255, 160)
        self.set_font("Mono", "", 7.5)
        for line in text.split("\n"):
            self.set_x(MARGIN_L)
            self.cell(CONTENT_W, 4.8, f"  {line}", fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BLACK)
        self.ln(1)

    def table_row(self, cols, widths, header=False, fill_color=None):
        fc = fill_color or WHITE
        self.set_fill_color(*fc)
        style = "B" if header else ""
        tc = WHITE if header and fill_color == BLUE_DARK else BLACK
        self.set_text_color(*tc)
        self.set_font("Sans", style, 8.2)
        self.set_x(MARGIN_L)
        for text, w in zip(cols, widths):
            self.cell(w, 6.2, f" {text}", border=1, fill=True,
                      new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_text_color(*BLACK)
        self.ln()

    def escalade_badge(self, niveau, label, color, bg):
        self.ln(3)
        self.set_fill_color(*color)
        self.set_text_color(*WHITE)
        self.set_font("Sans", "B", 11)
        self.cell(CONTENT_W, 9, f"  {niveau}  —  {label}",
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BLACK)
        self.ln(1)

    def faq_item(self, question, reponse, niveau_badge=None, badge_color=None, badge_bg=None):
        """Bloc FAQ : question en gras, réponse en body, badge de niveau optionnel."""
        self.ln(2)
        self.set_fill_color(*GREY_LIGHT)
        self.set_draw_color(*GREY_BORDER)
        self.set_line_width(0.2)
        self.set_x(MARGIN_L)
        self.set_font("Sans", "B", 9)
        self.set_text_color(*BLUE_DARK)
        q_prefix = "Q.  "
        pw = self.get_string_width(q_prefix)
        self.cell(pw, 6.5, q_prefix, fill=True, border="LT",
                  new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_font("Sans", "B", 9)
        self.set_text_color(*BLACK)
        avail = CONTENT_W - pw
        if niveau_badge:
            badge_text = f"  [{niveau_badge}]"
            bw = self.get_string_width(badge_text) + 2
            self.set_fill_color(*GREY_LIGHT)
            self.multi_cell(avail - bw, 6.5, question, fill=True, border="T",
                            new_x=XPos.RIGHT, new_y=YPos.LAST)
            self.set_fill_color(*(badge_bg or BLUE_LIGHT))
            self.set_text_color(*(badge_color or BLUE_DARK))
            self.set_font("Sans", "B", 7.5)
            self.cell(bw, 6.5, badge_text, fill=True, border="TR",
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.set_fill_color(*GREY_LIGHT)
            self.multi_cell(avail, 6.5, question, fill=True, border="TR",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*BLACK)
        self.set_draw_color(*BLACK)
        self.set_x(MARGIN_L + 4)
        self.set_font("Sans", "", 8.8)
        self.multi_cell(CONTENT_W - 4, 5.2, reponse,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def probleme_bloc(self, symptome, causes, resolution, niveau, escalade=None,
                      code_block=None):
        """Bloc de résolution structuré : symptôme → causes → résolution → escalade."""
        self.ln(3)
        niv_colors = {
            "N1": (GREEN_OK,    GREEN_LIGHT),
            "N2": (ORANGE_WARN, ORANGE_LIGHT),
            "N3": (RED_CRIT,    RED_LIGHT),
        }
        nc, nb = niv_colors.get(niveau, (BLUE_MED, BLUE_LIGHT))
        self.set_fill_color(*nb)
        self.set_draw_color(*nc)
        self.set_line_width(0.5)
        self.set_x(MARGIN_L)
        self.set_font("Sans", "B", 8.8)
        self.set_text_color(*nc)
        badge = f"[{niveau}]"
        bw = self.get_string_width(badge) + 4
        self.cell(bw, 7, badge, fill=True, border=1,
                  new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_text_color(*BLACK)
        self.set_fill_color(*GREY_LIGHT)
        self.set_font("Sans", "B", 8.8)
        self.cell(CONTENT_W - bw, 7, f"  {symptome}", fill=True, border=1,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*BLACK)
        self.set_line_width(0.2)

        self.set_x(MARGIN_L)
        self.set_fill_color(*BLUE_LIGHT)
        self.set_font("Sans", "B", 8)
        self.set_text_color(*BLUE_DARK)
        self.cell(22, 5.5, "  Causes :", fill=True, border="LB",
                  new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_font("Sans", "", 8)
        self.set_text_color(*BLACK)
        self.set_fill_color(*WHITE)
        self.multi_cell(CONTENT_W - 22, 5.5, f" {causes}", fill=True, border="BR",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_x(MARGIN_L)
        self.set_fill_color(*GREEN_LIGHT)
        self.set_font("Sans", "B", 8)
        self.set_text_color(*GREEN_OK)
        self.cell(22, 5.5, "  Action :", fill=True, border="LB",
                  new_x=XPos.RIGHT, new_y=YPos.LAST)
        self.set_font("Sans", "", 8)
        self.set_text_color(*BLACK)
        self.set_fill_color(*WHITE)
        self.multi_cell(CONTENT_W - 22, 5.5, f" {resolution}", fill=True, border="BR",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if code_block:
            self.code(code_block)

        if escalade:
            self.set_x(MARGIN_L)
            self.set_fill_color(*ORANGE_LIGHT)
            self.set_font("Sans", "B", 8)
            self.set_text_color(*ORANGE_WARN)
            self.cell(22, 5.5, "  Escalade :", fill=True, border="LB",
                      new_x=XPos.RIGHT, new_y=YPos.LAST)
            self.set_font("Sans", "I", 8)
            self.set_text_color(*BLACK)
            self.set_fill_color(*WHITE)
            self.multi_cell(CONTENT_W - 22, 5.5, f" {escalade}", fill=True, border="BR",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# =============================================================================
# Construction du document
# =============================================================================

pdf = PDF()
pdf.set_title("Guide d'assistance — SILLON")
pdf.set_author("SILLON")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE DE TITRE
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.set_y(24)
pdf.set_font("Sans", "B", 10)
pdf.set_text_color(*BLUE_DARK)
pdf.cell(0, 7, "RÉPUBLIQUE FRANÇAISE", align="C",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Sans", "I", 8)
pdf.cell(0, 5, "Liberté  •  Égalité  •  Fraternité",
         align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(*BLACK)

pdf.ln(5)
pdf.set_draw_color(*BLUE_DARK)
pdf.set_line_width(0.8)
pdf.line(MARGIN_L, pdf.get_y(), PAGE_W - MARGIN_R, pdf.get_y())
pdf.ln(7)

pdf.set_font("Sans", "B", 22)
pdf.set_text_color(*BLUE_DARK)
pdf.cell(0, 12, "SILLON", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Sans", "B", 15)
pdf.cell(0, 9, "Guide d'assistance", align="C",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Sans", "", 12)
pdf.cell(0, 8, "Équipes de support — Système d'escalade et FAQ", align="C",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(*BLACK)

pdf.ln(5)
pdf.set_line_width(0.4)
pdf.line(MARGIN_L, pdf.get_y(), PAGE_W - MARGIN_R, pdf.get_y())
pdf.ln(8)

for label, val in [
    ("Référence",   "SILLON-SUPPORT-2026"),
    ("Version",     "1.0"),
    ("Date",        TODAY),
    ("Public cible","Équipes d'assistance N1 / N2 / N3"),
    ("Diffusion",   "Interne — Équipes support de la direction"),
]:
    pdf.set_x(MARGIN_L + 18)
    pdf.set_font("Sans", "B", 9)
    pdf.cell(52, 6.5, label, new_x=XPos.RIGHT, new_y=YPos.LAST)
    pdf.set_font("Sans", "", 9)
    pdf.cell(CONTENT_W - 52, 6.5, val, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

pdf.ln(8)

pdf.set_fill_color(*BLUE_LIGHT)
pdf.set_draw_color(*BLUE_MED)
pdf.set_line_width(0.5)
pdf.set_x(MARGIN_L)
pdf.set_font("Sans", "B", 9.5)
pdf.cell(CONTENT_W, 7, "  À propos de ce guide", border="LTR", fill=True,
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Sans", "", 8.8)
pdf.set_x(MARGIN_L)
pdf.multi_cell(CONTENT_W, 5.2,
    "  Ce guide est destiné aux agents et techniciens chargés de l'assistance aux utilisateurs "
    "de SILLON. Il définit les trois niveaux d'escalade (N1 support utilisateur, N2 support "
    "technique, N3 infrastructure et sécurité), fournit une procédure de résolution pour chaque "
    "problème courant, recense les questions fréquentes des utilisateurs, et décrit les opérations "
    "de gestion des comptes (réinitialisation de mot de passe, désactivation, débannissement d'IP).",
    border="LBR", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_draw_color(*BLACK)

pdf.ln(6)

pdf.set_font("Sans", "B", 9)
pdf.set_text_color(*BLUE_DARK)
pdf.cell(CONTENT_W, 6, "  Sommaire", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_text_color(*BLACK)
sommaire = [
    ("1.", "Présentation de SILLON pour les équipes support",  "2"),
    ("2.", "Système d'escalade N1 / N2 / N3",                   "3"),
    ("3.", "Guide de résolution des problèmes courants",         "4–5"),
    ("4.", "FAQ utilisateurs",                                   "6–7"),
    ("5.", "Gestion des comptes et des accès",                   "8"),
    ("6.", "Contacts et ressources",                             "8"),
]
for num, titre, page in sommaire:
    pdf.set_x(MARGIN_L + 6)
    pdf.set_font("Sans", "B", 8.8)
    nw = pdf.get_string_width(num) + 2
    pdf.cell(nw, 6, num, new_x=XPos.RIGHT, new_y=YPos.LAST)
    pdf.set_font("Sans", "", 8.8)
    pdf.cell(CONTENT_W - nw - 15, 6, titre, new_x=XPos.RIGHT, new_y=YPos.LAST)
    pdf.set_font("Sans", "I", 8.2)
    pdf.set_text_color(*BLUE_MED)
    pdf.cell(15, 6, page, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*BLACK)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — PRÉSENTATION POUR LES ÉQUIPES SUPPORT
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h1("1. Présentation de SILLON pour les équipes support")

pdf.h2("1.1  Qu'est-ce que SILLON ?")
pdf.body(
    "SILLON (Système d'Interrogation Local et Libre d'Outils Numériques) est une plateforme "
    "web locale développée par la direction pour permettre à ses data analystes d'importer des "
    "fichiers CSV, de les transformer en bases PostgreSQL correctement typées, de les interroger "
    "en SQL libre ou via des scripts Python/R exécutés côté serveur, et de partager les résultats "
    "— sans dépendre du lac de données national."
)
pdf.body(
    "L'application est accessible uniquement sur le réseau interne de la direction, via "
    "navigateur web (HTTPS). Il n'existe pas de réinitialisation de mot de passe en libre-service : "
    "toute réinitialisation passe obligatoirement par un administrateur SILLON."
)

pdf.h2("1.2  Les trois profils utilisateurs")
pdf.ln(1)
w_roles = [28, 35, CONTENT_W - 28 - 35]
pdf.table_row(["Profil", "Nom affiché", "Droits"], w_roles,
              header=True, fill_color=BLUE_DARK)
roles = [
    ("lecteur",        "Lecteur",        "Consultation des bases qui lui ont été explicitement partagées"),
    ("agent",          "Agent",          "Base personnelle, import CSV, SQL libre, scripts, partage"),
    ("administrateur", "Administrateur", "Comptes, quotas, journal d'audit — pas d'usage métier direct"),
]
colors = [GREEN_LIGHT, BLUE_LIGHT, ORANGE_LIGHT]
for row, color in zip(roles, colors):
    pdf.table_row(row, w_roles, fill_color=color)

pdf.ln(2)
pdf.note(
    "Chaque utilisateur possède un rôle PostgreSQL personnel, créé par l'administrateur à la "
    "création du compte — c'est ce rôle qui porte réellement les droits, pas une table de "
    "permissions applicative séparée. Un changement de profil prend effet à la prochaine connexion.",
    color=BLUE_LIGHT
)

pdf.h2("1.3  Statuts d'un job (import, requête longue, script)")
pdf.ln(1)
w_stat = [40, CONTENT_W - 40]
pdf.table_row(["Statut", "Signification"], w_stat, header=True, fill_color=BLUE_DARK)
statuts = [
    ("en_attente",  "Job en file, en attente d'un travailleur disponible"),
    ("en_cours",    "Job en cours d'exécution"),
    ("termine",     "Job terminé avec succès, résultat disponible au téléchargement"),
    ("erreur",      "Échec ou dépassement du délai maximal — message d'erreur explicite"),
    ("annule",      "Annulé par l'utilisateur pendant qu'il était en attente ou en cours"),
]
for i, row in enumerate(statuts):
    pdf.table_row(row, w_stat, fill_color=GREY_LIGHT if i % 2 == 0 else WHITE)

pdf.h2("1.4  Architecture simplifiée (vue support)")
pdf.body(
    "SILLON repose sur un seul serveur. La connaissance de cette architecture permet "
    "de mieux orienter les tickets vers le bon niveau de support."
)
pdf.ln(1)
w_arch = [48, 30, CONTENT_W - 48 - 30]
pdf.table_row(["Composant", "Service", "Impact panne"], w_arch,
              header=True, fill_color=BLUE_DARK)
archi = [
    ("Interface web / TLS (Nginx)",       "nginx",               "Application inaccessible"),
    ("API de requêtage (PostgREST)",      "sillon-api",          "Erreur 502/503 — interface charge mais plantée"),
    ("Orchestrateur (bases, imports, file)", "sillon-orchestrateur", "Import/SQL/scripts impossibles"),
    ("Travailleur (conteneurs de script)", "sillon-worker",       "Requêtes SQL normales, scripts jamais lancés"),
    ("Base de données (PostgreSQL)",       "postgresql",          "Plus aucune fonctionnalité disponible"),
    ("Anti-bruteforce",                    "fail2ban",            "Comptes légitimes bannis à tort possibles"),
]
for i, row in enumerate(archi):
    pdf.table_row(row, w_arch, fill_color=GREY_LIGHT if i % 2 == 0 else WHITE)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — SYSTÈME D'ESCALADE
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h1("2. Système d'escalade N1 / N2 / N3")

pdf.body(
    "Toute demande d'assistance doit être traitée au niveau le plus bas capable de la résoudre. "
    "L'escalade vers le niveau supérieur se fait uniquement si le problème dépasse les "
    "compétences ou les droits du niveau courant, ou si le délai de résolution est dépassé."
)

pdf.escalade_badge("N1 — Support utilisateur", "Depuis l'interface SILLON, compte administrateur",
                   GREEN_OK, GREEN_LIGHT)
pdf.body(
    "Périmètre : tout ce qui se règle depuis le panneau Administration de SILLON, sans accès au "
    "serveur — mot de passe oublié, compte à désactiver/réactiver, question d'utilisation, "
    "consultation du journal d'audit."
)
pdf.ln(1)
w_n = [55, 25, CONTENT_W - 55 - 25]
pdf.table_row(["Problème", "Délai résolution", "Action"], w_n,
              header=True, fill_color=GREEN_OK)
for row in [
    ("Mot de passe oublié",              "< 15 min",  "Réinitialiser depuis Administration (§5.1)"),
    ("Compte à désactiver (départ agent)","< 15 min",  "Désactiver depuis Administration (§5.2)"),
    ("Job bloqué en file d'attente",     "< 5 min",    "Rediriger vers l'onglet Suivi — annulation en self-service"),
    ("Question d'utilisation générale",  "< 30 min",   "Voir le guide utilisateur SILLON"),
    ("Interface lente",                  "< 30 min",   "Vider le cache navigateur, réessayer"),
]:
    pdf.table_row(row, w_n, fill_color=GREEN_LIGHT)

pdf.note(
    "Critère d'escalade N1 → N2 : problème non résolu après 30 minutes, ou problème nécessitant "
    "un accès au serveur (adresse IP bannie, service arrêté, erreur 502/503).",
    color=GREEN_LIGHT
)

pdf.escalade_badge("N2 — Support technique SILLON", "Accès serveur (SSH/console)",
                   ORANGE_WARN, ORANGE_LIGHT)
pdf.body(
    "Périmètre : redémarrage des services, diagnostic des journaux, débannissement Fail2Ban, "
    "gestion des comptes en ligne de commande, lenteurs base de données."
)
pdf.ln(1)
pdf.table_row(["Problème", "Délai résolution", "Action"], w_n,
              header=True, fill_color=ORANGE_WARN)
for row in [
    ("Adresse IP bannie (Fail2Ban)",              "< 30 min", "fail2ban-client unbanip (§3)"),
    ("Erreur 502/503 (application inaccessible)", "< 30 min", "Vérifier/redémarrer sillon-api, sillon-orchestrateur"),
    ("Tous les scripts échouent (SQL normal)",    "< 1h",     "Vérifier sillon-worker, cf. guide install §9.1"),
    ("Lenteur persistante (> 5 sec)",              "< 1h",     "Analyser pg_stat_activity"),
    ("Sauvegarde en échec (pgBackRest)",           "< 2h",     "Vérifier le montage NFS, relancer"),
]:
    pdf.table_row(row, w_n, fill_color=ORANGE_LIGHT)

pdf.note(
    "Critère d'escalade N2 → N3 : compromission suspectée d'un ou plusieurs comptes, fuite "
    "potentielle du secret de signature des jetons, panne matérielle, incident de sécurité.",
    color=ORANGE_LIGHT
)

pdf.escalade_badge("N3 — Infrastructure et sécurité", "Administrateur technique / RSSI",
                   RED_CRIT, RED_LIGHT)
pdf.body(
    "Périmètre : compromission avérée ou fortement suspectée, régénération du secret de "
    "signature des jetons (invalide toutes les sessions de tous les utilisateurs d'un coup), "
    "sinistre matériel, restauration depuis sauvegarde."
)
pdf.ln(1)
pdf.table_row(["Problème", "Délai résolution", "Action"], w_n,
              header=True, fill_color=RED_CRIT)
for row in [
    ("Compte compromis, plusieurs comptes touchés", "Immédiat", "Désactivation ciblée + évaluation régénération secret (§3)"),
    ("Fuite suspectée du secret de signature",       "Immédiat", "Régénérer le secret JWT (§3) — déconnecte tout le monde"),
    ("Panne matérielle du serveur SILLON",           "Variable", "Restauration pgBackRest (guide install §7.5)"),
]:
    pdf.table_row(row, w_n, fill_color=RED_LIGHT)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — RÉSOLUTION DES PROBLÈMES (1/2)
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h1("3. Guide de résolution des problèmes courants")

pdf.body(
    "Chaque fiche indique le niveau de support requis [N1/N2/N3], les causes les plus "
    "fréquentes et les actions à mener dans l'ordre. Escalader si la résolution échoue."
)

pdf.probleme_bloc(
    symptome="L'utilisateur ne peut pas se connecter — message « Identifiants incorrects »",
    causes="Mot de passe erroné (casse, caractères spéciaux) ; email saisi avec une coquille ; "
           "compte désactivé (le message reste le même, par choix de sécurité — pas d'indice "
           "donné sur la cause exacte à un tiers non authentifié).",
    resolution="1. Vérifier l'email exact (copier-coller). "
               "2. Réinitialiser le mot de passe (§5.1). "
               "3. Vérifier dans la liste des comptes si le compte est marqué actif ; "
               "le réactiver si besoin (§5.2).",
    niveau="N1",
    escalade="Si l'erreur persiste après réinitialisation et compte actif → N2 (vérifier l'état de sillon-api)."
)

pdf.probleme_bloc(
    symptome="L'utilisateur est bloqué — message « Trop de requêtes » après échec de connexion",
    causes="Fail2Ban a banni l'adresse IP après 5 tentatives de connexion échouées en 10 minutes "
           "(jail sillon-login, ban d'1 heure). Cas fréquent : simples erreurs de frappe répétées, "
           "sans intention malveillante.",
    resolution="1. Attendre 1 heure (le ban expire automatiquement) si l'urgence ne le justifie pas. "
               "2. Sinon, débannir manuellement l'adresse.",
    niveau="N2",
    code_block="# Lister les IP actuellement bannies\nsudo fail2ban-client status sillon-login\n\n# Débannir une adresse précise\nsudo fail2ban-client set sillon-login unbanip <ADRESSE_IP>",
    escalade="Si le même utilisateur est banni de façon répétée sans erreur de frappe plausible → N3 (tentative de bruteforce possible)."
)

pdf.probleme_bloc(
    symptome="Erreur 502/503 — l'interface charge mais toutes les requêtes échouent",
    causes="Le service sillon-api (PostgREST) ou sillon-orchestrateur est arrêté ou ne répond plus. "
           "Cause fréquente : redémarrage de PostgreSQL sans redémarrage des services applicatifs.",
    resolution="Vérifier l'état des services, redémarrer ceux en défaut, consulter les journaux "
               "si le redémarrage ne suffit pas.",
    niveau="N2",
    code_block="sudo systemctl status sillon-api sillon-orchestrateur postgresql\nsudo systemctl restart sillon-api sillon-orchestrateur\n\n# Si le service ne redémarre pas : journaux\njournalctl -u sillon-api -n 50\njournalctl -u sillon-orchestrateur -n 50",
    escalade="Si les services refusent de démarrer après vérification des journaux → N3."
)

pdf.probleme_bloc(
    symptome="Les scripts Python/R échouent alors que les requêtes SQL fonctionnent normalement",
    causes="Cause connue et documentée : changement d'adresse IP du serveur (DHCP, VM redéployée) "
           "ou redémarrage complet depuis une installation ancienne de sillon-worker — les scripts "
           "s'exécutent dans un conteneur qui ne peut plus joindre PostgreSQL sur l'adresse détectée "
           "à l'installation (guide d'installation administrateur, §9.1 et §9.2).",
    resolution="1. Vérifier les journaux de sillon-worker pour confirmer une erreur de connexion "
               "PostgreSQL (pas une erreur applicative du script lui-même). "
               "2. Réinstaller le paquet sillon-worker (redétecte l'adresse et corrige la "
               "configuration automatiquement) — voir guide d'installation §9.1 pour la correction "
               "manuelle si une réinstallation n'est pas souhaitée.",
    niveau="N2",
    code_block="journalctl -u sillon-worker -n 50",
    escalade="Si le symptôme apparaît sans changement d'IP ni redémarrage récent → N3 (cause non identifiée, creuser plus loin)."
)

pdf.probleme_bloc(
    symptome="Un import CSV ou une requête est rejeté pour dépassement de quota",
    causes="Quota atteint : taille de CSV, durée de job, ou espace disque de la base personnelle. "
           "Le dépassement place le job en erreur avec un message explicite, jamais de "
           "dégradation silencieuse.",
    resolution="1. Vérifier si le quota par défaut est réellement insuffisant pour un usage "
               "légitime (import ponctuel exceptionnel, jeu de données volumineux justifié). "
               "2. Ajuster le quota global concerné depuis Administration → Quotas si pertinent "
               "pour l'ensemble de la plateforme.",
    niveau="N1",
    escalade="Aucune dérogation par utilisateur individuel n'existe à ce jour dans l'interface — "
             "seuls les quotas globaux sont réglables ; remonter à l'équipe de développement si "
             "un cas concret nécessite un quota différencié par agent."
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — RÉSOLUTION DES PROBLÈMES (2/2)
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h2("(suite — Problèmes courants)")

pdf.probleme_bloc(
    symptome="Compte compromis suspecté (identifiants divulgués, comportement anormal constaté)",
    causes="Fuite d'identifiants, poste de l'agent compromis, ou soupçon d'accès non autorisé "
           "détecté dans le journal d'audit.",
    resolution="1. Désactiver immédiatement le compte concerné depuis Administration (§5.2) — "
               "le statut est revérifié à chaque requête, l'effet est immédiat même si une "
               "session était déjà ouverte. 2. Consulter le journal d'audit pour évaluer l'étendue "
               "des actions effectuées avec ce compte.",
    niveau="N1",
    escalade="Si plusieurs comptes semblent touchés, ou si le secret de signature des jetons "
             "lui-même est potentiellement compromis → N3, régénération du secret (§3, action "
             "réservée à l'administrateur technique — déconnecte tous les utilisateurs)."
)

pdf.probleme_bloc(
    symptome="[N3 uniquement] Régénération du secret de signature des jetons (JWT)",
    causes="Mesure de dernier recours en cas de compromission avérée ou fortement suspectée — "
           "invalide immédiatement toutes les sessions actives de tous les utilisateurs.",
    resolution="Générer un nouveau secret aléatoire, le répercuter dans la base et dans la "
               "configuration de PostgREST, puis redémarrer les deux services qui le lisent.",
    niveau="N3",
    code_block="NOUVEAU=$(tr -dc 'A-Za-z0-9_-' < /dev/urandom | head -c 48)\n\n# 1. Mettre a jour le secret en base (catalogue applicatif)\nsudo -u postgres psql -d sillon_catalog -c \\\n    \"UPDATE auth.secrets SET valeur = '$NOUVEAU' WHERE cle = 'jwt_secret';\"\n\n# 2. Mettre a jour la configuration de PostgREST\nsudo sed -i \"s/^jwt-secret = .*/jwt-secret = \\\"$NOUVEAU\\\"/\" /etc/sillon-api.conf\n\n# 3. Mettre a jour le secret partage (lu par l'orchestrateur)\nsudo sed -i \"s/^SILLON_JWT_SECRET=.*/SILLON_JWT_SECRET=$NOUVEAU/\" /etc/sillon/secrets.env\n\n# 4. Redemarrer les services concernes\nsudo systemctl restart sillon-api sillon-orchestrateur",
    escalade="Action non disponible depuis l'interface web à ce jour — nécessite un accès serveur. "
             "Prévenir les utilisateurs avant exécution : tout le monde sera déconnecté."
)

pdf.probleme_bloc(
    symptome="Alerte e-mail de la sonde de sauvegarde ([ALERTE CRITIQUE] ou [AVERTISSEMENT])",
    causes="Aucune sauvegarde récente reçue sur le serveur de sauvegarde. Causes : montage NFS "
           "perdu sur le serveur SILLON, serveur de sauvegarde éteint, tâche planifiée non exécutée.",
    resolution="1. Vérifier le montage NFS sur le serveur SILLON. "
               "2. Vérifier l'état du service pgBackRest et de la tâche planifiée.",
    niveau="N2",
    code_block="df -h /mnt/savesillon\nsudo -u postgres pgbackrest --stanza=sillon info",
    escalade="Si le serveur de sauvegarde est injoignable après vérification réseau → N3."
)

pdf.probleme_bloc(
    symptome="Alerte navigateur : « Certificat non sécurisé » ou « Votre connexion n'est pas privée »",
    causes="SILLON utilise un certificat TLS auto-signé généré à l'installation, tant qu'aucun "
           "certificat institutionnel n'a été installé (comportement normal en l'état).",
    resolution="1. Informer l'utilisateur que l'alerte est attendue sur cette instance. "
               "2. Lui indiquer comment ajouter une exception dans son navigateur. "
               "Pour Chrome : Paramètres avancés → Continuer vers le site. "
               "Pour Firefox : Accepter le risque et continuer.",
    niveau="N1",
    escalade="Pour supprimer définitivement l'alerte → N2/N3 : installer un certificat institutionnel."
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6 — FAQ UTILISATEURS (1/2)
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h1("4. FAQ utilisateurs")

pdf.body(
    "Questions fréquentes posées par les agents. Le badge indique à quel niveau de support "
    "la réponse doit être apportée."
)

pdf.faq_item(
    "J'ai oublié mon mot de passe. Que faire ?",
    "SILLON ne propose pas de réinitialisation autonome par email — c'est un choix de sécurité "
    "délibéré. Contacter votre administrateur SILLON ou l'équipe support, qui réinitialisera "
    "votre mot de passe depuis le panneau d'administration et vous le communiquera hors bande.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Pourquoi mon compte me dit « trop de requêtes » alors que je n'ai rien fait d'anormal ?",
    "Après 5 échecs de connexion en 10 minutes, votre adresse IP est automatiquement bannie "
    "pendant 1 heure (protection anti-bruteforce). C'est le plus souvent dû à plusieurs essais "
    "successifs avec un mot de passe erroné. Patienter 1 heure, ou contacter le support si "
    "l'urgence le justifie — un déblocage manuel est possible.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Je ne peux pas importer de fichier ni créer de table. Pourquoi ?",
    "Vous êtes probablement connecté avec le profil Lecteur, qui permet uniquement de consulter "
    "les bases qui vous ont été partagées. Le profil Agent est nécessaire pour importer des "
    "fichiers et créer une base personnelle. Contacter votre administrateur SILLON pour faire "
    "évoluer votre profil.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Mon script Python/R reste bloqué en « en attente », il ne se lance jamais",
    "1. Vérifier dans l'onglet Suivi qu'un seul job à la fois est autorisé par défaut par "
    "utilisateur — si un autre job est déjà en cours, le nouveau attend son tour. "
    "2. Si aucun job n'est en cours et que l'attente se prolonge anormalement, contacter le "
    "support technique (le travailleur de file peut être arrêté).",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Comment partager ma base avec un collègue ?",
    "Depuis l'onglet Bases, sélectionner votre base personnelle puis « Gérer le partage » : "
    "rechercher le collègue par email et l'ajouter. Le partage donne un accès en lecture seule "
    "par défaut ; cocher séparément « autoriser l'exécution de scripts » si nécessaire — c'est "
    "une autorisation distincte, jamais activée par défaut.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Ma requête SQL a été interrompue automatiquement, pourquoi ?",
    "Un délai maximal d'exécution est imposé à chaque requête (30 minutes par défaut) pour "
    "protéger les autres utilisateurs de la plateforme. Pour un traitement plus long, basculer "
    "vers un job asynchrone (script déposé plutôt que requête interactive) : vous serez notifié "
    "par email à la fin.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 7 — FAQ UTILISATEURS (2/2)
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h2("(suite — FAQ utilisateurs)")

pdf.faq_item(
    "Mon import CSV est rejeté pour dépassement de taille",
    "La taille maximale d'un CSV importé est plafonnée (2 Go par défaut). Si le besoin est "
    "légitime et récurrent, transmettre la demande à l'administrateur SILLON, qui peut ajuster "
    "ce quota globalement depuis le panneau d'administration.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Je n'ai pas reçu le mail de fin de traitement d'un job",
    "Un mail n'est envoyé que lorsqu'un job passe en statut Terminé ou Erreur — jamais pour un "
    "traitement immédiat (import court, requête rapide). Vérifier d'abord le statut réel dans "
    "l'onglet Suivi. Si le job est bien terminé mais qu'aucun mail n'est arrivé, vérifier les "
    "courriers indésirables avant d'escalader.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Comment vérifier quel profil est attribué à un compte utilisateur ?",
    "Depuis l'interface administrateur : onglet Administration → tableau des comptes "
    "utilisateurs, qui affiche l'email, le nom et le profil de chaque compte. "
    "Depuis la ligne de commande (N2) :",
    niveau_badge="N2", badge_color=ORANGE_WARN, badge_bg=ORANGE_LIGHT
)
pdf.code("sudo -u postgres psql -d sillon_catalog \\\n    -c \"SELECT email, nom_complet, profil, actif FROM utilisateurs ORDER BY profil, email;\"")

pdf.faq_item(
    "Peut-on avoir deux sessions simultanées avec le même compte ?",
    "Oui. SILLON utilise des jetons JWT sans état : chaque connexion génère un jeton "
    "indépendant, valide 8 heures. Deux sessions simultanées sont possibles (deux postes, par "
    "exemple). La déconnexion sur l'une n'affecte pas l'autre. Désactiver le compte (§5.2) "
    "reste le seul moyen de couper l'accès immédiatement, y compris à une session déjà ouverte.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

pdf.faq_item(
    "Le certificat de sécurité du site est signalé comme non fiable par mon navigateur",
    "Comportement normal sur cette instance : SILLON utilise un certificat auto-signé tant "
    "qu'aucun certificat institutionnel n'a été installé par l'administrateur. Ajouter une "
    "exception dans le navigateur (voir §3, dernière fiche) pour continuer.",
    niveau_badge="N1", badge_color=GREEN_OK, badge_bg=GREEN_LIGHT
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 8 — GESTION DES COMPTES + CONTACTS
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()

pdf.h1("5. Gestion des comptes et des accès")

pdf.body(
    "Les opérations courantes se font depuis le panneau Administration de SILLON (aucun accès "
    "serveur requis). Une alternative en ligne de commande est donnée pour le support N2 "
    "lorsque l'interface est indisponible."
)

pdf.h2("5.1  Réinitialiser un mot de passe")
pdf.body("Depuis l'interface web : onglet Administration → tableau des comptes → bouton "
         "« Réinitialiser mdp » sur la ligne de l'utilisateur → saisir un nouveau mot de passe "
         "provisoire (12 caractères minimum) → valider.")
pdf.body("Depuis la base de données (N2, si l'interface est indisponible) :")
pdf.code(
    "sudo -u postgres psql -d sillon_catalog -c \\\n"
    "    \"SELECT public.reinitialiser_mdp(\n"
    "        'prenom.nom@direction.gouv.fr',\n"
    "        'NouveauMotDePasse!2026'\n"
    "    );\""
)
pdf.note(
    "Communiquer le mot de passe provisoire par un canal hors bande (jamais par le même canal "
    "qu'une demande de support non authentifiée) et vérifier l'identité de l'utilisateur avant "
    "toute réinitialisation.",
    color=ORANGE_LIGHT
)

pdf.h2("5.2  Désactiver ou réactiver un compte")
pdf.body("Depuis l'interface web : onglet Administration → tableau des comptes → bouton "
         "« Désactiver » (devient « Réactiver » une fois le compte désactivé). Effet immédiat : "
         "le statut est revérifié à chaque requête, indépendamment d'une session déjà ouverte.")
pdf.body("Depuis la base de données (N2) :")
pdf.code(
    "-- Désactiver\n"
    "sudo -u postgres psql -d sillon_catalog -c \\\n"
    "    \"SELECT public.desactiver_utilisateur('prenom.nom@direction.gouv.fr');\"\n\n"
    "-- Réactiver\n"
    "sudo -u postgres psql -d sillon_catalog -c \\\n"
    "    \"SELECT public.reactiver_utilisateur('prenom.nom@direction.gouv.fr');\""
)

pdf.h2("5.3  Créer un compte utilisateur")
pdf.body("Depuis l'interface web : Administration → formulaire de création (email, mot de "
         "passe provisoire, nom complet, profil initial).")
pdf.body("Depuis la base de données (N2) :")
pdf.code(
    "-- Profil : 'lecteur', 'agent' ou 'administrateur'\n"
    "sudo -u postgres psql -d sillon_catalog -c \\\n"
    "    \"SELECT public.creer_utilisateur(\n"
    "        'prenom.nom@direction.gouv.fr',\n"
    "        'MotDePasseProvisoire!2026',\n"
    "        'Prénom Nom',\n"
    "        'agent'\n"
    "    );\""
)

pdf.h1("6. Contacts et ressources")

pdf.ln(1)
w_c = [45, 55, CONTENT_W - 45 - 55]
pdf.table_row(["Contact", "Coordonnées", "Disponibilité"], w_c,
              header=True, fill_color=BLUE_DARK)
contacts = [
    ("Support N2 — Équipe technique SILLON", "À compléter", "Heures ouvrées"),
    ("Administrateur SILLON",                "À compléter", "Heures ouvrées"),
    ("Infrastructure / RSSI de la direction","À compléter", "H24 (incident SSI)"),
]
for i, row in enumerate(contacts):
    pdf.table_row(row, w_c, fill_color=GREY_LIGHT if i % 2 == 0 else WHITE)

pdf.ln(3)
pdf.h2("Documents de référence")
pdf.bullet("SILLON_cahier_des_charges.md — comportement attendu, sécurité, performances, packaging")
pdf.bullet("GUIDE_INSTALLATION_ADMINISTRATEUR.md — mise en place du serveur, dépannage d'infrastructure")
pdf.bullet("GUIDE_UTILISATEUR_SILLON.md — prise en main de l'application, onglet par onglet")
pdf.bullet("GUIDE_ASSISTANCE_INFORMATIQUE.md — version source (Markdown) de ce guide")
pdf.bullet("NOMENCLATURE_LOGICIELLE_SILLON (SBOM) — composants installés, réglementation NIS2")

pdf.ln(3)
pdf.note(
    "Document généré automatiquement par generer_pdf_guide_assistance.py (dépôt SILLON), "
    "à partir de GUIDE_ASSISTANCE_INFORMATIQUE.md. Pour toute question ou mise à jour, "
    "contacter l'équipe technique SILLON.",
    color=GREY_LIGHT
)

OUTPUT = "/home/adm1/SILLON/GUIDE_ASSISTANCE_INFORMATIQUE.pdf"
pdf.output(OUTPUT)
print(f"PDF généré : {OUTPUT}")
