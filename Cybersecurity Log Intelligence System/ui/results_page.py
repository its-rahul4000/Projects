import streamlit as st
from ui.components import (
    show_severity_cards, show_findings_table,
    plot_severity_pie, plot_threat_types, plot_timeline, plot_top_sources,
)
from services.threat_engine import compute_summary
from services.report_service import generate_pdf_report, get_report_filename
from services.email_service import send_pdf_report_email, is_smtp_configured
from services.audit_service import log_action, ACTION_DOWNLOAD_REPORT, ACTION_EMAIL_REPORT


def render_results_page(user, db):
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Analysis Results</div>'
        '<div class="page-subtitle">Threat findings, visualizations, and reports</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    findings      = st.session_state.get("analysis_results")
    analyzed_files = st.session_state.get("analyzed_files", [])
    append_mode   = st.session_state.get("append_mode", False)

    if findings is None:
        st.markdown(
            '<div class="info-box">'
            "No analysis results yet. Please upload and analyze a log file first."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("Go to Upload", type="primary"):
            st.session_state["page"] = "upload"
            st.rerun()
        return

    summary = compute_summary(findings)

    # ── Files + summary cards ──────────────────────────────────────────────────
    if analyzed_files:
        files_str = " &nbsp;|&nbsp; ".join(f"<code>{f}</code>" for f in analyzed_files)
        mode_tag  = " &nbsp;<span style='color:#d97706;font-weight:600;'>⊕ Append</span>" if append_mode else ""
        st.markdown(
            f'<p style="color:#718096;font-size:0.88rem;margin-bottom:12px;">'
            f"Files analyzed: {files_str}{mode_tag}</p>",
            unsafe_allow_html=True,
        )

    show_severity_cards(summary)

    # ── Action row ────────────────────────────────────────────────────────────
    st.markdown('<div style="margin: 16px 0;">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Generate PDF Report", width='stretch', type="primary", key="gen_pdf_btn"):
            st.session_state["_do_pdf"] = True

    smtp_ready = is_smtp_configured()
    with col2:
        if st.button(
            "Email Report to Me",
            width='stretch',
            key="email_pdf_btn",
            disabled=not smtp_ready,
            help="" if smtp_ready else "SMTP not configured. Go to Settings to configure email.",
        ):
            st.session_state["_do_email"] = True
        if not smtp_ready:
            st.caption("Email unavailable — SMTP not configured.")

    with col3:
        if st.button("Clear & New Analysis", width='stretch', key="clear_btn"):
            for k in ["analysis_results", "log_df", "analyzed_files", "append_mode",
                      "_do_pdf", "_do_email"]:
                st.session_state.pop(k, None)
            st.session_state["analyzed_files"] = []
            st.session_state["page"] = "upload"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── PDF generation ─────────────────────────────────────────────────────────
    if st.session_state.pop("_do_pdf", False):
        with st.spinner("Generating PDF report..."):
            try:
                pdf_bytes = generate_pdf_report(
                    findings=findings,
                    username=user.username,
                    email=user.email,
                    analyzed_files=analyzed_files,
                    append_mode=append_mode,
                )
                filename = get_report_filename(analyzed_files)
                log_action(user.id, ACTION_DOWNLOAD_REPORT, db, details=f"PDF downloaded: {filename}")
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    width='stretch',
                    type="primary",
                )
            except Exception as exc:
                st.error(f"PDF generation failed: {exc}")

    # ── Email sending ──────────────────────────────────────────────────────────
    if st.session_state.pop("_do_email", False):
        with st.spinner("Generating and sending report..."):
            try:
                pdf_bytes = generate_pdf_report(
                    findings=findings,
                    username=user.username,
                    email=user.email,
                    analyzed_files=analyzed_files,
                    append_mode=append_mode,
                )
                filename = get_report_filename(analyzed_files)
                sent = send_pdf_report_email(
                    to_email=user.email,
                    username=user.username,
                    pdf_bytes=pdf_bytes,
                    report_filename=filename,
                    summary=summary,
                    analyzed_files=analyzed_files,
                    append_mode=append_mode,
                )
                if sent:
                    st.success(f"Report emailed to **{user.email}**.")
                    log_action(user.id, ACTION_EMAIL_REPORT, db, details=f"Report emailed to {user.email}")
                else:
                    st.warning(
                        "Email delivery failed. Use the **Generate PDF Report** button "
                        "to download it directly instead."
                    )
            except Exception as exc:
                st.error(f"Failed to send report: {exc}")

    st.divider()

    # ── Recommended Actions (inline, above tabs) ───────────────────────────────
    if findings:
        from ui.components import show_recommendations_panel
        show_recommendations_panel(findings)

    st.divider()

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["Findings Table", "Visualizations", "Raw Log Data"])

    with tab1:
        if findings:
            c_filter, c_count = st.columns([3, 1])
            with c_filter:
                sev_filter = st.multiselect(
                    "Filter by Severity",
                    options=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
                    default=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
                    label_visibility="collapsed",
                )
            filtered = [f for f in findings if f.get("severity") in sev_filter]
            with c_count:
                st.metric("Showing", f"{len(filtered)} / {len(findings)}")
            show_findings_table(filtered)
        else:
            st.markdown(
                '<div class="success-box">No threats detected in the analyzed log file(s).</div>',
                unsafe_allow_html=True,
            )

    with tab2:
        if findings:
            c1, c2 = st.columns(2, gap="medium")
            with c1:
                fig = plot_severity_pie(findings)
                if fig:
                    st.plotly_chart(fig)
                else:
                    st.caption("No severity data available.")
            with c2:
                fig = plot_threat_types(findings)
                if fig:
                    st.plotly_chart(fig)
                else:
                    st.caption("No rule data available.")

            fig = plot_timeline(findings)
            if fig:
                st.plotly_chart(fig)
            else:
                st.caption("Timeline unavailable — no parseable timestamps in findings.")

            fig = plot_top_sources(findings)
            if fig:
                st.plotly_chart(fig)
            else:
                st.caption("No IP address data available.")
        else:
            st.markdown(
                '<div class="info-box">No threat data available for visualizations.</div>',
                unsafe_allow_html=True,
            )

    with tab3:
        log_df = st.session_state.get("log_df")
        if log_df is not None and not log_df.empty:
            st.markdown(
                f'<div class="info-box"><strong>{len(log_df)}</strong> raw log entries parsed.</div>',
                unsafe_allow_html=True,
            )
            display_cols = [c for c in ["line_num", "timestamp", "level", "source_ip", "message"]
                            if c in log_df.columns]
            st.dataframe(log_df[display_cols].head(500), width='stretch', hide_index=True)
        else:
            st.info("No raw log data available.")
