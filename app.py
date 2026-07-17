"""
C'est Quoi Ça ? — Routeur principal
Definit l'ordre d'affichage du menu lateral : logo + langue d'abord,
puis la navigation entre les pages en dessous.
"""

import os
import streamlit as st
from common import LOGO_PATH, t, init_session_state, apply_style, render_lang_selector

st.set_page_config(
    page_title="C'est Quoi Ça ?",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🔍",
    layout="centered",
)

init_session_state()
apply_style()

# Logo + selecteur de langue affiches EN PREMIER dans le menu lateral
render_lang_selector()

# Navigation affichee APRES (donc en dessous du logo/langue)
pages = [
    st.Page("pages/0_Scanner.py", title=t("nav_scanner"), icon="📸", default=True),
    st.Page("pages/1_Ma_collection.py", title=t("nav_collection"), icon="🗂️"),
    st.Page("pages/2_A_propos.py", title=t("nav_about"), icon="ℹ️"),
    st.Page("pages/3_Confidentialite.py", title=t("nav_privacy"), icon="🔒"),
    st.Page("pages/4_Conditions.py", title=t("nav_terms"), icon="📄"),
    st.Page("pages/5_Plans.py", title=t("nav_plans"), icon="⭐"),
    st.Page("pages/6_Parametres.py", title=t("nav_settings"), icon="⚙️"),
]

pg = st.navigation(pages, position="sidebar")
pg.run()
