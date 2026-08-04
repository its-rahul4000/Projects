import streamlit as st
from config.settings import APP_NAME
from services.user_service import register_it_owner


def render_register_page(db):
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            f"""<div class="login-card">
              <div class="login-logo">🛡️</div>
              <div class="login-title">Cybersecurity Log Intelligence</div>
              <div class="login-sub">IT Owner Registration</div>
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="info-box">'
            "Register your IT Owner account. A temporary password will be generated. "
            "Sign in with it to set your own password — your account is activated once you do."
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
                width='stretch',
                type="primary",
            )

        if submitted:
            if not username.strip():
                st.error("Username is required.")
            elif not email.strip():
                st.error("Email address is required.")
            else:
                with st.spinner("Submitting registration..."):
                    ok, message, temp_password = register_it_owner(
                        username.strip(), email.strip(), db
                    )

                if ok:
                    # Pre-fill the username on the login page for the next step.
                    st.session_state["prefill_username"] = username.strip()
                    # temp_password is only returned when email could not be sent.
                    if temp_password:
                        # Single concise instruction (no repeated "use it to sign in…" lines).
                        st.markdown(
                            '<div class="warn-box">'
                            "<strong>Temporary password (shown once — copy it now):</strong> sign in "
                            "with it to set your permanent password and activate your account."
                            "</div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="temp-pass-box">{temp_password}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        # Emailed — send the new user straight to login, username pre-filled.
                        st.session_state["flash_login"] = (
                            "Registration received — a temporary password has been emailed to you. "
                            "Sign in with it to set your permanent password and activate your account."
                        )
                        st.session_state["page"] = "login"
                        st.rerun()
                else:
                    st.error(message)

        st.divider()
        if st.button("Back to Sign In", width='stretch', key="reg_back"):
            st.session_state["page"] = "login"
            st.rerun()
