"""
Module partage par toutes les pages de l'app "C'est Quoi Ça ?"
Contient : secrets, traductions, base de donnees, appel IA, style visuel.
"""

import streamlit as st
import sqlite3
import base64
import json
import re
import os
import urllib.parse
from datetime import datetime, date
from google import genai
from google.genai import types
import streamlit.components.v1 as components

# ----------------------------------------------------------------------------
# CONSTANTES
# ----------------------------------------------------------------------------

LOGO_PATH = "logo.png"
DB_PATH = "scans.db"
VISION_MODEL = "gemini-3.1-flash-lite"
FREE_SCANS_PER_DAY = 2
WHATSAPP_NUMBER = "27750556027"
GA_MEASUREMENT_ID = "G-0MJ8GNR9QZ"
EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

PLANS = [
    {"name": "Starter", "price": 5, "quota": 20},
    {"name": "Pro", "price": 10, "quota": 60},
    {"name": "Illimité", "price": 15, "quota": None},
]


def get_secret(key, default=None):
    """Lit une cle secrete depuis st.secrets (Streamlit Cloud) OU depuis les
    variables d'environnement (Render, Railway, etc). Fonctionne sur les deux."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def has_secret(key):
    return get_secret(key) is not None


# ----------------------------------------------------------------------------
# TRADUCTIONS (FR / EN)
# ----------------------------------------------------------------------------

TRANSLATIONS = {
    "fr": {
        "title": "🔍 C'est Quoi Ça ?",
        "subtitle": "Prends une photo. Sais ce que c'est, pourquoi, et comment t'en servir — en 10 secondes.",
        "stat_scans": "📦 {n} objets identifiés",
        "stat_free": "🎟️ {remaining}/{total} scans gratuits aujourd'hui",
        "nav_scanner": "📸 Scanner",
        "nav_collection": "🗂️ Ma collection",
        "nav_about": "ℹ️ À propos",
        "nav_privacy": "🔒 Confidentialité",
        "nav_terms": "📄 Conditions",
        "nav_plans": "⭐ Plans",
        "nav_settings": "⚙️ Paramètres",
        "uploader_label": "Prends ou choisis une photo de l'objet",
        "context_label": "Contexte (optionnel)",
        "context_placeholder": "Ex: reçu de ma tante, acheté sur Temu, trouvé dans le garage...",
        "missing_key": "⚠️ Clé API manquante. Ajoute `GEMINI_API_KEY` dans les secrets de ton app. Clé gratuite sur aistudio.google.com.",
        "identify_button": "🔎 Identifier cet objet",
        "spinner_text": "L'IA regarde ton objet...",
        "rate_limit_warning": "⏳ Trop de scans d'un coup ! Attends environ 30 secondes et réessaie.",
        "generic_error": "Erreur pendant l'identification : {e}",
        "why_header": "🤔 Pourquoi ça existe",
        "how_header": "🛠️ Comment l'utiliser",
        "warning_header": "⚠️ Attention à",
        "scan_another": "🔄 Scanner un autre objet",
        "export_button": "📤 Exporter ce résultat",
        "export_why": "Pourquoi",
        "export_how": "Comment l'utiliser",
        "history_empty": "Aucun objet scanné pour l'instant. Va sur la page Scanner pour commencer !",
        "history_category": "**Catégorie :**",
        "history_why": "**Pourquoi :**",
        "history_how": "**Comment l'utiliser :**",
        "lang_label": "Langue",
        "about_title": "À propos",
        "about_text": (
            "**C'est Quoi Ça ?** t'aide à identifier n'importe quel objet en une photo : "
            "ce que c'est, pourquoi ça existe, et comment l'utiliser.\n\n"
            "Contact : [dynamiquekambu1@gmail.com](mailto:dynamiquekambu1@gmail.com)"
        ),
        "privacy_title": "Politique de confidentialité",
        "privacy_text": (
            "Les photos que tu envoies sont utilisées uniquement pour l'identification de l'objet "
            "et sont stockées dans l'historique de l'application (« Ma collection »).\n\n"
            "L'identification est réalisée par l'API Gemini de Google. Sur l'offre gratuite, Google "
            "peut utiliser les contenus envoyés pour améliorer ses modèles — voir les "
            "[conditions Google Gemini API](https://ai.google.dev/gemini-api/terms).\n\n"
            "Aucune donnée n'est vendue à des tiers. Pour toute question, contacte "
            "[dynamiquekambu1@gmail.com](mailto:dynamiquekambu1@gmail.com)."
        ),
        "terms_title": "Conditions d'utilisation",
        "terms_text": (
            "En utilisant cette application, tu acceptes que les informations fournies par l'IA "
            "sont données à titre indicatif et peuvent contenir des erreurs — vérifie toujours les "
            "informations importantes (sécurité, santé) auprès d'une source officielle.\n\n"
            "L'application est fournie « telle quelle », sans garantie."
        ),
        "stats_title": "📊 Statistiques d'usage",
        "stats_year": "Année",
        "stats_visits": "Ouvertures de l'app",
        "stats_scans": "Objets identifiés",
        "email_input_label": "Ton email",
        "email_submit": "Continuer",
        "email_invalid": "Entre un email valide pour continuer.",
        "premium_badge": "⭐ Illimité",
        "premium_title": "🔓 Passer en illimité",
        "premium_text": "Débloque plus de scans et le suivi complet de ta collection.",
        "already_paid_title": "Déjà payé ?",
        "already_paid_button": "Vérifier mon email",
        "not_premium_yet": "Pas encore activé — patiente le temps qu'on vérifie ton paiement.",
        "premium_active_msg": "✅ Compte {plan} actif ({email})",
        "need_email_text": "Entre ton email pour générer un résultat (ça sert juste à compter tes scans gratuits, pas de mot de passe).",
        "plan_quota": "{n} scans/mois",
        "plan_unlimited": "Illimité",
        "pay_button": "💬 Payer via WhatsApp",
        "admin_title": "🔐 Administration",
        "admin_password_label": "Mot de passe admin",
        "admin_wrong_password": "Mot de passe incorrect.",
        "admin_activate_title": "Activer un compte manuellement",
        "admin_plan_label": "Plan",
        "admin_approve_button": "✅ Activer",
        "admin_claim_approved": "Compte activé !",
        "home_step1": "Prends une photo de l'objet",
        "home_step2": "L'IA l'analyse en quelques secondes",
        "home_step3": "Tu obtiens quoi, pourquoi, comment",
    },
    "en": {
        "title": "🔍 What Is This?",
        "subtitle": "Take a photo. Know what it is, why it exists, and how to use it — in 10 seconds.",
        "stat_scans": "📦 {n} objects identified",
        "stat_free": "🎟️ {remaining}/{total} free scans today",
        "nav_scanner": "📸 Scanner",
        "nav_collection": "🗂️ My collection",
        "nav_about": "ℹ️ About",
        "nav_privacy": "🔒 Privacy",
        "nav_terms": "📄 Terms",
        "nav_plans": "⭐ Plans",
        "nav_settings": "⚙️ Settings",
        "uploader_label": "Take or choose a photo of the object",
        "context_label": "Context (optional)",
        "context_placeholder": "E.g.: gift from a relative, bought on Temu, found in the garage...",
        "missing_key": "⚠️ Missing API key. Add `GEMINI_API_KEY` to your app secrets. Free key at aistudio.google.com.",
        "identify_button": "🔎 Identify this object",
        "spinner_text": "The AI is looking at your object...",
        "rate_limit_warning": "⏳ Too many scans at once! Wait about 30 seconds and try again.",
        "generic_error": "Error during identification: {e}",
        "why_header": "🤔 Why it exists",
        "how_header": "🛠️ How to use it",
        "warning_header": "⚠️ Watch out for",
        "scan_another": "🔄 Scan another object",
        "export_button": "📤 Export this result",
        "export_why": "Why",
        "export_how": "How to use it",
        "history_empty": "No object scanned yet. Head to the Scanner page to get started!",
        "history_category": "**Category:**",
        "history_why": "**Why:**",
        "history_how": "**How to use it:**",
        "lang_label": "Language",
        "about_title": "About",
        "about_text": (
            "**What Is This?** helps you identify any object from a photo: "
            "what it is, why it exists, and how to use it.\n\n"
            "Contact: [dynamiquekambu1@gmail.com](mailto:dynamiquekambu1@gmail.com)"
        ),
        "privacy_title": "Privacy Policy",
        "privacy_text": (
            "Photos you upload are used only to identify the object and are stored in the "
            "app's history (\"My collection\").\n\n"
            "Identification is performed by Google's Gemini API. On the free tier, Google may use "
            "submitted content to improve its models — see the "
            "[Gemini API terms](https://ai.google.dev/gemini-api/terms).\n\n"
            "No data is sold to third parties. For any question, contact "
            "[dynamiquekambu1@gmail.com](mailto:dynamiquekambu1@gmail.com)."
        ),
        "terms_title": "Terms of Use",
        "terms_text": (
            "By using this app, you agree that the information provided by the AI is for "
            "informational purposes only and may contain errors — always verify important "
            "information (safety, health) with an official source.\n\n"
            "The app is provided \"as is\", without warranty."
        ),
        "stats_title": "📊 Usage statistics",
        "stats_year": "Year",
        "stats_visits": "App opens",
        "stats_scans": "Objects identified",
        "email_input_label": "Your email",
        "email_submit": "Continue",
        "email_invalid": "Enter a valid email to continue.",
        "premium_badge": "⭐ Unlimited",
        "premium_title": "🔓 Go unlimited",
        "premium_text": "Unlock more scans and full collection tracking.",
        "already_paid_title": "Already paid?",
        "already_paid_button": "Check my email",
        "not_premium_yet": "Not activated yet — please wait while we verify your payment.",
        "premium_active_msg": "✅ {plan} account active ({email})",
        "need_email_text": "Enter your email to generate a result (only used to track your free scans, no password needed).",
        "plan_quota": "{n} scans/month",
        "plan_unlimited": "Unlimited",
        "pay_button": "💬 Pay via WhatsApp",
        "admin_title": "🔐 Admin",
        "admin_password_label": "Admin password",
        "admin_wrong_password": "Wrong password.",
        "admin_activate_title": "Activate an account manually",
        "admin_plan_label": "Plan",
        "admin_approve_button": "✅ Activate",
        "admin_claim_approved": "Account activated!",
        "home_step1": "Take a photo of the object",
        "home_step2": "The AI analyzes it in seconds",
        "home_step3": "You get what, why, how",
    },
}


def t(key, **kwargs):
    lang = st.session_state.get("lang", "fr")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ----------------------------------------------------------------------------
# SESSION STATE PARTAGE (initialise une fois, dispo sur toutes les pages)
# ----------------------------------------------------------------------------

def init_session_state():
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "lang" not in st.session_state:
        st.session_state.lang = "fr"
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""


# ----------------------------------------------------------------------------
# STYLE + GOOGLE ANALYTICS (a appeler en haut de chaque page)
# ----------------------------------------------------------------------------

def apply_style():
    components.html(
        f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{ dataLayer.push(arguments); }}
          gtag('js', new Date());
          gtag('config', '{GA_MEASUREMENT_ID}');
        </script>
        """,
        height=0,
        width=0,
    )

    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

            #MainMenu, footer, header {visibility: hidden;}

            html, body, .stApp, [class*="css"] {
                font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            .stApp {
                background: radial-gradient(circle at top, #FFF3E9 0%, #FFFFFF 55%);
            }

            .block-container {
                padding-top: 1.6rem;
                padding-bottom: 3rem;
                max-width: 680px;
            }

            [data-testid="stSidebar"] {
                background-color: #FFFFFF !important;
            }

            [data-testid="stSidebarNav"] a span,
            [data-testid="stSidebarNav"] a p {
                color: #1F2937 !important;
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                background-color: #FFF1E6 !important;
                border-radius: 8px;
            }

            .hero-title {
                font-size: 2.3rem;
                font-weight: 800;
                text-align: center;
                color: #1F2937;
                margin-bottom: 0.15rem;
                letter-spacing: -0.02em;
            }

            .hero-sub {
                text-align: center;
                color: #6B7280;
                font-size: 1.02rem;
                margin-bottom: 1.8rem;
                line-height: 1.4;
            }

            .stat-pill {
                display: inline-block;
                background: #FFF1E6;
                color: #C2410C !important;
                border-radius: 999px;
                padding: 7px 18px;
                font-weight: 700;
                font-size: 0.85rem;
                margin: 2px 6px 2px 0;
                border: 1px solid #FFE0C7;
            }

            .result-card {
                background: #FFFFFF;
                border-radius: 20px;
                padding: 24px 24px;
                margin-bottom: 16px;
                box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
                border: 1px solid #F1F1F1;
                color: #1F2937;
            }

            .result-card p, .result-card li {
                line-height: 1.55;
                color: #1F2937;
            }

            .result-card h4 {
                margin-top: 0;
                margin-bottom: 10px;
                font-size: 1.05rem;
                font-weight: 700;
                color: #1F2937;
            }

            .object-name {
                font-size: 1.7rem;
                font-weight: 800;
                color: #111827;
                margin-bottom: 0;
                letter-spacing: -0.01em;
            }

            .object-category {
                display: inline-block;
                color: #EA580C !important;
                background: #FFF1E6;
                font-weight: 700;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin-bottom: 12px;
                padding: 3px 10px;
                border-radius: 999px;
            }

            div.stButton > button {
                border-radius: 999px;
                font-weight: 700;
                padding: 0.65rem 1.4rem;
                border: none;
                transition: transform 0.1s ease;
            }

            div.stButton > button:active {
                transform: scale(0.98);
            }

            div.stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #FB923C, #EA580C);
                color: white;
                box-shadow: 0 4px 14px rgba(234, 88, 12, 0.28);
            }

            .warn-box {
                background: #FFF7ED;
                border-left: 4px solid #F97316;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 0.92rem;
                color: #7C2D12;
            }

            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] ol,
            [data-testid="stMarkdownContainer"] ul,
            [data-testid="stMarkdownContainer"] table,
            [data-testid="stMarkdownContainer"] th,
            [data-testid="stMarkdownContainer"] td,
            [data-testid="stMarkdownContainer"] strong,
            [data-testid="stText"],
            [data-testid="stWidgetLabel"] p,
            [data-testid="stCaptionContainer"],
            .stAlert p,
            .stAlert div {
                color: #1F2937 !important;
            }

            [data-testid="stMarkdownContainer"] a {
                color: #EA580C !important;
            }

            [data-testid="stExpander"] summary,
            [data-testid="stExpander"] summary span,
            [data-testid="stExpander"] summary p {
                color: #1F2937 !important;
            }

            input, textarea,
            [data-baseweb="input"],
            [data-baseweb="textarea"],
            [data-baseweb="base-input"] {
                color: #1F2937 !important;
                background-color: #FFFFFF !important;
                -webkit-text-fill-color: #1F2937 !important;
            }

            [data-baseweb="select"] > div {
                color: #1F2937 !important;
                background-color: #FFFFFF !important;
            }

            .step-row {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                margin: 1.4rem 0;
                flex-wrap: wrap;
            }

            .step-card {
                background: #FFFFFF;
                border: 1px solid #F1F1F1;
                border-radius: 16px;
                padding: 16px 10px;
                text-align: center;
                width: 105px;
                box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
            }

            .step-emoji { font-size: 1.8rem; }

            .step-num {
                display: inline-block;
                background: #EA580C;
                color: white !important;
                font-weight: 800;
                font-size: 0.72rem;
                width: 18px;
                height: 18px;
                line-height: 18px;
                border-radius: 999px;
                margin: 4px 0;
            }

            .step-text {
                font-size: 0.78rem;
                color: #4B5563 !important;
                line-height: 1.3;
            }

            .step-arrow { color: #FDBA74; font-size: 1.3rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_lang_selector():
    with st.sidebar:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=48)
        lang_choice = st.selectbox(
            t("lang_label"),
            options=["fr", "en"],
            format_func=lambda x: "🇫🇷 Français" if x == "fr" else "🇬🇧 English",
            index=0 if st.session_state.lang == "fr" else 1,
        )
        if lang_choice != st.session_state.lang:
            st.session_state.lang = lang_choice
            st.rerun()


