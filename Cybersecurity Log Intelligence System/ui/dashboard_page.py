import time
import threading
from pathlib import Path

import streamlit as st

from config.settings import ROLE_ADMIN, ALLOWED_EXTENSIONS, now_ist
from ui.components import (
    show_severity_cards, show_findings_table, findings_to_csv_bytes,
    show_recommendations_panel, safe_ts_str, enable_global_drag_drop,
    plot_severity_pie, plot_threat_types, plot_timeline, plot_top_sources,
    plot_top_users, plot_rule_type_breakdown, threats_by_rule_table,
)
from services.threat_engine import get_enabled_rules, compute_summary
from services.analysis_runner import run_analysis_job, rules_to_dicts
from services.report_service import generate_pdf_report, get_report_filename
from services.email_service import send_pdf_report_email, is_smtp_configured
from services.audit_service import (
    log_action, ACTION_ANALYZE, ACTION_DOWNLOAD_REPORT, ACTION_EMAIL_REPORT,
)
from utils.validators import validate_file_extension
from utils.temp_file_manager import save_upload_to_temp, register_temp_file

_SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]


def _current_context() -> tuple[str, str]:
    """Application/Product + LeanIX ID/PIF ID entered for this session (stripped)."""
    application = (st.session_state.get("application") or "").strip()
    leanix_id = (st.session_state.get("leanix_id") or "").strip()
    return application, leanix_id


