import streamlit as st
from common import t, init_session_state, apply_style, render_lang_selector

st.set_page_config(page_title="Confidentialité", page_icon="🔒", layout="centered")

init_session_state()
apply_style()
render_lang_selector()

st.markdown(f'<div class="hero-title">{t("privacy_title")}</div>', unsafe_allow_html=True)
st.write("")
st.markdown(t("privacy_text"))
