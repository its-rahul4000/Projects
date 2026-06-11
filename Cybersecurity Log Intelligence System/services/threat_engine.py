import re
import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

import pandas as pd

from database.models import DetectionRule

logger = logging.getLogger(__name__)

# ── Patterns used by dynamic rule conditions ────────────────────────────────
_P_FAILED_LOGIN = re.compile(
    r'(?i)(failed\s+(login|authentication|password|auth)|'
    r'authentication\s+fail|login\s+fail|invalid\s+(credentials?|password|username)|'
    r'auth\s+fail|wrong\s+password|bad\s+password|incorrect\s+password)',
)
_P_SUCCESS_LOGIN = re.compile(
    r'(?i)(login\s+success|authentication\s+success|logged\s+in|'
    r'access\s+granted|session\s+(created|opened|started)|'
    r'user\s+authenticated|accepted\s+password)',
)
_P_ACCESS_DENIED = re.compile(r'(?i)(access\s+denied|\b403\b|\bforbidden\b|\bunauthorized\b|permission\s+denied)')
_P_ERROR = re.compile(r'(?i)\b(error|critical|fatal|exception|traceback|failure)\b')
_P_SERVICE_CRASH = re.compile(
    r'(?i)(service\s+(crash|restart|failed|stopped)|systemd.*failed|'
    r'process\s+kill|segmentation\s+fault|core\s+dump|fatal\s+error|killed\s+by\s+signal)',
)
_P_RESOURCE = re.compile(
    r'(?i)(out\s+of\s+memory|disk\s+full|too\s+many\s+(connections?|open\s+files?)|'
    r'no\s+space\s+left|memory\s+(allocation\s+)?fail|swap\s+full|cpu\s+(overload|100%))',
)
_P_SHUTDOWN = re.compile(
    r'(?i)(shutting\s+down|system\s+halt|terminated\s+unexpectedly|'
    r'killed\s+(by\s+signal|pid)|process\s+exit\s+\d+|SIGKILL|SIGTERM\s+received|'
    r'abnormal\s+(termination|exit)|crash\s+detect)',
)
_P_CONFIG = re.compile(
    r'(?i)(configuration\s+(changed|modified|updated)|config\s+(changed|update|modified)|'
    r'setting\s+(modified|changed)|parameter\s+(changed|updated)|policy\s+updated)',
)
_P_DB_ERROR = re.compile(
    r'(?i)(database\s+(error|fail|down)|sql\s+(error|exception)|'
    r'connection\s+refused.*(?:db|database|mysql|postgres|sqlite)|'
    r'query\s+fail|deadlock\s+detect|table\s+lock|db\s+conn.*fail)',
)
_P_HOURS = re.compile(r'(?i)(T|\s)(\d{2}):\d{2}:\d{2}')


def get_enabled_rules(db) -> list[DetectionRule]:
    return db.query(DetectionRule).filter_by(is_enabled=True).all()


def run_analysis(log_df: pd.DataFrame, rules: list[DetectionRule]) -> list[dict]:
    if log_df is None or log_df.empty:
        return []

    findings = []
    for rule in rules:
        try:
            if rule.condition.startswith("DYNAMIC:"):
                new_findings = _apply_behavioural_rule(rule, log_df)
            elif rule.rule_type == "dynamic":
                new_findings = _apply_dynamic_rule(rule, log_df)
            else:
                new_findings = _apply_static_rule(rule, log_df)
            findings.extend(new_findings)
        except Exception as exc:
            logger.warning("Rule '%s' evaluation failed: %s", rule.rule_name, exc)

    findings.sort(key=lambda f: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}.get(f["severity"], 0), reverse=True)
    return findings


def _apply_static_rule(rule: DetectionRule, df: pd.DataFrame) -> list[dict]:
    try:
        pattern = re.compile(rule.condition, re.IGNORECASE)
    except re.error as exc:
        logger.warning("Invalid regex in rule '%s': %s", rule.rule_name, exc)
        return []

    findings = []
    for _, row in df.iterrows():
        text = str(row.get("raw", "")) or str(row.get("message", ""))
        if pattern.search(text):
            findings.append(_make_finding(rule, row, text[:200]))
    return findings


def _apply_dynamic_rule(rule: DetectionRule, df: pd.DataFrame) -> list[dict]:
    condition = rule.condition
    threshold = rule.default_threshold or 1
    window = rule.time_window_seconds or 300

    dispatch = {
        "brute_force": _check_brute_force,
        "repeated_failed_logins": _check_repeated_failed_logins,
        "rapid_login_attempts": _check_rapid_logins,
        "multi_user_failures": _check_multi_user_failures,
        "repeated_access_denials": _check_repeated_denials,
        "error_rate_spike": _check_error_rate,
        "service_crash_loop": _check_service_crash,
        "rapid_sequential_actions": _check_rapid_actions,
        "mass_data_access": _check_mass_data,
        "resource_exhaustion": _check_resource_exhaustion,
        "unexpected_shutdown": _check_unexpected_shutdown,
        "configuration_change": _check_config_change,
        "database_error_spike": _check_db_error,
    }

    checker = dispatch.get(condition)
    if checker is None:
        logger.warning("Unknown dynamic condition key: %s", condition)
        return []

    return checker(rule, df, threshold, window)


