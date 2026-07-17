"""
C'est Quoi Ça ? — MVP
Prends une photo d'un objet mystère → l'IA te dit quoi, pourquoi, comment.
Stack : Streamlit + SQLite + Claude Vision (Anthropic API)
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
# CONFIG GENERALE
# ----------------------------------------------------------------------------

LOGO_PATH = "logo.png"
_page_icon = "🔍"
if os.path.exists(LOGO_PATH):
    _page_icon = LOGO_PATH

st.set_page_config(
    page_title="C'est Quoi Ça ?",
    page_icon=_page_icon,
    layout="centered",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# GOOGLE ANALYTICS
# ----------------------------------------------------------------------------

GA_MEASUREMENT_ID = "G-0MJ8GNR9QZ"

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

DB_PATH = "scans.db"
VISION_MODEL = "gemini-3.1-flash-lite"
FREE_SCANS_PER_DAY = 2
WHATSAPP_NUMBER = "27750556027"

PLANS = [
    {"name": "Starter", "price": 5, "quota": 20},
    {"name": "Pro", "price": 10, "quota": 60},
    {"name": "Illimité", "price": 15, "quota": None},
]

# ----------------------------------------------------------------------------
# TRADUCTIONS (FR / EN)
# ----------------------------------------------------------------------------

TRANSLATIONS = {
    "fr": {
        "title": "🔍 C'est Quoi Ça ?",
        "subtitle": "Prends une photo. Sais ce que c'est, pourquoi, et comment t'en servir — en 10 secondes.",
        "stat_scans": "📦 {n} objets identifiés",
        "stat_free": "🎟️ {remaining}/{total} scans gratuits aujourd'hui",
        "tab_scanner": "📸 Scanner",
        "tab_history": "🗂️ Ma collection",
        "tab_info": "ℹ️ Infos",
        "uploader_label": "Prends ou choisis une photo de l'objet",
        "context_label": "Contexte (optionnel)",
        "context_placeholder": "Ex: reçu de ma tante, acheté sur Temu, trouvé dans le garage...",
        "missing_key": "⚠️ Clé API manquante. Ajoute `GEMINI_API_KEY` dans les secrets de ton app (Settings → Secrets sur Streamlit Cloud). Clé gratuite sur aistudio.google.com.",
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
        "history_empty": "Aucun objet scanné pour l'instant. Va dans l'onglet Scanner pour commencer !",
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
        "email_gate_title": "Bienvenue 👋",
        "email_gate_text": "Entre ton email pour commencer (ça nous sert juste à suivre tes scans gratuits, pas de mot de passe).",
        "email_input_label": "Ton email",
        "email_submit": "Continuer",
        "email_invalid": "Entre un email valide pour continuer.",
        "premium_badge": "⭐ Illimité",
        "premium_title": "🔓 Passer en illimité",
        "premium_text": "Débloque les scans illimités et le suivi complet de ta collection.",
        "premium_instructions": (
            "**Comment payer par M-Pesa :**\n\n"
            "1. Envoie **[montant à définir]** au **[ton numéro M-Pesa]**\n"
            "2. Note le code de transaction reçu par SMS\n"
            "3. Colle-le ci-dessous avec ton email\n\n"
            "Ton compte sera débloqué manuellement sous 24h."
        ),
        "transaction_code_label": "Code de transaction M-Pesa",
        "submit_claim_button": "Envoyer pour vérification",
        "claim_submitted_msg": "✅ Reçu ! Ton compte sera débloqué sous 24h après vérification.",
        "admin_title": "🔐 Administration",
        "admin_password_label": "Mot de passe admin",
        "admin_wrong_password": "Mot de passe incorrect.",
        "admin_no_claims": "Aucune demande en attente.",
        "admin_approve_button": "✅ Marquer comme payé",
        "admin_claim_approved": "Compte activé !",
        "home_step1": "Prends une photo de l'objet",
        "home_step2": "L'IA l'analyse en quelques secondes",
        "home_step3": "Tu obtiens quoi, pourquoi, comment",
        "home_mock_category": "BEAUTÉ",
        "home_mock_name": "Exemple : Vaseline",
        "home_mock_why": "\"Hydrate et protège la peau en formant une barrière contre l'humidité...\"",
        "home_cta": "🚀 Essayer maintenant",
        "back_home": "← Accueil",
        "already_paid_title": "Déjà payé ?",
        "already_paid_button": "Vérifier mon email",
        "not_premium_yet": "Pas encore activé — patiente le temps qu'on vérifie ton paiement.",
        "premium_active_msg": "✅ Compte illimité actif ({email})",
        "need_email_text": "Entre ton email pour générer un résultat (ça sert juste à compter tes scans gratuits, pas de mot de passe).",
        "plan_quota": "{n} scans/mois",
        "plan_unlimited": "Illimité",
        "pay_button": "💬 Payer via WhatsApp",
        "admin_activate_title": "Activer un compte manuellement",
        "admin_plan_label": "Plan",
    },
    "en": {
        "title": "🔍 What Is This?",
        "subtitle": "Take a photo. Know what it is, why it exists, and how to use it — in 10 seconds.",
        "stat_scans": "📦 {n} objects identified",
        "stat_free": "🎟️ {remaining}/{total} free scans today",
        "tab_scanner": "📸 Scanner",
        "tab_history": "🗂️ My collection",
        "tab_info": "ℹ️ Info",
        "uploader_label": "Take or choose a photo of the object",
        "context_label": "Context (optional)",
        "context_placeholder": "E.g.: gift from a relative, bought on Temu, found in the garage...",
        "missing_key": "⚠️ Missing API key. Add `GEMINI_API_KEY` to your app secrets (Settings → Secrets on Streamlit Cloud). Free key at aistudio.google.com.",
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
        "history_empty": "No object scanned yet. Head to the Scanner tab to get started!",
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
        "email_gate_title": "Welcome 👋",
        "email_gate_text": "Enter your email to get started (only used to track your free scans, no password needed).",
        "email_input_label": "Your email",
        "email_submit": "Continue",
        "email_invalid": "Enter a valid email to continue.",
        "premium_badge": "⭐ Unlimited",
        "premium_title": "🔓 Go unlimited",
        "premium_text": "Unlock unlimited scans and full collection tracking.",
        "premium_instructions": (
            "**How to pay via M-Pesa:**\n\n"
            "1. Send **[amount to set]** to **[your M-Pesa number]**\n"
            "2. Note the transaction code you receive by SMS\n"
            "3. Paste it below with your email\n\n"
            "Your account will be unlocked manually within 24h."
        ),
        "transaction_code_label": "M-Pesa transaction code",
        "submit_claim_button": "Submit for verification",
        "claim_submitted_msg": "✅ Received! Your account will be unlocked within 24h after verification.",
        "admin_title": "🔐 Admin",
        "admin_password_label": "Admin password",
        "admin_wrong_password": "Wrong password.",
        "admin_no_claims": "No pending requests.",
        "admin_approve_button": "✅ Mark as paid",
        "admin_claim_approved": "Account activated!",
        "home_step1": "Take a photo of the object",
        "home_step2": "The AI analyzes it in seconds",
        "home_step3": "You get what, why, how",
        "home_mock_category": "BEAUTY",
        "home_mock_name": "Example: Vaseline",
        "home_mock_why": "\"Hydrates and protects skin by forming a moisture barrier...\"",
        "home_cta": "🚀 Try it now",
        "back_home": "← Home",
        "already_paid_title": "Already paid?",
        "already_paid_button": "Check my email",
        "not_premium_yet": "Not activated yet — please wait while we verify your payment.",
        "premium_active_msg": "✅ Unlimited account active ({email})",
        "need_email_text": "Enter your email to generate a result (only used to track your free scans, no password needed).",
        "plan_quota": "{n} scans/month",
        "plan_unlimited": "Unlimited",
        "pay_button": "💬 Pay via WhatsApp",
        "admin_activate_title": "Activate an account manually",
        "admin_plan_label": "Plan",
    },
}


def t(key, **kwargs):
    lang = st.session_state.get("lang", "fr")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["fr"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# ----------------------------------------------------------------------------
# STYLE (design chaleureux, mobile-first)
# ----------------------------------------------------------------------------

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
        }

        .result-card p,
        .result-card li,
        .result-card ol,
        .result-card ul {
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

        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: #FFF1E6;
            padding: 5px;
            border-radius: 999px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 8px 18px;
            font-weight: 600;
            color: #9A6C4F;
        }

        .stTabs [aria-selected="true"] {
            background: #FFFFFF !important;
            color: #1F2937 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .history-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 4px;
            border-bottom: 1px solid #F1F1F1;
        }

        .warn-box {
            background: #FFF7ED;
            border-left: 4px solid #F97316;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 0.92rem;
            color: #7C2D12;
        }

        /* Correction globale : force un texte lisible partout, meme en theme sombre */
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMarkdownContainer"] ol,
        [data-testid="stMarkdownContainer"] ul,
        [data-testid="stMarkdownContainer"] table,
        [data-testid="stMarkdownContainer"] th,
        [data-testid="stMarkdownContainer"] td,
        [data-testid="stMarkdownContainer"] strong,
        [data-testid="stMarkdownContainer"] span,
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

        .step-emoji {
            font-size: 1.8rem;
        }

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

        .step-arrow {
            color: #FDBA74;
            font-size: 1.3rem;
        }

        .mock-result {
            background: #FFFFFF;
            border-radius: 20px;
            padding: 20px 22px;
            border: 1px dashed #FDBA74;
            color: #1F2937;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    # Migration douce : ajoute les colonnes si la base existait deja sans elles
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
    """Retourne (plan, quota) si premium, sinon None. quota=None = illimite."""
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
    """Enregistre une visite une seule fois par session utilisateur."""
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


def get_scans_this_month(email):
    conn = get_conn()
    month_prefix = date.today().strftime("%Y-%m")
    count = conn.execute(
        "SELECT COUNT(*) FROM scans WHERE email = ? AND created_at LIKE ?",
        (email, f"{month_prefix}%"),
    ).fetchone()[0]
    conn.close()
    return count


def get_total_scans():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
    conn.close()
    return count


# ----------------------------------------------------------------------------
# APPEL IA — 2 ETAPES (vision pour identifier, texte pour expliquer)
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
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
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

    # Filet de securite : ne jamais laisser un champ vide s'afficher
    if not data["object_name"]:
        data["object_name"] = "Objet non identifié clairement"
    if not data["category"]:
        data["category"] = "Inconnu"
    if not data["why"]:
        data["why"] = "Pas assez d'informations trouvées pour expliquer cet objet en détail. Réessaie avec une photo plus nette ou ajoute du contexte."
    if not data["how_steps"]:
        data["how_steps"] = ["Réessaie avec une photo plus nette ou plus de contexte pour obtenir un mode d'emploi détaillé."]

    return data, image_b64


# ----------------------------------------------------------------------------
# ETAT DE SESSION
# ----------------------------------------------------------------------------

EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

if "view" not in st.session_state:
    st.session_state.view = "scanner"
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "lang" not in st.session_state:
    st.session_state.lang = "fr"
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

log_visit()

user_email = st.session_state.user_email


def get_usage_status(email):
    """Retourne (is_premium, remaining, quota) ; quota=None => illimite."""
    if not email:
        return False, FREE_SCANS_PER_DAY, FREE_SCANS_PER_DAY
    info = get_premium_info(email)
    if info:
        plan, quota = info
        if quota is None:
            return True, None, None
        used = get_scans_this_month(email)
        return True, max(0, quota - used), quota
    used = get_scans_today(email)
    return False, max(0, FREE_SCANS_PER_DAY - used), FREE_SCANS_PER_DAY


user_is_premium, remaining, quota = get_usage_status(user_email)

# ----------------------------------------------------------------------------
# SIDEBAR (navigation + infos + plans + admin)
# ----------------------------------------------------------------------------

with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=48)
    st.markdown(f"**{t('title')}**")

    if st.button(t("tab_scanner"), use_container_width=True):
        st.session_state.view = "scanner"
        st.rerun()
    if st.button(t("tab_history"), use_container_width=True):
        st.session_state.view = "collection"
        st.rerun()

    st.markdown("---")

    lang_choice = st.selectbox(
        t("lang_label"),
        options=["fr", "en"],
        format_func=lambda x: "🇫🇷 Français" if x == "fr" else "🇬🇧 English",
        index=0 if st.session_state.lang == "fr" else 1,
    )
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

    with st.expander(t("about_title")):
        st.markdown(t("about_text"))

    with st.expander(t("privacy_title")):
        st.markdown(t("privacy_text"))

    with st.expander(t("terms_title")):
        st.markdown(t("terms_text"))

    with st.expander(t("premium_title")):
        if user_is_premium:
            st.success(t("premium_active_msg", email=user_email))
        else:
            st.markdown(t("premium_text"))
            for plan in PLANS:
                quota_txt = t("plan_unlimited") if plan["quota"] is None else t("plan_quota", n=plan["quota"])
                st.markdown(f"**{plan['name']} — ${plan['price']}/mois** · {quota_txt}")
                wa_message = f"Bonjour, je veux le plan {plan['name']} (${plan['price']}) pour {t('title')}"
                wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(wa_message)}"
                st.link_button(t("pay_button"), wa_url, use_container_width=True)
                st.write("")

            st.markdown("---")
            st.markdown(f"**{t('already_paid_title')}**")
            check_email = st.text_input(t("email_input_label"), key="check_email_input", placeholder="toi@exemple.com")
            if st.button(t("already_paid_button"), use_container_width=True):
                clean_check_email = check_email.strip().lower()
                if is_premium(clean_check_email):
                    st.session_state.user_email = clean_check_email
                    st.rerun()
                else:
                    st.info(t("not_premium_yet"))

    with st.expander(t("stats_title")):
        stats_rows = get_stats_by_year()
        if not stats_rows:
            st.write("—")
        else:
            st.markdown(
                f"| {t('stats_year')} | {t('stats_visits')} | {t('stats_scans')} |\n"
                f"|---|---|---|\n"
                + "\n".join(f"| {y} | {v} | {s} |" for y, v, s in stats_rows)
            )

    if "ADMIN_PASSWORD" in st.secrets:
        with st.expander(t("admin_title")):
            admin_pw = st.text_input(t("admin_password_label"), type="password", key="admin_pw_input")
            if admin_pw:
                if admin_pw == st.secrets["ADMIN_PASSWORD"]:
                    st.markdown(f"**{t('admin_activate_title')}**")
                    activate_email = st.text_input(t("email_input_label"), key="activate_email_input")
                    plan_names = [p["name"] for p in PLANS]
                    chosen_plan_name = st.selectbox(t("admin_plan_label"), plan_names, key="activate_plan_select")
                    chosen_plan = next(p for p in PLANS if p["name"] == chosen_plan_name)
                    if st.button(t("admin_approve_button"), use_container_width=True):
                        clean_activate_email = activate_email.strip().lower()
                        if re.match(EMAIL_REGEX, clean_activate_email):
                            activate_premium(clean_activate_email, chosen_plan["name"], chosen_plan["quota"])
                            st.success(t("admin_claim_approved"))
                        else:
                            st.warning(t("email_invalid"))
                else:
                    st.error(t("admin_wrong_password"))

# ----------------------------------------------------------------------------
# HEADER (zone principale)
# ----------------------------------------------------------------------------

if os.path.exists(LOGO_PATH):
    col_logo_l, col_logo_c, col_logo_r = st.columns([1, 1, 1])
    with col_logo_c:
        st.image(LOGO_PATH, use_container_width=True)

st.markdown(f'<div class="hero-title">{t("title")}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="hero-sub">{t("subtitle")}</div>', unsafe_allow_html=True)

total_scans = get_total_scans()
col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f'<span class="stat-pill">{t("stat_scans", n=total_scans)}</span>', unsafe_allow_html=True)
with col_b:
    if user_is_premium and quota is None:
        st.markdown(f'<span class="stat-pill">{t("premium_badge")}</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="stat-pill">{t("stat_free", remaining=remaining, total=quota)}</span>', unsafe_allow_html=True)

st.write("")

# ----------------------------------------------------------------------------
# VUE SCANNER (ecran principal par defaut)
# ----------------------------------------------------------------------------

if st.session_state.view == "scanner":
    if get_total_scans() == 0 or not user_email:
        def find_step_image(n):
            for ext in ("jpg", "jpeg", "png"):
                path = f"step{n}.{ext}"
                if os.path.exists(path):
                    return path
            return None

        step_images = [find_step_image(1), find_step_image(2), find_step_image(3)]
        step_texts = [t("home_step1"), t("home_step2"), t("home_step3")]

        if all(step_images):
            cols = st.columns(3)
            for col, img_path, txt in zip(cols, step_images, step_texts):
                with col:
                    st.image(img_path, use_container_width=True)
                    st.caption(txt)
        else:
            step_html = """
            <div class="step-row">
                <div class="step-card">
                    <div class="step-emoji">📷</div>
                    <div class="step-num">1</div>
                    <div class="step-text">{s1}</div>
                </div>
                <div class="step-arrow">→</div>
                <div class="step-card">
                    <div class="step-emoji">🤖</div>
                    <div class="step-num">2</div>
                    <div class="step-text">{s2}</div>
                </div>
                <div class="step-arrow">→</div>
                <div class="step-card">
                    <div class="step-emoji">✅</div>
                    <div class="step-num">3</div>
                    <div class="step-text">{s3}</div>
                </div>
            </div>
            """.format(s1=t("home_step1"), s2=t("home_step2"), s3=t("home_step3"))
            st.markdown(step_html, unsafe_allow_html=True)
        st.write("")

    if "GEMINI_API_KEY" not in st.secrets:
        st.error(t("missing_key"))

    uploaded_file = st.file_uploader(
        t("uploader_label"),
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    context_input = st.text_input(
        t("context_label"),
        placeholder=t("context_placeholder"),
    )

    if uploaded_file is not None:
        st.image(uploaded_file, use_container_width=True)

    if not user_email:
        st.info(t("need_email_text"))
        gate_email = st.text_input(t("email_input_label"), placeholder="toi@exemple.com", key="gate_email_input")
        if st.button(t("email_submit"), type="primary", use_container_width=True):
            clean_gate_email = gate_email.strip().lower()
            if re.match(EMAIL_REGEX, clean_gate_email):
                st.session_state.user_email = clean_gate_email
                st.rerun()
            else:
                st.warning(t("email_invalid"))
    else:
        identify_disabled = uploaded_file is None or (not user_is_premium and remaining is not None and remaining <= 0)

        if not user_is_premium and remaining is not None and remaining <= 0 and uploaded_file is not None:
            st.warning(t("stat_free", remaining=0, total=quota))

        if st.button(t("identify_button"), type="primary", disabled=identify_disabled, use_container_width=True):
            if "GEMINI_API_KEY" not in st.secrets:
                st.stop()

            with st.spinner(t("spinner_text")):
                image_bytes = uploaded_file.getvalue()
                media_type = uploaded_file.type or "image/jpeg"
                try:
                    data, image_b64 = identify_object(image_bytes, media_type, context_input)
                    save_scan(context_input, data, image_b64, user_email)
                    st.session_state.last_result = data
                    st.rerun()
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        st.warning(t("rate_limit_warning"))
                    else:
                        st.error(t("generic_error", e=e))

    if st.session_state.last_result:
        data = st.session_state.last_result
        st.markdown("---")
        st.markdown(
            f"""
            <div class="result-card">
                <div class="object-category">{data.get('category', '')}</div>
                <div class="object-name">{data.get('object_name', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="result-card">
                <h4>{t('why_header')}</h4>
                <p>{data.get('why', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        steps_html = "".join(f"<li>{s}</li>" for s in data.get("how_steps", []))
        st.markdown(
            f"""
            <div class="result-card">
                <h4>{t('how_header')}</h4>
                <ol>{steps_html}</ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if data.get("warning"):
            st.markdown(
                f"""
                <div class="result-card">
                    <h4>{t('warning_header')}</h4>
                    <div class="warn-box">{data.get('warning')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("scan_another"), use_container_width=True):
                st.session_state.last_result = None
                st.rerun()
        with col2:
            share_text = (
                f"🔍 {data.get('object_name','')}\n\n"
                f"{t('export_why')} : {data.get('why','')}\n\n"
                f"{t('export_how')} :\n" + "\n".join(f"- {s}" for s in data.get("how_steps", []))
            )
            st.download_button(
                t("export_button"),
                data=share_text,
                file_name="cest_quoi_ca.txt",
                use_container_width=True,
            )

# ----------------------------------------------------------------------------
# VUE COLLECTION
# ----------------------------------------------------------------------------

elif st.session_state.view == "collection":
    if not user_email:
        st.info(t("history_empty"))
    else:
        history = get_history(user_email)
        if not history:
            st.info(t("history_empty"))
        else:
            for row in history:
                scan_id, created_at, name, category, why_text, how_steps_json, warning_text, image_b64 = row
                with st.expander(f"{name}  —  {created_at[:16].replace('T', ' ')}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        if image_b64:
                            st.image(base64.b64decode(image_b64), use_container_width=True)
                    with c2:
                        st.markdown(f"{t('history_category')} {category}")
                        st.markdown(f"{t('history_why')} {why_text}")
                        try:
                            steps = json.loads(how_steps_json)
                        except (json.JSONDecodeError, TypeError):
                            steps = []
                        if steps:
                            st.markdown(t("history_how"))
                            for s in steps:
                                st.markdown(f"- {s}")
                        if warning_text:
                            st.markdown(f"⚠️ {warning_text}")
