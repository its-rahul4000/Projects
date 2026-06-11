import streamlit as st
from pathlib import Path

from services.log_parser import parse_log_file, merge_dataframes
from services.threat_engine import get_enabled_rules, run_analysis
from services.audit_service import log_action, ACTION_ANALYZE
from utils.validators import validate_file_extension, validate_file_size
from utils.temp_file_manager import save_upload_to_temp, register_temp_file
from config.settings import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB


def render_upload_page(user, db):
    st.markdown(
        '<div class="page-header">'
        '<div class="page-title">Upload Log File</div>'
        '<div class="page-subtitle">Analyze log files for security threats using static and dynamic detection rules</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Options ────────────────────────────────────────────────────────────────
    col_opt, col_info = st.columns([2, 1])
    with col_opt:
        append_mode = st.checkbox(
            "Append to existing analysis",
            value=st.session_state.get("append_mode", False),
            help="Merge results with a previous upload instead of replacing them.",
        )
        st.session_state["append_mode"] = append_mode

        if append_mode and st.session_state.get("analysis_results"):
            existing = st.session_state.get("analyzed_files", [])
            st.markdown(
                f'<div class="info-box">Append mode ON — results will be merged '
                f'with {len(existing)} existing file(s): '
                f'{", ".join(existing)}</div>',
                unsafe_allow_html=True,
            )

    with col_info:
        st.markdown(
            f"""
<div class="section-card" style="padding:14px 16px;">
<div class="section-title" style="margin-bottom:8px;">Supported Formats</div>

{" &nbsp;".join(f"<code>{e}</code>" for e in sorted(ALLOWED_EXTENSIONS))}

Max size: **{MAX_UPLOAD_SIZE_MB} MB**
</div>
""",
            unsafe_allow_html=True,
        )

    # ── File uploader ──────────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Choose a log file",
        type=[ext.lstrip(".") for ext in ALLOWED_EXTENSIONS],
        help="Drag and drop or click to browse.",
        label_visibility="collapsed",
    )

    if not uploaded_file:
        st.markdown(
            '<div class="info-box" style="text-align:center;">'
            "Drag and drop a log file here, or click the button above to browse."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    file_bytes = uploaded_file.getvalue()
    filename   = uploaded_file.name

    # Validate
    if not validate_file_extension(filename):
        st.error(f"File type not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}")
        return
    if not validate_file_size(file_bytes):
        st.error(f"File too large. Maximum allowed size: {MAX_UPLOAD_SIZE_MB} MB.")
        return

    # Info bar
    st.markdown(
        f'<div class="success-box">'
        f"<strong>{filename}</strong> — "
        f"{len(file_bytes)/1024:.1f} KB uploaded successfully."
        f"</div>",
        unsafe_allow_html=True,
    )

    # Preview
    with st.expander("Preview (first 20 lines)", expanded=True):
        preview_lines = file_bytes.decode("utf-8", errors="replace").splitlines()[:20]
        st.code("\n".join(preview_lines), language="text")

    st.divider()
    if st.button("Analyze Log File", type="primary", use_container_width=True):
        _run_analysis(user, db, file_bytes, filename, append_mode)


def _run_analysis(user, db, file_bytes: bytes, filename: str, append_mode: bool):
    progress = st.progress(0, text="Saving file...")

    suffix   = Path(filename).suffix or ".log"
    temp_path = save_upload_to_temp(file_bytes, suffix)
    token    = st.session_state.get("session_token", "anon")
    register_temp_file(token, temp_path)
    progress.progress(20, text="Parsing log entries...")

    new_df = parse_log_file(temp_path)
    if new_df.empty:
        progress.empty()
        st.warning("Could not parse any log entries from this file. Please check the file format.")
        return

    progress.progress(50, text=f"Parsed {len(new_df)} entries. Running detection rules...")

    if append_mode and st.session_state.get("log_df") is not None:
        merged_df = merge_dataframes(st.session_state["log_df"], new_df)
    else:
        merged_df = new_df

    rules = get_enabled_rules(db)
    if not rules:
        progress.empty()
        st.warning("No detection rules are currently enabled. Ask the Administrator to configure rules.")
        return

    findings = run_analysis(merged_df, rules)
    progress.progress(90, text="Updating session...")

    existing_files = [] if not append_mode else st.session_state.get("analyzed_files", [])
    if filename not in existing_files:
        existing_files.append(filename)

    st.session_state["log_df"]           = merged_df
    st.session_state["analysis_results"] = findings
    st.session_state["analyzed_files"]   = existing_files

    log_action(
        user.id, ACTION_ANALYZE, db,
        file_name=filename,
        append_used=append_mode,
        details=f"Analyzed {len(merged_df)} entries with {len(rules)} rules. Threats: {len(findings)}.",
    )

    progress.progress(100, text="Done!")
    import time; time.sleep(0.4)
    progress.empty()

    threat_word = "threat" if len(findings) == 1 else "threats"
    severity_icon = "🔴" if any(f["severity"] == "CRITICAL" for f in findings) else \
                    "🟠" if any(f["severity"] == "HIGH" for f in findings) else \
                    "✅" if not findings else "🟡"

    st.markdown(
        f'<div class="success-box">'
        f"{severity_icon} Analysis complete — "
        f"<strong>{len(findings)} {threat_word}</strong> detected in "
        f"<strong>{len(merged_df)}</strong> log entries."
        f"</div>",
        unsafe_allow_html=True,
    )
    st.session_state["page"] = "results"
    st.rerun()
