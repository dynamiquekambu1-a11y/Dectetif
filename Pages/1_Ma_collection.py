import json
import base64
import streamlit as st
from common import t, init_session_state, apply_style, render_lang_selector, get_history

st.set_page_config(page_title="Ma collection", page_icon="🗂️", layout="centered")

init_session_state()
apply_style()
render_lang_selector()

st.markdown(f'<div class="hero-title">{t("nav_collection")}</div>', unsafe_allow_html=True)
st.write("")

user_email = st.session_state.user_email

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
