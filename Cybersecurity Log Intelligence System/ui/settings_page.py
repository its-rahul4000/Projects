import os
import streamlit as st
from services.email_service import is_smtp_configured, test_smtp_connection
from config.settings import (
    ENV_SMTP_HOST, ENV_SMTP_PORT, ENV_SMTP_USER, ENV_SMTP_FROM_NAME,
    ROLE_ADMIN, now_ist,
)


def render_settings_page(user, db):
    is_admin = user.role == ROLE_ADMIN

    st.markdown(
        '<div class="page-header">'
        f'<div class="page-title">{"System Settings" if is_admin else "Settings"}</div>'
        f'<div class="page-subtitle">'
        f'{"Administrator configuration and diagnostics" if is_admin else "Manage your account"}'
        "</div></div>",
        unsafe_allow_html=True,
    )

    # ── Administrator-only diagnostics ──────────────────────────────────────────
    if is_admin:
        _render_admin_sections(db)

    # ── Change Password (all users) ─────────────────────────────────────────────
    _render_change_password_section(user, db)


def _render_admin_sections(db):
    # ── SMTP Status ────────────────────────────────────────────────────────────
    st.subheader("Email / SMTP Configuration")

    smtp_ok = is_smtp_configured()
    host = os.getenv(ENV_SMTP_HOST, "")
    port = os.getenv(ENV_SMTP_PORT, "587")
    smtp_user = os.getenv(ENV_SMTP_USER, "")

    col1, col2 = st.columns([2, 1])
    with col1:
        if smtp_ok:
            st.markdown(
                '<div class="success-box">'
                "<strong>SMTP is configured.</strong> "
                f"Host: <code>{host}:{port}</code> — User: <code>{smtp_user}</code>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="warn-box">'
                "<strong>SMTP is not configured.</strong> "
                "Set <code>SMTP_HOST</code>, <code>SMTP_USER</code>, and <code>SMTP_PASS</code> "
                "in your <code>.env</code> file, then restart the application."
                "</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            """
**Required `.env` variables:**

| Variable | Example | Purpose |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | Mail server hostname |
| `SMTP_PORT` | `587` | SMTP port (587 = STARTTLS) |
| `SMTP_USER` | `alerts@company.com` | Login username |
| `SMTP_PASS` | `••••••••` | App password / secret |
| `SMTP_FROM_NAME` | `CyberSec System` | Friendly display name |

> **Gmail:** Enable 2-FA and create an **App Password** at
> [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
"""
        )

    with col2:
        st.markdown("**Test connection**")
        st.caption("Attempts to connect and login to the SMTP server without sending any email.")
        if st.button(
            "Test SMTP Connection",
            width='stretch',
            type="primary",
            key="test_smtp_btn",
            disabled=not smtp_ok,
        ):
            with st.spinner("Connecting..."):
                success, message = test_smtp_connection()
            if success:
                st.success(message)
            else:
                st.error(message)

        if not smtp_ok:
            st.caption("Configure SMTP in .env to enable this test.")

    st.divider()

    # ── Application Info ───────────────────────────────────────────────────────
    st.subheader("Application Information")

    from config.settings import (
        SESSION_TIMEOUT_SECONDS,
        PASSWORD_MIN_LENGTH,
        PASSWORD_EXPIRY_DAYS,
        AUDIT_LOG_RETENTION_DAYS,
        PASSWORD_HISTORY_DEPTH,
        ALLOWED_EXTENSIONS,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            f"""
<div class="section-card">
<div class="section-title">Security Settings</div>

| Setting | Value |
|---|---|
| Password minimum length | {PASSWORD_MIN_LENGTH} characters |
| IT Owner password expiry | {PASSWORD_EXPIRY_DAYS} days |
| Password history depth | Last {PASSWORD_HISTORY_DEPTH} passwords |
| Session timeout | {SESSION_TIMEOUT_SECONDS // 60} minutes |
| Audit log retention | {AUDIT_LOG_RETENTION_DAYS} days |
</div>
""",
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            f"""
<div class="section-card">
<div class="section-title">File Upload Settings</div>

| Setting | Value |
|---|---|
| Allowed extensions | {", ".join(sorted(ALLOWED_EXTENSIONS))} |
| Temp file storage | OS temp directory |
| Temp file cleanup | On logout / session expiry |
</div>
""",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Database Stats ─────────────────────────────────────────────────────────
    st.subheader("Database Overview")

    from database.models import User, DetectionRule, AuditLog, Session as DbSession

    try:
        total_users   = db.query(User).count()
        active_users  = db.query(User).filter_by(is_active=True).count()
        total_rules   = db.query(DetectionRule).count()
        active_rules  = db.query(DetectionRule).filter_by(is_enabled=True).count()
        audit_entries = db.query(AuditLog).count()
        # Use expiry_time comparison — Session model has no is_active column
        active_sessions = db.query(DbSession).filter(DbSession.expiry_time > now_ist()).count()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Users", total_users, delta=f"{active_users} active")
        with c2:
            st.metric("Detection Rules", total_rules, delta=f"{active_rules} enabled")
        with c3:
            st.metric("Audit Log Entries", audit_entries)
        with c4:
            st.metric("Active Sessions", active_sessions)
    except Exception as exc:
        st.error(f"Could not query database stats: {exc}")

    st.divider()


def _render_change_password_section(user, db):
    # ── Change Password ────────────────────────────────────────────────────────
    st.subheader("Change Your Password")
    st.markdown(
        '<div class="info-box">'
        "You will be automatically signed out after changing your password."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("settings_change_pw_form", clear_on_submit=True):
        current_pw = st.text_input(
            "Current Password", type="password", placeholder="Enter your current password"
        )
        new_pw = st.text_input(
            "New Password", type="password", placeholder="At least 20 characters"
        )
        confirm_pw = st.text_input(
            "Confirm New Password", type="password", placeholder="Repeat new password"
        )
        submitted = st.form_submit_button(
            "Update Password", width='stretch', type="primary"
        )

    if submitted:
        from auth.password import verify_password
        if not current_pw or not new_pw or not confirm_pw:
            st.error("All fields are required.")
        elif not verify_password(current_pw, user.password_hash):
            st.error("Current password is incorrect.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        else:
            from services.user_service import change_password
            from services.audit_service import ACTION_PASSWORD_CHANGE
            ok, msg = change_password(user.id, new_pw, db, action_label=ACTION_PASSWORD_CHANGE)
            if ok:
                st.success(msg + " Please log in again.")
                import time; time.sleep(1)
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
            else:
                st.error(msg)

    with st.expander("Password requirements"):
        st.markdown("""
- Minimum **20 characters**
- At least one **uppercase** letter (A-Z)
- At least one **lowercase** letter (a-z)
- At least one **digit** (0-9)
- At least one **special character** (!@#$%^&* etc.)
- Cannot reuse any of your last 5 passwords
        """)
