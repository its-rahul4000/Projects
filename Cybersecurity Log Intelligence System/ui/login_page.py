import streamlit as st
from config.settings import APP_NAME
from services.user_service import authenticate, is_password_expired
from auth.session_manager import create_session
from services.audit_service import log_action, ACTION_LOGIN, ACTION_LOGIN_FAILED


def render_login_page(db):
    # Centered login card via column centering
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            f"""
            <div class="login-card">
              <div class="login-logo">🛡️</div>
              <div class="login-title">{APP_NAME}</div>
              <div class="login-sub">Secure log threat detection platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                max_chars=100,
                placeholder="Enter your username",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )
            submitted = st.form_submit_button(
                "Sign In",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not username.strip() or not password:
                st.error("Please enter both username and password.")
                return

            success, user, msg = authenticate(username, password, db)
            if not success:
                log_action(
                    user_id=1,
                    action=ACTION_LOGIN_FAILED,
                    db=db,
                    details=f"Failed login for: {username[:50]}",
                )
                st.error(f"**Login failed:** {msg}")
                return

            log_action(user.id, ACTION_LOGIN, db, details=f"Login: {user.username}")
            user.last_login = __import__("datetime").datetime.utcnow()
            db.commit()

            if user.is_first_login or user.password_type == "temporary":
                token = create_session(user.id, db)
                st.session_state.update({
                    "session_token": token,
                    "current_user": user,
                    "current_user_id": user.id,
                    "page": "change_password",
                    "force_change_reason": "first_login",
                })
                st.rerun()
            elif is_password_expired(user):
                token = create_session(user.id, db)
                st.session_state.update({
                    "session_token": token,
                    "current_user": user,
                    "current_user_id": user.id,
                    "page": "change_password",
                    "force_change_reason": "expired",
                })
                st.rerun()
            else:
                token = create_session(user.id, db)
                st.session_state.update({
                    "session_token": token,
                    "current_user": user,
                    "current_user_id": user.id,
                    "page": "dashboard",
                })
                st.rerun()

        st.divider()
        st.markdown(
            "<p style='text-align:center;color:#718096;font-size:0.88rem;'>"
            "New IT Owner? Register below.</p>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Register as IT Owner",
            use_container_width=True,
            key="goto_register",
        ):
            st.session_state["page"] = "register"
            st.rerun()


def render_change_password_page(user, db):
    reason = st.session_state.get("force_change_reason", "")

    if reason == "first_login":
        st.warning(
            "You are using a **temporary password**. "
            "Please set a permanent password to continue."
        )
    elif reason == "expired":
        st.warning(
            "Your password has **expired** (180-day limit). "
            "Please set a new password to continue."
        )
    else:
        st.subheader("Change Password")

    with st.form("change_pw_form", clear_on_submit=True):
        new_pw = st.text_input(
            "New Password",
            type="password",
            placeholder="At least 20 characters",
        )
        confirm_pw = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Repeat new password",
        )
        submitted = st.form_submit_button(
            "Set New Password",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not new_pw or not confirm_pw:
            st.error("Both fields are required.")
            return
        if new_pw != confirm_pw:
            st.error("Passwords do not match.")
            return

        from services.user_service import change_password
        from services.audit_service import ACTION_PASSWORD_CHANGE, ACTION_PASSWORD_EXPIRED_CHANGE
        label = ACTION_PASSWORD_EXPIRED_CHANGE if reason == "expired" else ACTION_PASSWORD_CHANGE
        ok, msg = change_password(user.id, new_pw, db, action_label=label)
        if not ok:
            st.error(msg)
        else:
            st.success(msg)
            st.session_state.pop("force_change_reason", None)
            token = create_session(user.id, db)
            db.refresh(user)
            st.session_state.update({
                "session_token": token,
                "current_user": user,
                "page": "dashboard",
            })
            st.rerun()

    with st.expander("Password requirements"):
        st.markdown("""
        - Minimum **20 characters**
        - At least one **uppercase** letter (A-Z)
        - At least one **lowercase** letter (a-z)
        - At least one **digit** (0-9)
        - At least one **special character** (!@#$%^&* etc.)
        - Cannot reuse any of your last 5 passwords
        """)
