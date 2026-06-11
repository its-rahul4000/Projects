import streamlit as st
from config.settings import APP_NAME
from services.user_service import register_it_owner


def render_register_page(db):
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            f"""
            <div class="login-card">
              <div class="login-logo">🛡️</div>
              <div class="login-title">IT Owner Registration</div>
              <div class="login-sub">{APP_NAME}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="info-box">'
            "Register your IT Owner account. A temporary password will be generated "
            "and emailed to you (if SMTP is configured). You must change it on first login."
            "</div>",
            unsafe_allow_html=True,
        )

        with st.form("register_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                max_chars=100,
                placeholder="Choose a unique username (min 3 chars)",
            )
            email = st.text_input(
                "Email Address",
                max_chars=254,
                placeholder="your@company.com",
            )
            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not username.strip():
                st.error("Username is required.")
            elif not email.strip():
                st.error("Email address is required.")
            else:
                with st.spinner("Creating account..."):
                    ok, message, temp_password = register_it_owner(
                        username.strip(), email.strip(), db
                    )

                if ok:
                    st.success(message)
                    if temp_password:
                        # Email failed — show temp password for admin to relay
                        st.markdown(
                            '<div class="warn-box">'
                            "<strong>Action required:</strong> SMTP is not configured or delivery failed. "
                            "Please copy the temporary password below and share it securely with the new user."
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="temp-pass-box">{temp_password}</div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(
                            "This password is shown once. "
                            "The user must change it immediately on first login."
                        )
                    else:
                        st.markdown(
                            '<div class="success-box">'
                            "A temporary password has been sent to the registered email address. "
                            "The user should sign in and change it immediately."
                            "</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.error(message)

        st.divider()
        if st.button("Back to Sign In", use_container_width=True):
            st.session_state["page"] = "login"
            st.rerun()