def _apply_behavioural_rule(rule: DetectionRule, df: pd.DataFrame) -> list[dict]:
    """Handle rules whose condition starts with 'DYNAMIC:'"""
    key = rule.condition.split(":", 1)[1]
    threshold = rule.default_threshold or 3
    window = rule.time_window_seconds or 300

    if key == "unusual_hours":
        return _check_unusual_hours(rule, df)
    if key == "off_hours_access":
        return _check_off_hours_access(rule, df)
    if key == "login_after_failures":
        return _check_login_after_failures(rule, df, threshold)
    return []


# ── Dynamic checkers ─────────────────────────────────────────────────────────

def _check_brute_force(rule, df, threshold, window) -> list[dict]:
    failed = df[df["raw"].str.contains(_P_FAILED_LOGIN.pattern, case=False, na=False, regex=True)]
    if failed.empty:
        return []
    findings = []
    by_ip = defaultdict(list)
    for _, row in failed.iterrows():
        ip = row.get("source_ip")
        if ip:
            by_ip[ip].append(row)
    for ip, rows in by_ip.items():
        if len(rows) >= threshold:
            r = rows[0]
            findings.append(_make_finding(
                rule, r,
                f"IP {ip} had {len(rows)} failed login(s) (threshold={threshold}).",
            ))
    return findings


def _check_repeated_failed_logins(rule, df, threshold, window) -> list[dict]:
    failed = df[df["raw"].str.contains(_P_FAILED_LOGIN.pattern, case=False, na=False, regex=True)]
    if failed.empty:
        return []
    findings = []
    by_user = defaultdict(list)
    for _, row in failed.iterrows():
        user = row.get("username")
        if user:
            by_user[user].append(row)
    for user, rows in by_user.items():
        if len(rows) >= threshold:
            findings.append(_make_finding(
                rule, rows[0],
                f"User '{user}' had {len(rows)} failed logins (threshold={threshold}).",
            ))
    return findings


def _check_rapid_logins(rule, df, threshold, window) -> list[dict]:
    login_lines = df[
        df["raw"].str.contains(_P_FAILED_LOGIN.pattern, case=False, na=False, regex=True) |
        df["raw"].str.contains(_P_SUCCESS_LOGIN.pattern, case=False, na=False, regex=True)
    ]
    if len(login_lines) >= threshold:
        r = login_lines.iloc[0]
        return [_make_finding(rule, r, f"Total {len(login_lines)} login attempts detected (threshold={threshold}).")]
    return []


def _check_multi_user_failures(rule, df, threshold, window) -> list[dict]:
    failed = df[df["raw"].str.contains(_P_FAILED_LOGIN.pattern, case=False, na=False, regex=True)]
    if failed.empty:
        return []
    findings = []
    by_ip = defaultdict(set)
    for _, row in failed.iterrows():
        ip = row.get("source_ip")
        user = row.get("username")
        if ip and user:
            by_ip[ip].add(user)
    for ip, users in by_ip.items():
        if len(users) >= threshold:
            r = failed[failed["source_ip"] == ip].iloc[0]
            findings.append(_make_finding(
                rule, r,
                f"IP {ip} failed logins for {len(users)} different users (credential stuffing, threshold={threshold}).",
            ))
    return findings


def _check_repeated_denials(rule, df, threshold, window) -> list[dict]:
    denied = df[df["raw"].str.contains(_P_ACCESS_DENIED.pattern, case=False, na=False, regex=True)]
    if denied.empty:
        return []
    findings = []
    by_ip = defaultdict(int)
    for _, row in denied.iterrows():
        ip = row.get("source_ip") or "unknown"
        by_ip[ip] += 1
    for ip, count in by_ip.items():
        if count >= threshold:
            r = denied.iloc[0]
            findings.append(_make_finding(
                rule, r,
                f"Source {ip} had {count} access denied events (threshold={threshold}).",
            ))
    return findings


def _check_error_rate(rule, df, threshold, window) -> list[dict]:
    errors = df[df["raw"].str.contains(_P_ERROR.pattern, case=False, na=False, regex=True)]
    if len(errors) >= threshold:
        r = errors.iloc[0]
        return [_make_finding(rule, r, f"{len(errors)} error-level events detected (threshold={threshold}).")]
    return []


def _check_service_crash(rule, df, threshold, window) -> list[dict]:
    crashes = df[df["raw"].str.contains(_P_SERVICE_CRASH.pattern, case=False, na=False, regex=True)]
    if len(crashes) >= threshold:
        r = crashes.iloc[0]
        return [_make_finding(rule, r, f"{len(crashes)} service crash/restart events detected (threshold={threshold}).")]
    return []


