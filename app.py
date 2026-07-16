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
VISION_MODEL = "gemini-3.1-flash-lite"
EXPLAIN_MODEL = "gemini-3.5-flash"

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
# APPEL IA — 2 ETAPES (vision pour identifier, texte pour expliquer)
# ----------------------------------------------------------------------------

VISION_PROMPT = """Tu es un expert capable d'identifier n'importe quel objet du quotidien \
a partir d'une photo, meme des gadgets obscurs, pieces detachees, objets importes sans notice, \
produits de niche, ou produits de marque connue.

Si tu n'es pas certain a 100%, donne ta meilleure hypothese plausible plutot que de refuser."""

VISION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "object_name": {"type": "STRING", "description": "Nom court et clair de l'objet (marque si visible)"},
        "category": {"type": "STRING", "description": "Categorie en 1-2 mots (ex: Cuisine, Electronique, Beaute, Bricolage)"},
    },
    "required": ["object_name", "category"],
}

EXPLAIN_PROMPT = """Tu es un assistant qui explique a quoi sert un objet ou un produit et comment \
l'utiliser, pour quelqu'un qui le decouvre pour la premiere fois. C'est une question generale de \
connaissance grand public, pas un avis medical.

Utilise la recherche Google pour trouver des informations reelles et a jour sur ce produit \
precis (notice officielle, usage courant, avis, precautions), surtout s'il s'agit d'une marque \
connue (ex: Vaseline, Nivea, un medicament courant, un gadget vendu en ligne...).

Reponds UNIQUEMENT dans ce format texte exact, avec ces marqueurs, rien avant ni apres :

POURQUOI: <2 a 3 phrases expliquant pourquoi ce produit existe et quel probleme il resout>
COMMENT: <etape 1> | <etape 2> | <etape 3>
ATTENTION: <un conseil pratique ou une erreur courante a eviter en une phrase, ou "aucun">

REGLES IMPORTANTES :
- POURQUOI et COMMENT ne doivent JAMAIS etre vides, meme pour un produit tres connu.
- COMMENT doit contenir au moins 2 etapes separees par le caractere |
- Ne mets aucun texte en dehors de ces 3 lignes."""


def call_gemini_json(client, model, system_prompt, contents, max_tokens, schema=None):
    config_kwargs = dict(
        system_instruction=system_prompt,
        max_output_tokens=max_tokens,
    )
    if schema:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = schema

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    raw_text = (response.text or "").strip()
    cleaned = re.sub(r"^```json|```$", "", raw_text, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {}


def call_gemini_grounded(client, model, system_prompt, contents, max_tokens):
    """Appel avec recherche Google activee (gratuite) — pas de mode JSON, l'outil de
    recherche et le JSON strict ne sont pas compatibles ensemble sur l'API Gemini."""
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return (response.text or "").strip()


def parse_explain_text(raw_text):
    def extract(marker, text):
        match = re.search(rf"{marker}\s*:\s*(.+?)(?=\n[A-Z]+\s*:|\Z)", text, re.DOTALL)
        return match.group(1).strip() if match else ""

    why = extract("POURQUOI", raw_text)
    comment_raw = extract("COMMENT", raw_text)
    warning = extract("ATTENTION", raw_text)

    how_steps = [s.strip() for s in comment_raw.split("|") if s.strip()]
    if warning.lower() in ("aucun", "aucune", ""):
        warning = ""

    return {"why": why, "how_steps": how_steps, "warning": warning}


def identify_object(image_bytes, media_type, user_context):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    user_text = "Identifie cet objet."
    if user_context:
        user_text += f" Contexte donne par l'utilisateur : {user_context}"

    # Etape 1 : identification visuelle (modele rapide, gros quota gratuit, schema force)
    vision_data = call_gemini_json(
        client,
        VISION_MODEL,
        VISION_PROMPT,
        [types.Part.from_bytes(data=image_bytes, mime_type=media_type), user_text],
        max_tokens=300,
        schema=VISION_SCHEMA,
    )

    object_name = vision_data.get("object_name") or "Objet non identifie clairement"
    category = vision_data.get("category") or "Inconnu"

    # Etape 2 : explication avec recherche Google gratuite pour des infos reelles
    explain_input = f"Objet : {object_name}. Categorie : {category}."
    if user_context:
        explain_input += f" Contexte : {user_context}."

    raw_explain = call_gemini_grounded(
        client,
        EXPLAIN_MODEL,
        EXPLAIN_PROMPT,
        explain_input,
        max_tokens=1000,
    )
    explain_data = parse_explain_text(raw_explain)

    data = {
        "object_name": object_name,
        "category": category,
        "why": explain_data.get("why", ""),
        "how_steps": explain_data.get("how_steps", []),
        "warning": explain_data.get("warning", ""),
    }

    # Filet de securite : ne jamais laisser un champ vide s'afficher
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