def render_dashboard(user, db):
    role_label = "Administrator" if user.role == ROLE_ADMIN else "IT Owner"

    st.markdown(
        f'<div class="page-header">'
        f'<div class="page-title">Security Dashboard</div>'
        f'<div class="page-subtitle">Welcome back &nbsp;|&nbsp; {role_label}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Upload + analyze (inline — no separate page navigation) ─────────────────
    _render_workspace(user, db)

    findings = st.session_state.get("analysis_results")

    if not findings:
        if findings == []:
            st.markdown(
                '<div class="success-box">No threats detected in the analyzed log file(s).</div>',
                unsafe_allow_html=True,
            )
        if user.role == ROLE_ADMIN:
            st.divider()
            _show_admin_stats(db)
        return

    # ── Results (inline, right below the uploader) ──────────────────────────────
    try:
        _render_results(user, db, findings)
    except Exception as exc:  # never let a render glitch crash the whole app
        st.error(f"Could not render results: {exc}")

    if user.role == ROLE_ADMIN:
        st.divider()
        _show_admin_stats(db)


# ── Upload / analyze workspace ──────────────────────────────────────────────────

def _render_context_fields() -> tuple[str, str, bool]:
    """Render the two mandatory inputs (Application/Product, LeanIX ID / PIF ID), shown
    just above the uploader.

    Both must be filled before the Analyze button is enabled — the uploader/drop area
    stays active so a file can be added first. Once an analysis is running or results
    exist, the fields lock for the rest of the session so every analyzed file is grouped
    under the same Application/Product + LeanIX/PIF ID. They reset only when the user
    clicks "Clear & New Analysis". Returns (application, leanix_id, ready).
    """
    locked = (
        st.session_state.get("analysis_running", False)
        or st.session_state.get("analysis_results") is not None
    )

    c1, c2 = st.columns(2)
    with c1:
        st.text_input(
            "Application / Product :red[*]",
            key="application",
            max_chars=150,
            disabled=locked,
        )
    with c2:
        st.text_input(
            "LeanIX ID / PIF ID :red[*]",
            key="leanix_id",
            max_chars=100,
            disabled=locked,
        )

    application, leanix_id = _current_context()
    ready = bool(application and leanix_id)

    if locked:
        st.caption(
            f"🔒 Session linked to **{application or 'N/A'}** | **{leanix_id or 'N/A'}**. "
            "**Clear & New Analysis** for a new session."
        )
    elif not ready:
        st.caption("Both fields are required to start the analysis.")

    return application, leanix_id, ready


def _render_workspace(user, db):
    st.markdown('<div class="section-title" style="margin-bottom:8px;">Upload &amp; Analyze Log Files</div>',
                unsafe_allow_html=True)

    # Drop area is always active — let users drop a file anywhere on the page.
    enable_global_drag_drop()

    running = st.session_state.get("analysis_running", False)

    # ── Session context (above the uploader) ────────────────────────────────────
    # IT Owners must tag each analysis with an Application/Product + LeanIX/PIF ID. The
    # Administrator analyses ad-hoc to TEST rules before publishing them, so those fields
    # are not shown for the admin and the Analyze button is never gated on them.
    if user.role == ROLE_ADMIN:
        ready = True
    else:
        _application, _leanix_id, ready = _render_context_fields()

    # The uploader is an "add files" control. Dropped files are moved into a persistent
    # staged list (a plain session key) that SURVIVES page navigation — the native
    # file_uploader cannot be re-populated after it unmounts when you switch pages, so the
    # staged list (not the drop box) is the single source of truth for what gets analyzed.
    allowed_types = [ext.lstrip(".") for ext in ALLOWED_EXTENSIONS]
    nonce = st.session_state.get("uploader_nonce", 0)
    dropped = st.file_uploader(
        "Choose one or more log files", type=allowed_types,
        accept_multiple_files=True, label_visibility="collapsed",
        key=f"log_uploader_{nonce}",
    ) or []
    if dropped and not running:
        _ingest_dropped(dropped)

    # A background analysis is in progress. Its progress + completion are driven by
    # the job state in session_state (NOT by the uploader), so leaving Home and
    # coming back keeps showing progress and never interrupts the running job.
    if running:
        _handle_running(user, db)
        return

    staged = st.session_state.get("staged_files", [])
    if not staged:
        return

    _render_staged_list(staged)

    btn_label = f"Analyze {len(staged)} File(s)" if len(staged) > 1 else "Analyze Log File"
    if not ready:
        st.caption("⚠️  Fill in **Application / Product** and **LeanIX ID / PIF ID** above to enable analysis.")
    if st.button(btn_label, type="primary", width='stretch', disabled=not ready):
        _start_analysis(user, db, list(staged))


def _ingest_dropped(dropped):
    """Move newly dropped files into the persistent staged list, then reset the uploader.

    Validates each file (invalid ones never get staged); names already staged are skipped
    (the uploader re-reports its files on every rerun). Bumps the uploader nonce so the
    widget remounts empty, keeping the staged list the single source of truth."""
    staged = list(st.session_state.get("staged_files", []))
    names = {n for n, _ in staged}
    added = False
    for uf in dropped:
        if uf.name in names:
            continue
        fb = uf.getvalue()
        if not validate_file_extension(uf.name):
            st.error(f"**{uf.name}**: File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")
            continue
        staged.append((uf.name, fb))
        names.add(uf.name)
        added = True
    if added:
        st.session_state["staged_files"] = staged
        st.session_state["uploader_nonce"] = st.session_state.get("uploader_nonce", 0) + 1
        st.rerun()


def _unstage_file(name):
    """on_click callback: drop one file from the staged list."""
    st.session_state["staged_files"] = [
        (n, b) for n, b in st.session_state.get("staged_files", []) if n != name
    ]


def _render_staged_list(staged):
    # Collapse the file list into an expander (dropdown) so a large batch doesn't stretch
    # the page. The label is FIXED (not the file count) so Streamlit keeps the open/closed
    # state the user chose across reruns — a changing label would make it a new expander and
    # snap it shut when a file is removed. Collapsed by default on first upload.
    with st.expander("View / remove files", expanded=False):
        for name, fb in staged:
            c_name, c_rm = st.columns([12, 1])
            with c_name:
                st.markdown(
                    f'<div style="padding:3px 0;color:#374151;">📄 <code>{name}</code> '
                    f'<span style="color:#9aa0a6;font-size:0.85rem;">({len(fb) / 1024:.1f} KB)</span></div>',
                    unsafe_allow_html=True,
                )
            with c_rm:
                st.button("✕", key=f"unstage_{name}", help="Remove file",
                          on_click=_unstage_file, args=(name,))


# ── Background analysis (runs in a detached thread + worker process) ────────────
#
# The job is kicked off in a daemon thread that writes progress/results into a
# plain dict ("holder"). Because it is detached from the Streamlit script run,
# navigating to another page does NOT stop it (request: analysis must not stop),
# and a script interruption can never leave the UI stuck "running" — completion
# is always detected on the next Home render via the holder.

def _job_worker(all_paths, rule_dicts, holder):
    """Runs in a separate thread. Touches NO Streamlit APIs — only the holder dict."""
    cancel_event = holder.get("cancel_event")

    def _cb(frac, text=""):
        holder["frac"] = frac
        if text:
            holder["text"] = text

    try:
        holder["result"] = run_analysis_job(
            all_paths, rule_dicts, progress_cb=_cb, cancel_event=cancel_event,
        )
    except Exception as exc:  # surfaced to the user on the next poll
        holder["error"] = str(exc)
    finally:
        holder["done"] = True


def _start_analysis(user, db, valid_files):
    token = st.session_state.get("session_token", "anon")

    # Analyze exactly the files currently in the uploader. Persist each to a temp file
    # (needs the session token).
    all_paths, file_names = [], []
    for filename, file_bytes in valid_files:
        temp_path = save_upload_to_temp(file_bytes, Path(filename).suffix or ".log")
        register_temp_file(token, temp_path)
        all_paths.append(temp_path)
        file_names.append(filename)

    # The Administrator's own analysis includes staged (not-yet-propagated) rules so
    # they can test a new/edited rule on Home before publishing it. IT Owners only run
    # rules that have been propagated to them.
    rules = get_enabled_rules(db, include_unpropagated=(user.role == ROLE_ADMIN))
    if not rules:
        st.warning("No detection rules are currently enabled. Ask the Administrator to configure rules.")
        return
    rule_dicts = rules_to_dicts(rules)

    # Per-job duration estimate for the linear, time-based progress bar — derived from
    # input size and the machine's measured speed from the previous run (self-calibrating).
    total_bytes = sum(len(fb) for _, fb in valid_files)
    bps = st.session_state.get("_analysis_bps", _DEFAULT_ANALYSIS_BPS)
    est_total_sec = min(_EST_MAX_SEC, max(_EST_MIN_SEC, total_bytes / max(bps, 1.0)))

    holder = {
        "frac": 0.0, "text": "Starting analysis…", "done": False,
        "result": None, "error": None, "cancel_event": threading.Event(),
        "total_bytes": total_bytes, "est_total_sec": est_total_sec,
        "start_time": time.monotonic(),
    }
    thread = threading.Thread(target=_job_worker, args=(all_paths, rule_dicts, holder), daemon=True)

    application, leanix_id = _current_context()
    st.session_state["job_holder"] = holder
    st.session_state["job_thread"] = thread
    st.session_state["job_meta"] = {
        "analyzed_files": file_names,
        "rule_count": len(rules),
        "application": application,
        "leanix_id": leanix_id,
    }
    st.session_state["analysis_running"] = True
    thread.start()
    st.rerun()


def _handle_running(user, db):
    """Render live progress for the active analysis on every full Home render.

    Everything here keys off the job state in session_state — never the file
    uploader — so navigating away and back neither hides the progress nor stops
    the job. Cancellation is an explicit button, not file removal.
    """
    holder = st.session_state.get("job_holder")
    if holder is None:
        st.session_state["analysis_running"] = False
        st.rerun()
        return

    thread = st.session_state.get("job_thread")
    # Safety net: thread died without flagging completion → don't hang the UI.
    if thread is not None and not thread.is_alive() and not holder.get("done"):
        if not holder.get("result") and not holder.get("error"):
            holder["error"] = "Analysis worker stopped unexpectedly."
        holder["done"] = True

    if holder.get("done"):
        _finalize(user, db)
        return

    # Live progress via a self-refreshing fragment — only this small block reruns
    # (~0.3s), so the rest of the page does NOT flicker while the bar updates.
    _progress_fragment()
    _, c_stop, _ = st.columns([2, 1, 2])
    with c_stop:
        if st.button("✕  Stop analysis", key="stop_analysis_btn", width='stretch'):
            _cancel_analysis()


# Linear, time-based progress: the bar fills with ELAPSED TIME against a per-job
# duration estimate (so a ~4-min run reads ~25% at 1 min, ~50% at 2 min, …) instead of
# tracking the choppy backend phases. It is capped just below 100% so an underestimate
# waits near the top rather than overshooting; the real completion fills it to 100%.
# The estimate self-calibrates from the previous run's measured bytes/sec, so it adapts
# to this machine (see _start_analysis / _finalize).
_PROGRESS_TIME_CAP = 0.99
_DEFAULT_ANALYSIS_BPS = 220_000      # bytes/sec seed (~49.8 MB ≈ 4 min) until calibrated
_EST_MIN_SEC = 6.0
_EST_MAX_SEC = 1800.0


@st.fragment(run_every=0.3)
def _progress_fragment():
    holder = st.session_state.get("job_holder")
    if holder is None:
        st.rerun()
        return

    thread = st.session_state.get("job_thread")
    if thread is not None and not thread.is_alive() and not holder.get("done"):
        if not holder.get("result") and not holder.get("error"):
            holder["error"] = "Analysis worker stopped unexpectedly."
        holder["done"] = True

    if holder.get("done"):
        st.rerun()  # full-app rerun → _handle_running() finalizes and shows results
        return

    # Linear time-based fill: advance with ELAPSED TIME against this job's duration
    # estimate so the bar climbs steadily (≈25% per quarter of the estimate) rather than
    # tracking the choppy backend phases. Capped just below 100%; the real completion
    # (handled above via holder["done"]) is what finishes it. The status text still
    # reflects the real phase ("Parsing… N entries" / "Running detection rules…").
    start = holder.get("start_time")
    est = holder.get("est_total_sec") or 60.0
    if start is None:
        disp = holder.get("frac") or 0.0
    else:
        elapsed = max(0.0, time.monotonic() - start)
        disp = min(elapsed / est, _PROGRESS_TIME_CAP)

    pct = max(0, min(int(disp * 100), 100))
    st.progress(pct, text=holder.get("text") or "Analyzing…")


def _cancel_analysis():
    holder = st.session_state.get("job_holder")
    if holder is not None:
        ev = holder.get("cancel_event")
        if ev is not None:
            ev.set()  # tells the worker thread to terminate its subprocess
    for k in ("job_holder", "job_thread", "job_meta"):
        st.session_state.pop(k, None)
    st.session_state["analysis_running"] = False
    try:
        st.toast("Analysis stopped.")
    except Exception:
        # Toast is cosmetic; never block cancellation on a UI glitch.
        pass  # nosec B110
    st.rerun()


def _finalize(user, db):
    holder = st.session_state.get("job_holder") or {}
    meta = st.session_state.get("job_meta", {}) or {}
    result = holder.get("result") or {}
    err = holder.get("error") or result.get("error")

    # Self-calibrate the time-based bar from this run's real duration (successful runs
    # only) so the next analysis's estimate matches this machine's actual speed (EWMA).
    if not result.get("cancelled") and not err:
        _start = holder.get("start_time")
        _nbytes = holder.get("total_bytes") or 0
        if _start is not None and _nbytes > 0:
            _actual = time.monotonic() - _start
            if _actual >= 1.0:
                _bps = _nbytes / _actual
                _prev = st.session_state.get("_analysis_bps", _DEFAULT_ANALYSIS_BPS)
                st.session_state["_analysis_bps"] = 0.5 * _prev + 0.5 * _bps

    for k in ("job_holder", "job_thread", "job_meta"):
        st.session_state.pop(k, None)
    st.session_state["analysis_running"] = False

    if result.get("cancelled"):
        return
    if err:
        st.error(f"Analysis failed: {err}. Please try again or check the file.")
        return

    total_entries = result.get("total_entries", 0)
    if total_entries == 0:
        st.warning("Could not parse any log entries from the uploaded file(s). Please check the file format.")
        return

    findings = result.get("findings", [])
    analyzed_files = list(meta.get("analyzed_files", []))

    st.session_state["analysis_results"] = findings
    st.session_state["analyzed_files"] = analyzed_files
    st.session_state["log_df"] = result.get("raw_sample")
    st.session_state["log_total"] = total_entries

    try:
        log_action(
            user.id, ACTION_ANALYZE, db,
            file_name=", ".join(analyzed_files)[:200],
            application=meta.get("application", ""),
            leanix_id=meta.get("leanix_id", ""),
            details=(f"Analyzed {total_entries} entries with {meta.get('rule_count', 0)} "
                     f"rules. Threats: {len(findings)}."),
        )
    except Exception:
        # Audit logging is best-effort; must not block showing results.
        pass  # nosec B110

    st.rerun()


# ── Results ──────────────────────────────────────────────────────────────────

def _render_results(user, db, findings):
    summary = compute_summary(findings)
    analyzed_files = st.session_state.get("analyzed_files", [])

    st.divider()

    # ── Action row (directly below the Analyze Log File button) ─────────────────
    smtp_ready = is_smtp_configured()
    is_admin = user.role == ROLE_ADMIN

    # Email Report is available to BOTH roles. When SMTP isn't configured the button is
    # shown disabled with a role-appropriate hint (only the Administrator can set up SMTP).
    cols = st.columns(3)
    with cols[0]:
        if st.button("Generate PDF Report", width='stretch', type="primary", key="gen_pdf_btn"):
            st.session_state["_do_pdf"] = True
    with cols[1]:
        if smtp_ready:
            if st.button("Email Report", width='stretch', key="email_pdf_btn"):
                st.session_state["_do_email"] = True
        else:
            st.button("Email Report", width='stretch', key="email_pdf_btn", disabled=True)
            st.caption("Email unavailable — configure SMTP in Settings." if is_admin
                       else "Email unavailable — contact your Administrator.")
    with cols[2]:
        # Clearing runs as an on_click callback so the Application/LeanIX text-input keys
        # can be safely reset before the widgets re-instantiate on the next run.
        st.button("Clear & New Analysis", width='stretch', key="clear_btn",
                  on_click=_clear_and_new_analysis)

    _handle_pdf(user, db, findings, analyzed_files)
    _handle_email(user, db, findings, summary, analyzed_files)

    # ── Severity summary ────────────────────────────────────────────────────────
    show_severity_cards(summary)

    st.divider()

    # ── Tabs: Visualizations → Findings Table → Recommended Actions → Raw Log ───
    # The marker lets CSS center THIS tab group (the Rules tabs stay left-aligned).
    st.markdown('<span class="viz-tabs-marker"></span>', unsafe_allow_html=True)
    tab_viz, tab_find, tab_rec, tab_raw = st.tabs(
        ["Visualizations", "Findings Table", "Recommended Actions", "Raw Log Data"]
    )
    with tab_viz:
        _render_visualizations(findings)
    with tab_find:
        _render_findings_tab(findings)
    with tab_rec:
        show_recommendations_panel(findings)
    with tab_raw:
        _render_raw_log_tab()


@st.fragment
def _render_findings_tab(findings):
    # A fragment so the severity filter + search box refresh ONLY this table locally —
    # the page (and the Plotly charts in the sibling tab) is not re-rendered on each
    # keystroke / filter change, which keeps the results view snappy.
    # Left column holds the severity filter AND the search box (stacked); the
    # "Showing" metric sits to their right — no empty gap.
    c_filter, c_count = st.columns([3, 1])
    with c_filter:
        sev_filter = st.multiselect(
            "Filter by Severity", options=_SEVERITIES, default=_SEVERITIES,
            label_visibility="collapsed", key="sev_filter",
        )
        # Full-width search box (no reserved column → no gap on the right).
        search = st.text_input(
            "Search findings",
            placeholder="🔍  Search by IP, username, rule, or description…",
            label_visibility="collapsed", key="findings_search",
        )
        # Borderless ✕ overlaid on the right edge of the box (CSS lifts it onto the
        # input and shows it only once text is typed).
        st.button("✕", key="clear_search_btn", on_click=_clear_search, help="Clear search")

    filtered = [f for f in findings if f.get("severity") in sev_filter]
    q = search.strip().lower()
    if q:
        filtered = [f for f in filtered if _matches_search(f, q)]

    with c_count:
        st.metric("Showing", f"{len(filtered)} / {len(findings)}")

    show_findings_table(filtered)

    if filtered:
        csv = findings_to_csv_bytes(filtered)
        _, c_dl, _ = st.columns([1, 2, 1])
        with c_dl:
            st.download_button(
                "Download findings (CSV)", data=csv,
                file_name="threat_findings.csv", mime="text/csv",
                width='stretch', key="dl_findings",
            )


def _clear_search():
    # Runs as a button on_click callback (before the widget re-instantiates),
    # so resetting the key here clears the search box on the next render.
    st.session_state["findings_search"] = ""


def _clear_and_new_analysis():
    """Reset the whole analysis session, including the Application/Product + LeanIX/PIF
    context so both fields are requested again. Runs as an on_click callback (before any
    widget re-instantiates), so clearing the text-input + uploader keys is safe."""
    # Retire the current uploader widget (and bump the nonce) so the staged file is
    # dropped from the drop box on the next render.
    nonce = st.session_state.get("uploader_nonce", 0)
    st.session_state.pop(f"log_uploader_{nonce}", None)
    st.session_state["uploader_nonce"] = nonce + 1

    for k in ["analysis_results", "log_df", "log_total", "analyzed_files",
              "staged_files", "_do_pdf", "_do_email", "application", "leanix_id"]:
        st.session_state.pop(k, None)
    st.session_state["analyzed_files"] = []


def _matches_search(f: dict, q: str) -> bool:
    parts = [
        str(f.get("severity", "")), str(f.get("rule_name", "")),
        str(f.get("source_ip") or ""), str(f.get("username") or ""),
        str(f.get("description", "")), str(f.get("line_num") or ""),
        safe_ts_str(f.get("timestamp")),
    ]
    return q in " ".join(parts).lower()


def _render_visualizations(findings):
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        fig = plot_severity_pie(findings)
        if fig:
            st.plotly_chart(fig)
    with c2:
        fig = plot_threat_types(findings)
        if fig:
            st.plotly_chart(fig)

    fig = plot_timeline(findings)
    if fig:
        st.plotly_chart(fig)
    else:
        st.caption("Timeline unavailable — no parseable timestamps in findings.")

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        fig = plot_top_sources(findings)
        if fig:
            st.plotly_chart(fig)
        else:
            st.caption("No source IP data available.")
    with c4:
        fig = plot_top_users(findings)
        if fig:
            st.plotly_chart(fig)
        else:
            st.caption("No username data available.")

    fig = plot_rule_type_breakdown(findings)
    if fig:
        st.plotly_chart(fig)

    # Aggregated table of threats per rule
    by_rule = threats_by_rule_table(findings)
    if not by_rule.empty:
        st.markdown('<div class="section-title" style="margin-top:8px;">Threats by Rule</div>',
                    unsafe_allow_html=True)
        st.dataframe(by_rule, width='stretch', hide_index=True, height=300)


def _render_raw_log_tab():
    log_df = st.session_state.get("log_df")
    total = st.session_state.get("log_total", 0)
    if log_df is not None and not log_df.empty:
        note = f"<strong>{total:,}</strong> raw log entries parsed."
        if total > len(log_df):
            note += f" Showing a sample of the first {len(log_df):,} entries."
        st.markdown(f'<div class="info-box">{note}</div>', unsafe_allow_html=True)
        st.dataframe(log_df, width='stretch', hide_index=True)
    else:
        st.info("No raw log data available.")


# ── PDF / Email handlers ────────────────────────────────────────────────────────

def _handle_pdf(user, db, findings, analyzed_files):
    if not st.session_state.pop("_do_pdf", False):
        return
    application, leanix_id = _current_context()
    with st.spinner("Generating PDF report…"):
        try:
            pdf_bytes = generate_pdf_report(
                findings=findings, username=user.username, email=user.email,
                analyzed_files=analyzed_files,
                application=application, leanix_id=leanix_id,
            )
            filename = get_report_filename(analyzed_files)
            log_action(user.id, ACTION_DOWNLOAD_REPORT, db, details=f"PDF generated: {filename}",
                       application=application, leanix_id=leanix_id)
            st.download_button(
                label="Download PDF Report", data=pdf_bytes, file_name=filename,
                mime="application/pdf", width='stretch', type="primary", key="dl_pdf",
            )
        except Exception as exc:
            st.error(f"PDF generation failed: {exc}")


def _handle_email(user, db, findings, summary, analyzed_files):
    if not st.session_state.pop("_do_email", False):
        return
    application, leanix_id = _current_context()
    with st.spinner("Generating and sending report…"):
        try:
            pdf_bytes = generate_pdf_report(
                findings=findings, username=user.username, email=user.email,
                analyzed_files=analyzed_files,
                application=application, leanix_id=leanix_id,
            )
            filename = get_report_filename(analyzed_files)
            # Attach the full findings table as CSV alongside the PDF (same data as the
            # dashboard "Download findings (CSV)" button); the table is also embedded in
            # the email body by the email service.
            csv_bytes = findings_to_csv_bytes(findings)
            csv_filename = f"threat_findings_{now_ist().strftime('%Y%m%d_%H%M%S')}.csv"

            # An IT Owner's report is also sent to the Administrator (greeted by name, with
            # a subject identifying the IT Owner). An Administrator's report goes only to
            # the Administrator.
            admin_email = admin_name = None
            if user.role != ROLE_ADMIN:
                admin_email, admin_name = _lookup_admin(db, exclude_email=user.email)

            recipients = [user.email] + ([admin_email] if admin_email else [])
            sent = send_pdf_report_email(
                to_email=user.email, username=user.username, pdf_bytes=pdf_bytes,
                report_filename=filename, summary=summary,
                analyzed_files=analyzed_files,
                admin_email=admin_email, admin_name=admin_name,
                csv_bytes=csv_bytes, csv_filename=csv_filename,
                application=application, leanix_id=leanix_id,
            )
            if sent:
                st.success(f"Report emailed to: **{', '.join(recipients)}**.")
                log_action(user.id, ACTION_EMAIL_REPORT, db,
                           details=f"Report emailed to {', '.join(recipients)}",
                           application=application, leanix_id=leanix_id)
            else:
                st.warning("Email delivery failed. Use **Generate PDF Report** to download it instead.")
        except Exception as exc:
            st.error(f"Failed to send report: {exc}")


def _lookup_admin(db, exclude_email: str = "") -> tuple["str | None", "str | None"]:
    """Return (email, username) of the Administrator to also notify, or (None, None).

    Skips the Administrator when they are the uploader (same email)."""
    try:
        from database.models import User
        admin = db.query(User).filter_by(role=ROLE_ADMIN).first()
        if admin and admin.email and admin.email.lower() != (exclude_email or "").lower():
            return admin.email, admin.username
    except Exception:
        # Admin-cc lookup is best-effort; the uploader still gets the report.
        pass  # nosec B110
    return None, None


# ── Admin stats ────────────────────────────────────────────────────────────────

def _show_admin_stats(db):
    from database.models import User, DetectionRule, AuditLog
    st.markdown(
        '<div class="section-title" style="font-size:1rem;font-weight:700;color:#1e3a5f;margin-bottom:12px;">'
        "System Overview</div>",
        unsafe_allow_html=True,
    )
    try:
        active_users  = db.query(User).filter_by(is_active=True).count()
        active_rules  = db.query(DetectionRule).filter_by(is_enabled=True).count()
        audit_entries = db.query(AuditLog).count()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Active Users", active_users)
        with c2:
            st.metric("Active Detection Rules", active_rules)
        with c3:
            st.metric("Audit Log Entries", audit_entries)
    except Exception as exc:
        st.caption(f"Could not load system stats: {exc}")