# ----------------------------------------------------------------------------
# BASE DE DONNEES
# ----------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            context TEXT,
            object_name TEXT,
            category TEXT,
            why_text TEXT,
            how_steps TEXT,
            warning_text TEXT,
            image_b64 TEXT,
            email TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS premium_emails (
            email TEXT PRIMARY KEY,
            activated_at TEXT NOT NULL,
            plan TEXT,
            monthly_quota INTEGER
        )
        """
    )
    for stmt in (
        "ALTER TABLE scans ADD COLUMN email TEXT",
        "ALTER TABLE premium_emails ADD COLUMN plan TEXT",
        "ALTER TABLE premium_emails ADD COLUMN monthly_quota INTEGER",
    ):
        try:
            conn.execute(stmt)
            conn.commit()
        except sqlite3.OperationalError:
            pass
    conn.commit()
    return conn


def get_premium_info(email):
    if not email:
        return None
    conn = get_conn()
    row = conn.execute(
        "SELECT plan, monthly_quota FROM premium_emails WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return row


def is_premium(email):
    return get_premium_info(email) is not None


def activate_premium(email, plan, quota):
    conn = get_conn()
    conn.execute(
        "INSERT INTO premium_emails (email, activated_at, plan, monthly_quota) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(email) DO UPDATE SET plan=excluded.plan, monthly_quota=excluded.monthly_quota",
        (email, datetime.now().isoformat(), plan, quota),
    )
    conn.commit()
    conn.close()


def get_scans_today(email):
    conn = get_conn()
    today_prefix = date.today().isoformat()
    count = conn.execute(
        "SELECT COUNT(*) FROM scans WHERE email = ? AND created_at LIKE ?",
        (email, f"{today_prefix}%"),
    ).fetchone()[0]
    conn.close()
    return count


def get_scans_this_month(email):
    conn = get_conn()
    month_prefix = date.today().strftime("%Y-%m")
    count = conn.execute(
        "SELECT COUNT(*) FROM scans WHERE email = ? AND created_at LIKE ?",
        (email, f"{month_prefix}%"),
    ).fetchone()[0]
    conn.close()
    return count


def log_visit():
    if st.session_state.get("visit_logged"):
        return
    conn = get_conn()
    conn.execute("INSERT INTO visits (created_at) VALUES (?)", (datetime.now().isoformat(),))
    conn.commit()
    conn.close()
    st.session_state.visit_logged = True


def get_stats_by_year():
    conn = get_conn()
    visits_rows = conn.execute(
        "SELECT strftime('%Y', created_at) as y, COUNT(*) FROM visits GROUP BY y ORDER BY y DESC"
    ).fetchall()
    scans_rows = conn.execute(
        "SELECT strftime('%Y', created_at) as y, COUNT(*) FROM scans GROUP BY y ORDER BY y DESC"
    ).fetchall()
    conn.close()
    visits_by_year = {y: c for y, c in visits_rows}
    scans_by_year = {y: c for y, c in scans_rows}
    years = sorted(set(visits_by_year) | set(scans_by_year), reverse=True)
    return [(y, visits_by_year.get(y, 0), scans_by_year.get(y, 0)) for y in years]


def save_scan(context, data, image_b64, email):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO scans (created_at, context, object_name, category, why_text, how_steps, warning_text, image_b64, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            context,
            data.get("object_name", ""),
            data.get("category", ""),
            data.get("why", ""),
            json.dumps(data.get("how_steps", [])),
            data.get("warning", ""),
            image_b64,
            email,
        ),
    )
    conn.commit()
    conn.close()


def get_history(email, limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, created_at, object_name, category, why_text, how_steps, warning_text, image_b64 "
        "FROM scans WHERE email = ? ORDER BY id DESC LIMIT ?",
        (email, limit),
    ).fetchall()
    conn.close()
    return rows


def get_total_scans():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    conn.close()
    return count


def get_usage_status(email):
    """Retourne (is_premium, remaining, quota, plan_name)."""
    if not email:
        return False, FREE_SCANS_PER_DAY, FREE_SCANS_PER_DAY, None
    info = get_premium_info(email)
    if info:
        plan, quota = info
        if quota is None:
            return True, None, None, plan
        used = get_scans_this_month(email)
        return True, max(0, quota - used), quota, plan
    used = get_scans_today(email)
    return False, max(0, FREE_SCANS_PER_DAY - used), FREE_SCANS_PER_DAY, None


# ----------------------------------------------------------------------------
# APPEL IA
# ----------------------------------------------------------------------------

IDENTIFY_PROMPT = """Tu es un expert capable d'identifier n'importe quel objet du quotidien a \
partir d'une photo, meme des gadgets obscurs, pieces detachees, objets importes sans notice, \
produits de niche, ou produits de marque connue (cosmetiques, entretien, alimentaire, etc).

