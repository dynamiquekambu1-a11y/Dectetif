import streamlit as st
from common import t, init_session_state, apply_style, render_lang_selector

st.set_page_config(page_title="À propos", page_icon="ℹ️", layout="centered")

init_session_state()
apply_style()
render_lang_selector()

st.markdown(f'<div class="hero-title">{t("about_title")}</div>', unsafe_allow_html=True)
st.write("")
st.markdown(t("about_text"))
