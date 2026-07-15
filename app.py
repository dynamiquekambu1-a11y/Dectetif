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
from datetime import datetime, date
from google import genai
from google.genai import types

# ----------------------------------------------------------------------------
# CONFIG GENERALE
# ----------------------------------------------------------------------------

st.set_page_config(
    page_title="C'est Quoi Ça ?",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DB_PATH = "scans.db"
FREE_SCANS_PER_MONTH = 3
MODEL_NAME = "gemini-3.1-flash-lite"

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
        }

        .result-card h4 {
            margin-top: 0;
            margin-bottom: 8px;
            font-size: 1.05rem;
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
    conn.commit()
    return conn


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
# APPEL IA (Claude Vision)
# ----------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un expert capable d'identifier n'importe quel objet du quotidien \
à partir d'une photo, même des gadgets obscurs, pièces détachées, objets importés sans notice, \
produits de niche, ou produits de marque connue (cosmetiques, entretien, alimentaire, etc).

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans balises markdown, \
au format exact suivant :

{
  "object_name": "Nom court et clair de l'objet",
  "category": "Categorie en 1-2 mots (ex: Cuisine, Electronique, Beaute, Bricolage)",
  "why": "2 a 3 phrases expliquant pourquoi cet objet existe et quel probleme il resout, en francais simple.",
  "how_steps": ["Etape 1 courte et actionnable", "Etape 2", "Etape 3", "Etape 4 (optionnel)"],
  "warning": "Un conseil de securite ou une erreur courante a eviter, en 1 phrase. Laisse une chaine vide si non pertinent."
}

REGLES IMPORTANTES :
- Les champs "why" et "how_steps" NE DOIVENT JAMAIS etre vides, meme pour un produit de marque \
tres connu (ex: Vaseline, dentifrice, savon...). Explique son usage general comme si tu \
t'adressais a quelqu'un qui ne l'a jamais vu.
- "how_steps" doit toujours contenir au moins 2 etapes concretes.
- Si tu n'es pas certain a 100% de l'identification, donne ta meilleure hypothese plausible \
et remplis quand meme tous les champs en te basant sur cette hypothese.
- Ne mets jamais de texte en dehors du JSON."""


def identify_object(image_bytes, media_type, user_context):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    user_text = "Identifie cet objet."
    if user_context:
        user_text += f" Contexte donne par l'utilisateur : {user_context}"

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=media_type),
            user_text,
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            max_output_tokens=1200,
        ),
    )

    raw_text = (response.text or "").strip()
    # Nettoyage au cas ou le modele ajoute des balises markdown malgre la consigne
    cleaned = re.sub(r"^```json|```$", "", raw_text, flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {
            "object_name": "Objet non identifie clairement",
            "category": "Inconnu",
            "why": "L'IA n'a pas pu structurer sa reponse. Reessaie avec une photo plus nette ou plus de contexte.",
            "how_steps": [],
            "warning": "",
        }

    # Filet de securite : ne jamais laisser un champ vide s'afficher
    if not data.get("why"):
        data["why"] = "Pas assez d'informations trouvées pour expliquer cet objet en détail. Réessaie avec une photo plus nette ou ajoute du contexte."
    if not data.get("how_steps"):
        data["how_steps"] = ["Réessaie avec une photo plus nette ou plus de contexte pour obtenir un mode d'emploi détaillé."]

    return data, image_b64


# ----------------------------------------------------------------------------
# ETAT DE SESSION
# ----------------------------------------------------------------------------

if "view" not in st.session_state:
    st.session_state.view = "scanner"
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------

st.markdown('<div class="hero-title">🔍 C\'est Quoi Ça ?</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Prends une photo. Sais ce que c\'est, pourquoi, et comment t\'en servir — en 10 secondes.</div>',
    unsafe_allow_html=True,
)

total_scans = get_total_scans()
scans_this_month = get_scans_this_month()
remaining = max(0, FREE_SCANS_PER_MONTH - scans_this_month)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown(f'<span class="stat-pill">📦 {total_scans} objets identifiés</span>', unsafe_allow_html=True)
with col_b:
    st.markdown(f'<span class="stat-pill">🎟️ {remaining}/{FREE_SCANS_PER_MONTH} scans gratuits ce mois</span>', unsafe_allow_html=True)

st.write("")

tab_scan, tab_history = st.tabs(["📸 Scanner", "🗂️ Ma collection"])

# ----------------------------------------------------------------------------
# ONGLET SCANNER
# ----------------------------------------------------------------------------

with tab_scan:
    if "GEMINI_API_KEY" not in st.secrets:
        st.error(
            "⚠️ Clé API manquante. Ajoute `GEMINI_API_KEY` dans les secrets "
            "de ton app (Settings → Secrets sur Streamlit Cloud, ou fichier "
            "`.streamlit/secrets.toml` en local). Clé gratuite sur aistudio.google.com."
        )

    uploaded_file = st.file_uploader(
        "Prends ou choisis une photo de l'objet",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    context_input = st.text_input(
        "Contexte (optionnel)",
        placeholder="Ex: reçu de ma tante, acheté sur Temu, trouvé dans le garage...",
    )

    if uploaded_file is not None:
        st.image(uploaded_file, use_container_width=True)

    identify_disabled = uploaded_file is None

    if st.button("🔎 Identifier cet objet", type="primary", disabled=identify_disabled, use_container_width=True):
        if "GEMINI_API_KEY" not in st.secrets:
            st.stop()

        with st.spinner("L'IA regarde ton objet..."):
            image_bytes = uploaded_file.getvalue()
            media_type = uploaded_file.type or "image/jpeg"
            try:
                data, image_b64 = identify_object(image_bytes, media_type, context_input)
                save_scan(context_input, data, image_b64)
                st.session_state.last_result = data
                st.rerun()
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    st.warning("⏳ Trop de scans d'un coup ! Attends environ 30 secondes et réessaie.")
                else:
                    st.error(f"Erreur pendant l'identification : {e}")

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
                <h4>🤔 Pourquoi ça existe</h4>
                <p>{data.get('why', '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        steps_html = "".join(f"<li>{s}</li>" for s in data.get("how_steps", []))
        st.markdown(
            f"""
            <div class="result-card">
                <h4>🛠️ Comment l'utiliser</h4>
                <ol>{steps_html}</ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if data.get("warning"):
            st.markdown(
                f"""
                <div class="result-card">
                    <h4>⚠️ Attention à</h4>
                    <div class="warn-box">{data.get('warning')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Scanner un autre objet", use_container_width=True):
                st.session_state.last_result = None
                st.rerun()
        with col2:
            share_text = (
                f"🔍 {data.get('object_name','')}\n\n"
                f"Pourquoi : {data.get('why','')}\n\n"
                f"Comment l'utiliser :\n" + "\n".join(f"- {s}" for s in data.get("how_steps", []))
            )
            st.download_button(
                "📤 Exporter ce résultat",
                data=share_text,
                file_name="cest_quoi_ca.txt",
                use_container_width=True,
            )

# ----------------------------------------------------------------------------
# ONGLET HISTORIQUE
# ----------------------------------------------------------------------------

with tab_history:
    history = get_history()

    if not history:
        st.info("Aucun objet scanné pour l'instant. Va dans l'onglet Scanner pour commencer !")
    else:
        for row in history:
            scan_id, created_at, name, category, why_text, how_steps_json, warning_text, image_b64 = row
            with st.expander(f"{name}  —  {created_at[:16].replace('T', ' ')}"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if image_b64:
                        st.image(base64.b64decode(image_b64), use_container_width=True)
                with c2:
                    st.markdown(f"**Catégorie :** {category}")
                    st.markdown(f"**Pourquoi :** {why_text}")
                    try:
                        steps = json.loads(how_steps_json)
                    except (json.JSONDecodeError, TypeError):
                        steps = []
                    if steps:
                        st.markdown("**Comment l'utiliser :**")
                        for s in steps:
                            st.markdown(f"- {s}")
                    if warning_text:
                        st.markdown(f"⚠️ {warning_text}")
