import os
import streamlit as st
from auth.access_control import require_admin
from services.email_service import is_smtp_configured, test_smtp_connection
from config.settings import ENV_SMTP_HOST, ENV_SMTP_PORT, ENV_SMTP_USER, ENV_SMTP_FROM_NAME


def render_settings_page(user, db):
    require_admin()

    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">⚙️ System Settings</div>'
        '<div class="page-subtitle">Administrator configuration and diagnostics</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── SMTP Status ────────────────────────────────────────────────────────────
    st.subheader("Email / SMTP Configuration")

    smtp_ok = is_smtp_configured()
    host = os.getenv(ENV_SMTP_HOST, "")
    port = os.getenv(ENV_SMTP_PORT, "587")
    user = os.getenv(ENV_SMTP_USER, "")
    from_name = os.getenv(ENV_SMTP_FROM_NAME, "")

    col1, col2 = st.columns([2, 1])
    with col1:
        if smtp_ok:
            st.markdown(
                '<div class="success-box">'
                "<strong>SMTP is configured.</strong> "
                f"Host: <code>{host}:{port}</code> — User: <code>{user}</code>"
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
            use_container_width=True,
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
        MAX_UPLOAD_SIZE_MB,
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
| Max upload size | {MAX_UPLOAD_SIZE_MB} MB |
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
        active_sessions = db.query(DbSession).filter_by(is_active=True).count()

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
