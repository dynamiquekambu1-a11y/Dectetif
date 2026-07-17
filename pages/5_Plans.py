import re
import urllib.parse
import streamlit as st
from common import (
    t, init_session_state, apply_style, render_lang_selector,
    PLANS, WHATSAPP_NUMBER, EMAIL_REGEX, is_premium, get_usage_status,
)

st.set_page_config(page_title="Plans", page_icon="⭐", layout="centered")

init_session_state()
apply_style()
render_lang_selector()

st.markdown(f'<div class="hero-title">{t("premium_title")}</div>', unsafe_allow_html=True)
st.write("")

user_email = st.session_state.user_email
user_is_premium, remaining, quota, plan_name = get_usage_status(user_email)

if user_is_premium:
    st.success(t("premium_active_msg", email=user_email, plan=plan_name))
else:
    st.markdown(t("premium_text"))
    st.write("")

    for plan in PLANS:
        quota_txt = t("plan_unlimited") if plan["quota"] is None else t("plan_quota", n=plan["quota"])
        st.markdown(
            f"""
            <div class="result-card">
                <div class="object-name">{plan['name']} — ${plan['price']}/mois</div>
                <p>{quota_txt}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
