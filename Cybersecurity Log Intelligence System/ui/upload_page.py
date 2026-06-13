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
            help="Merge results with a previous upload instead of replacing them. Allows multiple files.",
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
            f"""<div class="section-card" style="padding:14px 16px;">
<div class="section-title" style="margin-bottom:8px;">Supported Formats</div>
{" &nbsp;".join(f"<code>{e}</code>" for e in sorted(ALLOWED_EXTENSIONS))}

Max size: **{MAX_UPLOAD_SIZE_MB} MB per file**
</div>""",
            unsafe_allow_html=True,
        )

    # ── File uploader ──────────────────────────────────────────────────────────
    # Append mode: allow multiple files; non-append: single file only
    allowed_types = [ext.lstrip(".") for ext in ALLOWED_EXTENSIONS]

    if append_mode:
        uploaded_files = st.file_uploader(
            "Choose one or more log files",
            type=allowed_types,
            accept_multiple_files=True,
            help="Drag and drop or click to browse. Multiple files allowed in append mode.",
            label_visibility="collapsed",
        )
        # Normalise to list
        if uploaded_files is None:
            uploaded_files = []
    else:
        single_file = st.file_uploader(
            "Choose a log file",
            type=allowed_types,
            accept_multiple_files=False,
            help="Drag and drop or click to browse. Only one file allowed in non-append mode.",
            label_visibility="collapsed",
        )
        uploaded_files = [single_file] if single_file is not None else []

    if not uploaded_files:
        st.markdown(
            '<div class="info-box" style="text-align:center;">'
            + ("Drag and drop one or more log files here." if append_mode else "Drag and drop a log file here, or click the button above to browse.")
            + "</div>",
            unsafe_allow_html=True,
        )
        return

    # ── Validate each file ─────────────────────────────────────────────────────
    valid_files = []
    for uf in uploaded_files:
        fb = uf.getvalue()
        if not validate_file_extension(uf.name):
            st.error(f"**{uf.name}**: File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
            continue
        if not validate_file_size(fb):
            st.error(f"**{uf.name}**: File too large (max {MAX_UPLOAD_SIZE_MB} MB).")
            continue
        valid_files.append((uf.name, fb))

    if not valid_files:
        return

    # Info summary
    file_list = ", ".join(f[0] for f in valid_files)
    total_kb = sum(len(fb) for _, fb in valid_files) / 1024
    st.markdown(
        f'<div class="success-box">'
        f"<strong>{len(valid_files)} file(s) ready:</strong> {file_list} — "
        f"{total_kb:.1f} KB total"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Preview first file
    first_name, first_bytes = valid_files[0]
    with st.expander(f"Preview: {first_name} (first 20 lines)", expanded=True):
        preview_lines = first_bytes.decode("utf-8", errors="replace").splitlines()[:20]
        st.code("\n".join(preview_lines), language="text")

    st.divider()
    btn_label = f"Analyze {len(valid_files)} File(s)" if len(valid_files) > 1 else "Analyze Log File"
    if st.button(btn_label, type="primary", width='stretch'):
        _run_analysis(user, db, valid_files, append_mode)


def _run_analysis(user, db, valid_files: list[tuple[str, bytes]], append_mode: bool):
    progress = st.progress(0, text="Saving files...")

    token = st.session_state.get("session_token", "anon")
    all_dfs = []

    for i, (filename, file_bytes) in enumerate(valid_files):
        suffix = Path(filename).suffix or ".log"
        temp_path = save_upload_to_temp(file_bytes, suffix)
        register_temp_file(token, temp_path)
        progress.progress(
            int(10 + 30 * (i / len(valid_files))),
            text=f"Parsing {filename}...",
        )
        df = parse_log_file(temp_path)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        progress.empty()
        st.warning("Could not parse any log entries from the uploaded file(s). Please check the file format.")
        return

    # Merge newly parsed frames together
    merged_new = all_dfs[0]
    for df in all_dfs[1:]:
        merged_new = merge_dataframes(merged_new, df)

    progress.progress(55, text=f"Parsed {len(merged_new)} entries. Running detection rules...")

    if append_mode and st.session_state.get("log_df") is not None:
        merged_df = merge_dataframes(st.session_state["log_df"], merged_new)
    else:
        merged_df = merged_new

    rules = get_enabled_rules(db)
    if not rules:
        progress.empty()
        st.warning("No detection rules are currently enabled. Ask the Administrator to configure rules.")
        return

    findings = run_analysis(merged_df, rules)
    progress.progress(90, text="Updating session...")

    existing_files = [] if not append_mode else st.session_state.get("analyzed_files", [])
    for filename, _ in valid_files:
        if filename not in existing_files:
            existing_files.append(filename)

    st.session_state["log_df"]           = merged_df
    st.session_state["analysis_results"] = findings
    st.session_state["analyzed_files"]   = existing_files

    filenames_str = ", ".join(f for f, _ in valid_files)
    log_action(
        user.id, ACTION_ANALYZE, db,
        file_name=filenames_str[:200],
        append_used=append_mode,
        details=f"Analyzed {len(merged_df)} entries with {len(rules)} rules. Threats: {len(findings)}.",
    )

    progress.progress(100, text="Done!")
    import time; time.sleep(0.4)
    progress.empty()

    threat_word = "threat" if len(findings) == 1 else "threats"
    severity_icon = (
        "🔴" if any(f["severity"] == "CRITICAL" for f in findings) else
        "🟠" if any(f["severity"] == "HIGH" for f in findings) else
        "✅" if not findings else "🟡"
    )

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