Explique ensuite a quoi il sert et comment l'utiliser, pour quelqu'un qui le decouvre pour la \
premiere fois. C'est une question generale de connaissance grand public, pas un avis medical.

Reponds UNIQUEMENT dans ce format texte exact, avec ces 4 marqueurs, rien avant ni apres, \
chaque marqueur sur sa propre ligne :

NOM: <nom court et clair de l'objet, marque si visible>
CATEGORIE: <1-2 mots, ex: Cuisine, Electronique, Beaute, Bricolage>
POURQUOI: <2 a 3 phrases expliquant pourquoi ce produit existe et quel probleme il resout>
COMMENT: <etape 1> | <etape 2> | <etape 3>
ATTENTION: <un conseil pratique ou une erreur courante a eviter en une phrase, ou "aucun">

REGLES IMPORTANTES :
- Si tu n'es pas certain a 100% de l'identification, donne ta meilleure hypothese plausible \
plutot que de refuser de repondre.
- NOM, POURQUOI et COMMENT ne doivent JAMAIS etre vides, meme pour un produit de marque tres \
connue (ex: Vaseline, dentifrice, savon, creme...). Donne l'usage general grand public.
- COMMENT doit contenir au moins 2 etapes separees par le caractere |
- Ne mets aucun texte en dehors de ces 4 lignes, aucune balise markdown."""


def parse_identify_text(raw_text):
    def extract(marker, text):
        match = re.search(rf"{marker}\s*:\s*(.+?)(?=\n[A-Z]+\s*:|\Z)", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    name = extract("NOM", raw_text)
    category = extract("CATEGORIE", raw_text)
    why = extract("POURQUOI", raw_text)
    comment_raw = extract("COMMENT", raw_text)
    warning = extract("ATTENTION", raw_text)

    how_steps = [s.strip() for s in comment_raw.split("|") if s.strip()]
    if warning.lower() in ("aucun", "aucune", ""):
        warning = ""

    return {
        "object_name": name,
        "category": category,
        "why": why,
        "how_steps": how_steps,
        "warning": warning,
    }


def identify_object(image_bytes, media_type, user_context):
    client = genai.Client(api_key=get_secret("GEMINI_API_KEY"))
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    user_text = "Identifie cet objet et explique-le."
    if user_context:
        user_text += f" Contexte donne par l'utilisateur : {user_context}"

    response = client.models.generate_content(
        model=VISION_MODEL,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=media_type), user_text],
        config=types.GenerateContentConfig(
            system_instruction=IDENTIFY_PROMPT,
            max_output_tokens=1200,
        ),
    )
    raw_text = (response.text or "").strip()
    data = parse_identify_text(raw_text)

    if not data["object_name"]:
        data["object_name"] = "Objet non identifié clairement"
    if not data["category"]:
        data["category"] = "Inconnu"
    if not data["why"]:
        data["why"] = "Pas assez d'informations trouvées pour expliquer cet objet en détail. Réessaie avec une photo plus nette ou ajoute du contexte."
    if not data["how_steps"]:
        data["how_steps"] = ["Réessaie avec une photo plus nette ou plus de contexte pour obtenir un mode d'emploi détaillé."]

    return data, image_b64
