import re
import streamlit as st
from common import (
    t, init_session_state, apply_style, render_lang_selector,
    get_stats_by_year, has_secret, get_secret, EMAIL_REGEX, PLANS, activate_premium,
)

st.set_page_config(page_title="Paramètres", page_icon="⚙️", layout="centered")

init_session_state()
apply_style()
render_lang_selector()

st.markdown(f'<div class="hero-title">{t("nav_settings")}</div>', unsafe_allow_html=True)
st.write("")

st.markdown(f"### {t('stats_title')}")
stats_rows = get_stats_by_year()
if not stats_rows:
    st.write("—")
else:
    st.markdown(
        f"| {t('stats_year')} | {t('stats_visits')} | {t('stats_scans')} |\n"
        f"|---|---|---|\n"
        + "\n".join(f"| {y} | {v} | {s} |" for y, v, s in stats_rows)
    )

if has_secret("ADMIN_PASSWORD"):
    st.markdown("---")
    st.markdown(f"### {t('admin_title')}")
    admin_pw = st.text_input(t("admin_password_label"), type="password", key="admin_pw_input")
    if admin_pw:
        if admin_pw == get_secret("ADMIN_PASSWORD"):
            st.markdown(f"**{t('admin_activate_title')}**")
            activate_email = st.text_input(t("email_input_label"), key="activate_email_input")
            plan_names = [p["name"] for p in PLANS]
            chosen_plan_name = st.selectbox(t("admin_plan_label"), plan_names, key="activate_plan_select")
            chosen_plan = next(p for p in PLANS if p["name"] == chosen_plan_name)
            if st.button(t("admin_approve_button"), use_container_width=True):
                clean_activate_email = activate_email.strip().lower()
                if re.match(EMAIL_REGEX, clean_activate_email):
                    activate_premium(clean_activate_email, chosen_plan["name"], chosen_plan["quota"])
                    st.success(t("admin_claim_approved"))
                else:
                    st.warning(t("email_invalid"))
        else:
            st.error(t("admin_wrong_password"))