def _check_rapid_actions(rule, df, threshold, window) -> list[dict]:
    if len(df) >= threshold:
        r = df.iloc[0]
        return [_make_finding(rule, r, f"{len(df)} log entries detected — possible automated/rapid activity (threshold={threshold}).")]
    return []


def _check_mass_data(rule, df, threshold, window) -> list[dict]:
    if len(df) >= threshold:
        r = df.iloc[0]
        return [_make_finding(rule, r, f"{len(df)} log entries indicate potential mass data access (threshold={threshold}).")]
    return []


def _check_resource_exhaustion(rule, df, threshold, window) -> list[dict]:
    hits = df[df["raw"].str.contains(_P_RESOURCE.pattern, case=False, na=False, regex=True)]
    if hits.empty:
        return []
    return [_make_finding(rule, hits.iloc[0], f"Resource exhaustion event: {hits.iloc[0]['raw'][:150]}")]


def _check_unexpected_shutdown(rule, df, threshold, window) -> list[dict]:
    hits = df[df["raw"].str.contains(_P_SHUTDOWN.pattern, case=False, na=False, regex=True)]
    if hits.empty:
        return []
    return [_make_finding(rule, hits.iloc[0], f"Unexpected shutdown/termination detected: {hits.iloc[0]['raw'][:150]}")]


def _check_config_change(rule, df, threshold, window) -> list[dict]:
    hits = df[df["raw"].str.contains(_P_CONFIG.pattern, case=False, na=False, regex=True)]
    if hits.empty:
        return []
    return [_make_finding(rule, hits.iloc[0], f"Configuration change detected: {hits.iloc[0]['raw'][:150]}")]


def _check_db_error(rule, df, threshold, window) -> list[dict]:
    hits = df[df["raw"].str.contains(_P_DB_ERROR.pattern, case=False, na=False, regex=True)]
    if len(hits) >= threshold:
        return [_make_finding(rule, hits.iloc[0], f"{len(hits)} database error events (threshold={threshold}).")]
    return []


def _check_unusual_hours(rule, df) -> list[dict]:
    ts_col = df["timestamp"].dropna()
    if ts_col.empty:
        return []
    total = len(ts_col)
    outside = ts_col[(ts_col.dt.hour < 9) | (ts_col.dt.hour >= 17)]
    if total > 0 and (len(outside) / total) > 0.5:
        r = df.iloc[0]
        return [_make_finding(rule, r, f"{len(outside)}/{total} events ({len(outside)*100//total}%) outside business hours (09:00–17:00).")]
    return []


def _check_off_hours_access(rule, df) -> list[dict]:
    success = df[df["raw"].str.contains(_P_SUCCESS_LOGIN.pattern, case=False, na=False, regex=True)]
    ts_col = success["timestamp"].dropna()
    if ts_col.empty:
        return []
    night = ts_col[(ts_col.dt.hour >= 0) & (ts_col.dt.hour < 5)]
    if not night.empty:
        idx = night.index[0]
        r = success.loc[idx]
        return [_make_finding(rule, r, f"Successful login at {night.iloc[0].strftime('%H:%M:%S')} (off-hours: 00:00–05:00).")]
    return []


def _check_login_after_failures(rule, df, threshold) -> list[dict]:
    findings = []
    by_user: dict[str, list[dict]] = defaultdict(list)

    for _, row in df.iterrows():
        user = row.get("username")
        raw = str(row.get("raw", ""))
        if not user:
            continue
        if _P_FAILED_LOGIN.search(raw):
            by_user[user].append({"success": False, "row": row})
        elif _P_SUCCESS_LOGIN.search(raw):
            by_user[user].append({"success": True, "row": row})

    for user, events in by_user.items():
        consecutive_fail = 0
        for event in events:
            if not event["success"]:
                consecutive_fail += 1
            else:
                if consecutive_fail >= threshold:
                    r = event["row"]
                    findings.append(_make_finding(
                        rule, r,
                        f"User '{user}' logged in successfully after {consecutive_fail} consecutive failures.",
                    ))
                consecutive_fail = 0

    return findings


def _safe_ts(ts):
    """Convert pd.NaT / NaN / None to None; leave real datetimes untouched."""
    if ts is None:
        return None
    try:
        if pd.isnull(ts):
            return None
    except (TypeError, ValueError):
        pass
    return ts


def _make_finding(rule: DetectionRule, row, description: str) -> dict:
    ts = _safe_ts(row.get("timestamp"))
    return {
        "rule_name": rule.rule_name,
        "severity": rule.severity.upper(),
        "rule_type": rule.rule_type,
        "description": description,
        "source_ip": row.get("source_ip"),
        "username": row.get("username"),
        "timestamp": ts,
        "line_num": row.get("line_num"),
        "matched_text": str(row.get("raw", ""))[:300],
    }


def compute_summary(findings: list[dict]) -> dict:
    summary = {"total": len(findings), "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
    for f in findings:
        sev = f.get("severity", "INFO")
        summary[sev] = summary.get(sev, 0) + 1
    return summary
