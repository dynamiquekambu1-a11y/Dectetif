"""
C'est Quoi Ça ? — Page Scanner (page principale)
"""

import os
import re
import streamlit as st
from common import (
    LOGO_PATH, EMAIL_REGEX, t, init_session_state, apply_style,
    render_lang_selector, log_visit, get_total_scans, get_usage_status,
    has_secret, identify_object, save_scan,
)

st.set_page_config(
    page_title="C'est Quoi Ça ?",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "🔍",
    layout="centered",
)

init_session_state()
apply_style()
render_lang_selector()
log_visit()

user_email = st.session_state.user_email
user_is_premium, remaining, quota, plan_name = get_usage_status(user_email)

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------

if os.path.exists(LOGO_PATH):
    col_l, col_c, col_r = st.columns([1, 1, 1])
    with col_c:
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
# ILLUSTRATION "COMMENT CA MARCHE" (tant que rien n'a ete scanne)
# ----------------------------------------------------------------------------

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

# ----------------------------------------------------------------------------
# FORMULAIRE SCANNER
# ----------------------------------------------------------------------------

if not has_secret("GEMINI_API_KEY"):
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
        if not has_secret("GEMINI_API_KEY"):
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

# ----------------------------------------------------------------------------
# RESULTAT
# ----------------------------------------------------------------------------

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
