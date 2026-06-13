import streamlit as st
import pandas as pd
from config.settings import APP_NAME, ROLE_ADMIN
from ui.components import show_severity_cards, plot_severity_pie, plot_threat_types, plot_timeline, plot_top_sources
from services.threat_engine import compute_summary


def render_dashboard(user, db):
    role_label = "Administrator" if user.role == ROLE_ADMIN else "IT Owner"

    st.markdown(
        f'<div class="page-header">'
        f'<div class="page-title">Security Dashboard</div>'
        f'<div class="page-subtitle">Welcome back, {user.username} &nbsp;|&nbsp; {role_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    findings = st.session_state.get("analysis_results", [])
    analyzed_files = st.session_state.get("analyzed_files", [])
    append_mode = st.session_state.get("append_mode", False)

    # ── No data state ──────────────────────────────────────────────────────────
    if not findings:
        st.markdown(
            '<div class="info-box">'
            "<strong>No analysis results yet.</strong> Upload a log file to begin threat detection."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Upload Log File", type="primary", width='stretch'):
            st.session_state["page"] = "upload"
            st.rerun()

        if user.role == ROLE_ADMIN:
            st.divider()
            _show_admin_stats(db)
        return

    # ── Summary ────────────────────────────────────────────────────────────────
    summary = compute_summary(findings)

    if analyzed_files:
        files_str = ", ".join(f"`{f}`" for f in analyzed_files)
        st.markdown(f"**Analyzed {len(analyzed_files)} file(s):** {files_str}")
        if append_mode:
            st.caption("Append mode was active — results include multiple files.")

    show_severity_cards(summary)

    # ── Quick actions (right under the summary, above the charts) ───────────────
    col_act1, col_act2, _ = st.columns(3)
    with col_act1:
        if st.button("View Detailed Results", width='stretch', type="primary"):
            st.session_state["page"] = "results"
            st.rerun()
    with col_act2:
        if st.button("Upload Another File", width='stretch'):
            st.session_state["page"] = "upload"
            st.rerun()

    st.divider()

    # ── Charts ─────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="medium")
    with col_left:
        fig = plot_severity_pie(findings)
        if fig:
            st.plotly_chart(fig)
    with col_right:
        fig = plot_threat_types(findings)
        if fig:
            st.plotly_chart(fig)

    fig = plot_timeline(findings)
    if fig:
        st.plotly_chart(fig)
    else:
        st.caption("Threat timeline not available — log entries lacked parseable timestamps.")

    fig = plot_top_sources(findings)
    if fig:
        st.plotly_chart(fig)

    if user.role == ROLE_ADMIN:
        st.divider()
        _show_admin_stats(db)


def _show_admin_stats(db, compact=False):
    from database.models import User, DetectionRule, AuditLog
    st.markdown(
        '<div class="section-title" style="font-size:1rem;font-weight:700;color:#111827;margin-bottom:12px;">'
        "System Overview</div>",
        unsafe_allow_html=True,
    )
    try:
        active_users  = db.query(User).filter_by(is_active=True).count()
        active_rules  = db.query(DetectionRule).filter_by(is_enabled=True).count()
        audit_entries = db.query(AuditLog).count()
        if compact:
            # Narrow side column — stack vertically so labels don't truncate
            st.metric("Active Users", active_users)
            st.metric("Active Detection Rules", active_rules)
            st.metric("Audit Log Entries", audit_entries)
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Active Users", active_users)
            with c2:
                st.metric("Active Detection Rules", active_rules)
            with c3:
                st.metric("Audit Log Entries", audit_entries)
    except Exception as exc:
        st.caption(f"Could not load system stats: {exc}")
