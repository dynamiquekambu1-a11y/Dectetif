import streamlit as st
from common import t, init_session_state, apply_style


init_session_state()
apply_style()

st.markdown(f'<div class="hero-title">{t("terms_title")}</div>', unsafe_allow_html=True)
st.write("")
st.markdown(t("terms_text"))
