import streamlit as st
from config.settings import APP_NAME, ROLE_ADMIN, now_ist
from services.user_service import authenticate, is_password_expired
from auth.session_manager import create_session
from services.audit_service import log_action, ACTION_LOGIN, ACTION_LOGIN_FAILED, ACTION_ADMIN_SETUP


def render_login_page(db):
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown(
            f"""<div class="login-card">
              <div class="login-logo">🛡️</div>
              <div class="login-title">Cybersecurity Log Intelligence</div>
              <div class="login-sub">Secure log threat detection platform</div>
            </div>""",
            unsafe_allow_html=True,
        )

        # Flash message + pre-filled username when arriving from registration / reset
        flash = st.session_state.pop("flash_login", None)
        if flash:
            st.success(flash)
        temp_pw = st.session_state.pop("flash_temp_pw", None)
        if temp_pw:
            st.markdown(f'<div class="temp-pass-box">{temp_pw}</div>', unsafe_allow_html=True)
            st.caption("Temporary password — copy it into the Password field below, then sign in.")
        prefill_user = st.session_state.get("prefill_username", "")

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input(
                "Username", max_chars=100, placeholder="Enter your username",
                value=prefill_user,
            )
            password = st.text_input(
                "Password", type="password", placeholder="Enter your password"
            )
            submitted = st.form_submit_button(
                "Sign In", width='stretch', type="primary"
            )

        # Forgot-password link, right-aligned just under the form
        _, fcol = st.columns([2, 1])
        with fcol:
            if st.button("Forgot Password?", width='stretch', key="goto_forgot", type="tertiary"):
                st.session_state["page"] = "forgot_password"
                st.rerun()

        # Submit handling uses if/elif (never an early ``return``) so a failed or
        # incomplete login falls through to the "Register as IT Owner" footer below
        # instead of hiding it. Successful logins end in ``st.rerun()`` and navigate
        # away, so the footer is skipped only on success.
        if submitted and (not username.strip() or not password):
            st.error("Please enter both username and password.")

        elif submitted:
            success, user, msg = authenticate(username, password, db)
            if not success:
                # No real account yet? It may be a pending registration whose
                # temporary password is correct — route the registrant to set a
                # permanent password, which is what actually creates the account.
                from services.user_service import find_pending_registration
                pending = find_pending_registration(username, password, db)
                if pending:
                    st.session_state["pending_username"] = pending.username
                    st.session_state["page"] = "complete_registration"
                    st.rerun()
                log_action(
                    user_id=1,
                    action=ACTION_LOGIN_FAILED,
                    db=db,
                    details=f"Failed login for: {username[:50]}",
                )
                st.error(f"**Login failed:** {msg}")

            else:
                log_action(user.id, ACTION_LOGIN, db, details=f"Login: {user.username}")
                user.last_login = now_ist()
                db.commit()

                token = create_session(user.id, db)
                base = {"session_token": token, "current_user": user, "current_user_id": user.id}

                # Admin on fresh DB → configure recovery email first
                if (
                    user.role == ROLE_ADMIN
                    and getattr(user, "is_first_login", False)
                    and getattr(user, "password_type", "") == "permanent"
                ):
                    st.session_state.update({**base, "page": "admin_setup"})
                    st.rerun()

                # Any user with a temporary password or forced first-login change
                elif getattr(user, "is_first_login", False) or getattr(user, "password_type", "") == "temporary":
                    st.session_state.update({
                        **base,
                        "page": "change_password",
                        "force_change_reason": "first_login",
                    })
                    st.rerun()

                elif is_password_expired(user):
                    st.session_state.update({
                        **base,
                        "page": "change_password",
                        "force_change_reason": "expired",
                    })
                    st.rerun()

                else:
                    st.session_state.update({**base, "page": "dashboard"})
                    st.rerun()

        st.markdown(
            '<p class="login-divider-text">New IT Owner? Register below.</p>',
            unsafe_allow_html=True,
        )
        if st.button("Register as IT Owner", width='stretch', key="goto_register"):
            st.session_state["page"] = "register"
            st.rerun()


def render_forgot_password_page(db):
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            f"""<div class="login-card">
              <div class="login-logo">🔑</div>
              <div class="login-title">Reset Password</div>
              <div class="login-sub">Enter your username or registered email address</div>
            </div>""",
            unsafe_allow_html=True,
        )

        with st.form("forgot_pw_form", clear_on_submit=False):
            identifier = st.text_input(
                "Username or Email",
                max_chars=150,
                placeholder="Enter username or email",
            )
            submitted = st.form_submit_button(
                "Send Reset Email", width='stretch', type="primary"
            )

        if submitted:
            if not identifier.strip():
                st.error("Please enter your username or email address.")
            else:
                from services.user_service import forgot_password
                ok, msg, temp_pw, uname = forgot_password(identifier.strip(), db)
                if ok:
                    # Land back on the login page with everything ready: username
                    # pre-filled and (when email isn't configured) the temp password shown.
                    if uname:
                        st.session_state["prefill_username"] = uname
                    st.session_state["flash_login"] = msg
                    if temp_pw:
                        st.session_state["flash_temp_pw"] = temp_pw
                    st.session_state["page"] = "login"
                    st.rerun()
                else:
                    st.error(msg)

        st.divider()
        if st.button("← Back to Login", width='stretch', key="back_to_login"):
            st.session_state["page"] = "login"
            st.rerun()


