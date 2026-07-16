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
from datetime import datetime, date
from google import genai
from google.genai import types

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
    initial_sidebar_state="collapsed",
)

DB_PATH = "scans.db"
FREE_SCANS_PER_MONTH = 3
VISION_MODEL = "gemini-3.1-flash-lite"

# ----------------------------------------------------------------------------
# TRADUCTIONS (FR / EN)
# ----------------------------------------------------------------------------

TRANSLATIONS = {
    "fr": {
        "title": "🔍 C'est Quoi Ça ?",
        "subtitle": "Prends une photo. Sais ce que c'est, pourquoi, et comment t'en servir — en 10 secondes.",
        "stat_scans": "📦 {n} objets identifiés",
        "stat_free": "🎟️ {remaining}/{total} scans gratuits ce mois",
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
    },
    "en": {
        "title": "🔍 What Is This?",
        "subtitle": "Take a photo. Know what it is, why it exists, and how to use it — in 10 seconds.",
        "stat_scans": "📦 {n} objects identified",
        "stat_free": "🎟️ {remaining}/{total} free scans this month",
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
        #MainMenu, footer, header {visibility: hidden;}

        .stApp {
            background: linear-gradient(180deg, #FFF8F0 0%, #FFFFFF 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 680px;
        }

        .hero-title {
            font-size: 2.1rem;
            font-weight: 800;
            text-align: center;
            color: #1F2937;
            margin-bottom: 0.2rem;
        }

        .hero-sub {
            text-align: center;
            color: #6B7280;
            font-size: 1rem;
            margin-bottom: 1.6rem;
        }

        .stat-pill {
            display: inline-block;
            background: #FFF1E6;
            color: #C2410C;
            border-radius: 999px;
            padding: 6px 16px;
            font-weight: 600;
            font-size: 0.85rem;
            margin: 2px 6px 2px 0;
        }

        .result-card {
            background: #FFFFFF;
            border-radius: 18px;
            padding: 22px 22px;
            margin-bottom: 16px;
            box-shadow: 0 2px 14px rgba(0,0,0,0.06);
            border: 1px solid #F1F1F1;
            color: #1F2937;
        }

        .result-card p,
        .result-card li,
        .result-card ol,
        .result-card ul {
            color: #1F2937;
        }

        .result-card h4 {
            margin-top: 0;
            margin-bottom: 8px;
            font-size: 1.05rem;
            color: #1F2937;
        }

        .object-name {
            font-size: 1.6rem;
            font-weight: 800;
            color: #111827;
            margin-bottom: 0;
        }

        .object-category {
            color: #F97316;
            font-weight: 600;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 14px;
        }

        div.stButton > button {
            border-radius: 999px;
            font-weight: 700;
            padding: 0.6rem 1.4rem;
            border: none;
        }

        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #F97316, #EA580C);
            color: white;
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
            image_b64 TEXT
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
    conn.commit()
    return conn


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


def save_scan(context, data, image_b64):
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO scans (created_at, context, object_name, category, why_text, how_steps, warning_text, image_b64)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        ),
    )
    conn.commit()
    conn.close()


def get_history(limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, created_at, object_name, category, why_text, how_steps, warning_text, image_b64 "
        "FROM scans ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def get_scans_this_month():
    conn = get_conn()
    month_prefix = date.today().strftime("%Y-%m")
    count = conn.execute(
        "SELECT COUNT(*) FROM scans WHERE created_at LIKE ?",
        (f"{month_prefix}%",),
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

if "view" not in st.session_state:
    st.session_state.view = "scanner"
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "lang" not in st.session_state:
    st.session_state.lang = "fr"

log_visit()

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------

col_logo, col_lang = st.columns([3, 1])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=64)
with col_lang:
    lang_choice = st.selectbox(
        t("lang_label"),
        options=["fr", "en"],
        format_func=lambda x: "🇫🇷 Français" if x == "fr" else "🇬🇧 English",
        index=0 if st.session_state.lang == "fr" else 1,
        label_visibility="collapsed",
    )
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

st.markdown(f'<div class="hero-title">{t("title")}</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="hero-sub">{t("subtitle")}</div>',
    unsafe_allow_html=True,
)

total_scans = get_total_scans()
scans_this_month = get_scans_this_month()
remaining = max(0, FREE_SCANS_PER_MONTH - scans_this_month)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f'<span class="stat-pill">{t("stat_scans", n=total_scans)}</span>', unsafe_allow_html=True)
with col_b:
    st.markdown(f'<span class="stat-pill">{t("stat_free", remaining=remaining, total=FREE_SCANS_PER_MONTH)}</span>', unsafe_allow_html=True)

st.write("")

tab_scan, tab_history, tab_info = st.tabs([t("tab_scanner"), t("tab_history"), t("tab_info")])

# ----------------------------------------------------------------------------
# ONGLET SCANNER
# ----------------------------------------------------------------------------

with tab_scan:
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

    identify_disabled = uploaded_file is None

    if st.button(t("identify_button"), 