def render_complete_registration_page(db):
    """Final step of IT Owner registration: the registrant sets a permanent password,
    which actually creates the account, then is signed in."""
    username = st.session_state.get("pending_username")
    if not username:
        st.session_state["page"] = "login"
        st.rerun()
        return

    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown(
            f"""<div class="login-card">
              <div class="login-logo">🛡️</div>
              <div class="login-title">Cybersecurity Log Intelligence</div>
              <div class="login-sub">Activate your account</div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="info-box">'
            f"Welcome, <strong>{username}</strong>. Set a permanent password to finish "
            "creating your account."
            "</div>",
            unsafe_allow_html=True,
        )

        with st.form("complete_reg_form", clear_on_submit=True):
            new_pw = st.text_input("New Password", type="password",
                                   placeholder="At least 20 characters")
            confirm_pw = st.text_input("Confirm Password", type="password",
                                       placeholder="Repeat new password")
            submitted = st.form_submit_button("Create Account & Sign In",
                                              width='stretch', type="primary")

        if submitted:
            if not new_pw or not confirm_pw:
                st.error("Both fields are required.")
            elif new_pw != confirm_pw:
                st.error("Passwords do not match.")
            else:
                from services.user_service import complete_pending_registration
                ok, msg, user = complete_pending_registration(username, new_pw, db)
                if not ok:
                    st.error(msg)
                else:
                    token = create_session(user.id, db)
                    user.last_login = now_ist()
                    db.commit()
                    log_action(user.id, ACTION_LOGIN, db, details=f"Login: {user.username}")
                    st.session_state.pop("pending_username", None)
                    st.session_state.update({
                        "session_token": token,
                        "current_user": user,
                        "current_user_id": user.id,
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
            """)

        st.divider()
        if st.button("← Back to Sign In", width='stretch', key="complete_reg_back"):
            st.session_state.pop("pending_username", None)
            st.session_state["page"] = "login"
            st.rerun()


def render_admin_setup_page(user, db):
    st.markdown(
        "<div class='section-card'>"
        "<div class='section-title'>Administrator Initial Setup</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='info-box'>"
        "Welcome, Administrator! Before you start, please configure a <strong>recovery email address</strong>. "
        "This email will be used for critical system notifications. You cannot skip this step."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("admin_setup_form", clear_on_submit=False):
        email = st.text_input(
            "Recovery Email Address",
            max_chars=200,
            placeholder="admin@yourdomain.com",
        )
        confirm_email = st.text_input(
            "Confirm Email Address",
            max_chars=200,
            placeholder="Repeat email address",
        )
        submitted = st.form_submit_button(
            "Save & Continue to Dashboard", width='stretch', type="primary"
        )

    if submitted:
        from utils.validators import validate_email_address
        email = email.strip().lower()
        confirm_email = confirm_email.strip().lower()

        if not email:
            st.error("Email address is required.")
        elif not validate_email_address(email):
            st.error("Please enter a valid email address.")
        elif email != confirm_email:
            st.error("Email addresses do not match.")
        else:
            user.email = email
            user.is_first_login = False
            db.commit()
            log_action(
                user.id, ACTION_ADMIN_SETUP, db,
                details=f"Admin configured recovery email: {email}",
            )
            st.success("Recovery email saved. Redirecting to Dashboard…")
            st.session_state["current_user"] = user
            st.session_state["page"] = "dashboard"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_change_password_page(user, db):
    reason = st.session_state.get("force_change_reason", "")

    if reason == "first_login":
        st.markdown(
            "<div class='warn-box'>You are using a <strong>temporary password</strong>. "
            "Please set a permanent password to continue.</div>",
            unsafe_allow_html=True,
        )
    elif reason == "expired":
        st.markdown(
            "<div class='warn-box'>Your password has <strong>expired</strong> (180-day limit). "
            "Please set a new password to continue.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="page-header">'
            '<div class="page-title">Change Password</div>'
            '<div class="page-subtitle">Set a new password for your account</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    with st.form("change_pw_form", clear_on_submit=True):
        new_pw = st.text_input(
            "New Password", type="password", placeholder="At least 20 characters"
        )
        confirm_pw = st.text_input(
            "Confirm Password", type="password", placeholder="Repeat new password"
        )
        submitted = st.form_submit_button(
            "Set New Password", width='stretch', type="primary"
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
