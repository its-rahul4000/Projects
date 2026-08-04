import os
import re
import math
import logging
import warnings
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from database.models import DetectionRule
from config.settings import ANALYSIS_MAX_WORKERS
# Imported (not inlined) so the function lives in a stdlib-only module — spawned worker
# processes import THAT, not this pandas-heavy module, keeping child startup cheap.
from services._static_match import match_chunk

logger = logging.getLogger(__name__)

# Cap findings stored per rule. A 400k-line log can match a single rule on tens of
# thousands of lines; storing every match explodes memory and the UI for no benefit.
# We keep a representative sample and report the true match count in the description.
MAX_FINDINGS_PER_RULE = 1000

# Below this row count, parallel static matching is skipped — the process-pool spin-up
# would cost more than it saves on a small log.
_PARALLEL_MIN_ROWS = 50_000


def _worker_count() -> int:
    """Cores to use for parallel matching (never more than the CPU count)."""
    return max(1, min(int(ANALYSIS_MAX_WORKERS), os.cpu_count() or 1))


def _parallel_static_match(texts: list[str], patterns: list[str],
                           workers: int) -> list[list[int]]:
    """Split the text column across cores and match all patterns on each chunk.

    The per-chunk work runs in ``services._static_match.match_chunk`` — a stdlib-only
    module — so spawned children start fast (no pandas import). Returns, per pattern,
    the GLOBAL ascending row indices that matched; chunks are collected in submission
    order so the merged indices stay ascending.
    """
    n = len(texts)
    result: list[list[int]] = [[] for _ in patterns]
    if n == 0:
        return result
    chunk = max(1, math.ceil(n / workers))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        submitted = []
        for start in range(0, n, chunk):
            submitted.append((start, ex.submit(match_chunk, texts[start:start + chunk], patterns)))
        for start, fut in submitted:
            per_pat = fut.result()
            for pi, locs in enumerate(per_pat):
                if locs:
                    result[pi].extend(start + loc for loc in locs)
    return result


# ── Patterns used by behavioural rule conditions ─────────────────────────────
# All groups changed to non-capturing (?:) to suppress pandas str.contains warning

_P_FAILED_LOGIN = re.compile(
    r'(?:failed\s+(?:login|authentication|password|auth)|'
    r'authentication\s+fail|login\s+fail|invalid\s+(?:credentials?|password|username)|'
    r'auth\s+fail|wrong\s+password|bad\s+password|incorrect\s+password)',
    re.IGNORECASE,
)
_P_SUCCESS_LOGIN = re.compile(
    r'(?:login\s+success|authentication\s+success|logged\s+in|'
    r'access\s+granted|session\s+(?:created|opened|started)|'
    r'user\s+authenticated|accepted\s+password)',
    re.IGNORECASE,
)
_P_ACCESS_DENIED = re.compile(
    r'(?:access\s+denied|\b403\b|\bforbidden\b|\bunauthorized\b|permission\s+denied)',
    re.IGNORECASE,
)
_P_ERROR = re.compile(r'\b(?:error|critical|fatal|exception|traceback|failure)\b', re.IGNORECASE)
_P_SERVICE_CRASH = re.compile(
    r'(?:service\s+(?:crash|restart|failed|stopped)|systemd.*failed|'
    r'process\s+kill|segmentation\s+fault|core\s+dump|fatal\s+error|killed\s+by\s+signal)',
    re.IGNORECASE,
)
_P_RESOURCE = re.compile(
    r'(?:out\s+of\s+memory|disk\s+full|too\s+many\s+(?:connections?|open\s+files?)|'
    r'no\s+space\s+left|memory\s+(?:allocation\s+)?fail|swap\s+full|cpu\s+(?:overload|100%))',
    re.IGNORECASE,
)
_P_SHUTDOWN = re.compile(
    r'(?:shutting\s+down|system\s+halt|terminated\s+unexpectedly|'
    r'killed\s+(?:by\s+signal|pid)|process\s+exit\s+\d+|SIGKILL|SIGTERM\s+received|'
    r'abnormal\s+(?:termination|exit)|crash\s+detect)',
    re.IGNORECASE,
)
_P_CONFIG = re.compile(
    r'(?:configuration\s+(?:changed|modified|updated)|config\s+(?:changed|update|modified)|'
    r'setting\s+(?:modified|changed)|parameter\s+(?:changed|updated)|policy\s+updated)',
    re.IGNORECASE,
)
_P_DB_ERROR = re.compile(
    r'(?:database\s+(?:error|fail|down)|sql\s+(?:error|exception)|'
    r'connection\s+refused.*(?:db|database|mysql|postgres|sqlite)|'
    r'query\s+fail|deadlock\s+detect|table\s+lock|db\s+conn.*fail)',
    re.IGNORECASE,
)
_P_HOURS = re.compile(r'(?:T|\s)(\d{2}):\d{2}:\d{2}', re.IGNORECASE)


class _MaskCache:
    """Computes each regex mask over the raw-text column at most ONCE and reuses it
    for every rule that needs it.

    Many rules scan for the same thing — e.g. five separate rules look for failed
    logins. Without caching, each one re-runs a full-column regex over hundreds of
    thousands of rows. Caching the boolean mask per pattern removes that redundant
    work and is the single biggest analysis speed-up on large logs.
    """

    def __init__(self, text_series: pd.Series):
        self._text = text_series
        self._cache: dict[str, pd.Series] = {}

    def mask(self, pattern: str) -> pd.Series:
        cached = self._cache.get(pattern)
        if cached is None:
            with warnings.catch_warnings():
                # Admin regexes may contain capturing groups; pandas warns but the
                # boolean result is unaffected.
                warnings.simplefilter("ignore", UserWarning)
                cached = self._text.str.contains(pattern, case=False, na=False, regex=True)
            self._cache[pattern] = cached
        return cached


def get_enabled_rules(db, include_unpropagated: bool = False) -> list[DetectionRule]:
    """Enabled rules to run for an analysis.

    IT Owners only ever run rules that have been propagated to them. The Administrator
    can additionally run staged (not-yet-propagated) rules so they can test a new or
    edited rule on their own Home page before publishing it to everyone — pass
    ``include_unpropagated=True`` for that case.
    """
    q = db.query(DetectionRule).filter_by(is_enabled=True)
    if not include_unpropagated:
        q = q.filter_by(is_propagated=True)
    return q.all()


def _is_prefixed_behavioral(rule) -> bool:
    cond = rule.condition or ""
    return cond.startswith("BEHAVIORAL:") or cond.startswith("DYNAMIC:")


def run_analysis(log_df: pd.DataFrame, rules: list[DetectionRule],
                 progress_cb=None, parallel: bool = False) -> list[dict]:
    """Evaluate all rules against the parsed log DataFrame.

    progress_cb, if given, is called with a float in [0, 1] as rules complete so the
    UI can show real progress. ``parallel`` enables multi-core matching of static
    (per-line regex) rules — only set by the isolated analysis worker process, never
    by the in-process fallback (so we never spawn child processes from Streamlit).
    """
    if log_df is None or log_df.empty:
        if progress_cb:
            progress_cb(1.0)
        return []

    # Pre-compute the text column ONCE (vectorized matching uses this for every rule).
    if "raw" in log_df.columns:
        text_series = log_df["raw"].fillna("").astype(str)
    else:
        text_series = log_df.get("message", pd.Series([""] * len(log_df))).fillna("").astype(str)

    # One mask cache shared across every rule → each regex scan runs at most once.
    mask_cache = _MaskCache(text_series)

    # Partition: per-line static regex rules can be matched in parallel; behavioural,
    # custom and BEHAVIORAL:-prefixed rules aggregate over the whole frame and run here.
    static_rules, other_rules = [], []
    for rule in rules:
        if _is_prefixed_behavioral(rule) or rule.rule_type in ("custom", "behavioral", "dynamic"):
            other_rules.append(rule)
        else:
            static_rules.append(rule)

    findings: list[dict] = []
    total = max(len(rules), 1)
    done = 0

    # ── Static rules ───────────────────────────────────────────────────────────
    use_parallel = (parallel and len(static_rules) > 1
                    and len(log_df) >= _PARALLEL_MIN_ROWS and _worker_count() > 1)
    if static_rules and use_parallel:
        try:
            findings.extend(_run_static_parallel(static_rules, log_df, text_series))
        except Exception as exc:
            logger.warning("Parallel static matching failed (%s); using single-process.", exc)
            for rule in static_rules:
                findings.extend(_safe_apply(_apply_static_rule, rule, log_df, mask_cache))
    else:
        for rule in static_rules:
            findings.extend(_safe_apply(_apply_static_rule, rule, log_df, mask_cache))
    done += len(static_rules)
    if progress_cb:
        progress_cb(done / total)

    # ── Behavioural / custom / prefixed rules ────────────────────────────────────
    for rule in other_rules:
        if _is_prefixed_behavioral(rule):
            findings.extend(_safe_apply(_apply_prefixed_behavioral_rule, rule, log_df, mask_cache))
        elif rule.rule_type == "custom":
            findings.extend(_safe_apply(_apply_custom_rule, rule, log_df, mask_cache))
        else:
            findings.extend(_safe_apply(_apply_behavioral_rule, rule, log_df, mask_cache))
        done += 1
        if progress_cb:
            progress_cb(done / total)

    findings.sort(
        key=lambda f: {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}.get(f["severity"], 0),
        reverse=True,
    )
    return findings


def _safe_apply(fn, rule, df, mask_cache) -> list[dict]:
    try:
        return fn(rule, df, mask_cache)
    except Exception as exc:
        logger.warning("Rule '%s' evaluation failed: %s", rule.rule_name, exc)
        return []


def _run_static_parallel(static_rules: list, df: pd.DataFrame,
                         text_series: pd.Series) -> list[dict]:
    """Match all static regex rules across CPU cores. Results are identical to the
    single-process path (per-line, per-row matching is order-independent)."""
    patterns, valid_rules = [], []
    for rule in static_rules:
        try:
            re.compile(rule.condition, re.IGNORECASE)
        except re.error as exc:
            logger.warning("Invalid regex in rule '%s': %s", rule.rule_name, exc)
            continue
        patterns.append(rule.condition)
        valid_rules.append(rule)
    if not patterns:
        return []

    texts = text_series.tolist()
    matched_per_rule = _parallel_static_match(texts, patterns, _worker_count())

    findings: list[dict] = []
    for rule, positions in zip(valid_rules, matched_per_rule):
        if not positions:
            continue
        recs = df.iloc[positions[:MAX_FINDINGS_PER_RULE]].to_dict("records")
        for rec in recs:
            text = str(rec.get("raw", "")) or str(rec.get("message", ""))
            findings.append(_make_finding(rule, rec, text[:200]))
    return findings


def _apply_static_rule(rule: DetectionRule, df: pd.DataFrame,
                       mask_cache: _MaskCache) -> list[dict]:
    try:
        re.compile(rule.condition, re.IGNORECASE)
    except re.error as exc:
        logger.warning("Invalid regex in rule '%s': %s", rule.rule_name, exc)
        return []

    # Vectorized match across the whole column in C — orders of magnitude faster
    # than iterating rows in Python.
    try:
        mask = mask_cache.mask(rule.condition)
    except Exception as exc:
        logger.warning("Static rule '%s' match failed: %s", rule.rule_name, exc)
        return []

    matched = df[mask.values]
    if matched.empty:
        return []

    # to_dict("records") on the capped slice avoids the slow per-row iterrows().
    findings = []
    for rec in matched.head(MAX_FINDINGS_PER_RULE).to_dict("records"):
        text = str(rec.get("raw", "")) or str(rec.get("message", ""))
        findings.append(_make_finding(rule, rec, text[:200]))
    return findings


def _apply_behavioral_rule(rule: DetectionRule, df: pd.DataFrame,
                           mask_cache: _MaskCache) -> list[dict]:
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
        logger.warning("Unknown behavioural condition key: %s", condition)
        return []

    return checker(rule, df, threshold, window, mask_cache)


def _apply_custom_rule(rule: DetectionRule, df: pd.DataFrame,
                       mask_cache: _MaskCache) -> list[dict]:
    """Generic no-code rule built from the Web UI: count rows whose text matches the
    admin-supplied pattern, aggregated by source IP / username / whole-file, and fire
    when the count meets the threshold.

    Reuses the shared _MaskCache (the pattern is scanned at most once) and the grouped
    threshold helper, so a custom rule is as fast as a built-in behavioural rule.
    """
    try:
        re.compile(rule.condition, re.IGNORECASE)
    except re.error as exc:
        logger.warning("Invalid regex in custom rule '%s': %s", rule.rule_name, exc)
        return []

    try:
        mask = mask_cache.mask(rule.condition)
    except Exception as exc:
        logger.warning("Custom rule '%s' match failed: %s", rule.rule_name, exc)
        return []

    matched = df[mask.values]
    if matched.empty:
        return []

    threshold = rule.default_threshold or 1
    group_by = (rule.group_by or "global").strip().lower()

    if group_by in ("source_ip", "username") and group_by in matched.columns:
        subset = matched[matched[group_by].notna()]
        if subset.empty:
            return []
        label = "IP" if group_by == "source_ip" else "User"
        return _grouped_over_threshold(
            subset, group_by, threshold,
            lambda key, cnt: f"{label} {key} matched '{rule.rule_name}' {cnt} time(s) (threshold={threshold}).",
            rule,
        )

    # Whole-file count.
    if len(matched) >= threshold:
        return [_make_finding(
            rule, matched.iloc[0],
            f"{len(matched)} event(s) matched '{rule.rule_name}' (threshold={threshold}).",
        )]
    return []


def _apply_prefixed_behavioral_rule(rule: DetectionRule, df: pd.DataFrame,
                                    mask_cache: _MaskCache) -> list[dict]:
    # Handles BEHAVIORAL:<key> (and the legacy DYNAMIC:<key>) static-stored behaviourals.
    key = rule.condition.split(":", 1)[1]
    threshold = rule.default_threshold or 3
    window = rule.time_window_seconds or 300

    if key == "unusual_hours":
        return _check_unusual_hours(rule, df, mask_cache)
    if key == "off_hours_access":
        return _check_off_hours_access(rule, df, mask_cache)
    if key == "login_after_failures":
        return _check_login_after_failures(rule, df, threshold, mask_cache)
    return []


# ── Helpers shared by the grouped behavioural checkers ─────────────────────────

def _grouped_over_threshold(subset, key_col, threshold, describe, rule):
    """Emit one finding per `key_col` value whose row-count meets the threshold.

    A representative row per key is taken with drop_duplicates (so we never re-scan
    the subset once per key), and findings are capped at MAX_FINDINGS_PER_RULE.
    """
    counts = subset.groupby(key_col).size()
    over = counts[counts >= threshold]
    if over.empty:
        return []
    reps = subset.drop_duplicates(key_col).set_index(key_col, drop=False)
    findings = []
    for key, cnt in over.items():
        findings.append(_make_finding(rule, reps.loc[key], describe(key, int(cnt))))
        if len(findings) >= MAX_FINDINGS_PER_RULE:
            break
    return findings


# ── Behavioural checkers ───────────────────────────────────────────────────────

def _check_brute_force(rule, df, threshold, window, mc) -> list[dict]:
    failed = df[mc.mask(_P_FAILED_LOGIN.pattern).values]
    failed = failed[failed["source_ip"].notna()]
    if failed.empty:
        return []
    return _grouped_over_threshold(
        failed, "source_ip", threshold,
        lambda ip, cnt: f"IP {ip} had {cnt} failed login(s) (threshold={threshold}).",
        rule,
    )


def _check_repeated_failed_logins(rule, df, threshold, window, mc) -> list[dict]:
    failed = df[mc.mask(_P_FAILED_LOGIN.pattern).values]
    failed = failed[failed["username"].notna()]
    if failed.empty:
        return []
    return _grouped_over_threshold(
        failed, "username", threshold,
        lambda user, cnt: f"User '{user}' had {cnt} failed logins (threshold={threshold}).",
        rule,
    )


def _check_rapid_logins(rule, df, threshold, window, mc) -> list[dict]:
    mask = mc.mask(_P_FAILED_LOGIN.pattern).values | mc.mask(_P_SUCCESS_LOGIN.pattern).values
    login_lines = df[mask]
    if len(login_lines) >= threshold:
        r = login_lines.iloc[0]
        return [_make_finding(rule, r, f"Total {len(login_lines)} login attempts detected (threshold={threshold}).")]
    return []


def _check_multi_user_failures(rule, df, threshold, window, mc) -> list[dict]:
    failed = df[mc.mask(_P_FAILED_LOGIN.pattern).values]
    failed = failed[failed["source_ip"].notna() & failed["username"].notna()]
    if failed.empty:
        return []
    distinct_users = failed.groupby("source_ip")["username"].nunique()
    over = distinct_users[distinct_users >= threshold]
    if over.empty:
        return []
    reps = failed.drop_duplicates("source_ip").set_index("source_ip", drop=False)
    findings = []
    for ip, n_users in over.items():
        findings.append(_make_finding(
            rule, reps.loc[ip],
            f"IP {ip} failed logins for {int(n_users)} different users (credential stuffing, threshold={threshold}).",
        ))
        if len(findings) >= MAX_FINDINGS_PER_RULE:
            break
    return findings


def _check_repeated_denials(rule, df, threshold, window, mc) -> list[dict]:
    denied = df[mc.mask(_P_ACCESS_DENIED.pattern).values]
    if denied.empty:
        return []
    denied = denied.assign(_ip=denied["source_ip"].fillna("unknown"))
    return _grouped_over_threshold(
        denied, "_ip", threshold,
        lambda ip, cnt: f"Source {ip} had {cnt} access denied events (threshold={threshold}).",
        rule,
    )


def _check_error_rate(rule, df, threshold, window, mc) -> list[dict]:
    errors = df[mc.mask(_P_ERROR.pattern).values]
    if len(errors) >= threshold:
        r = errors.iloc[0]
        return [_make_finding(rule, r, f"{len(errors)} error-level events detected (threshold={threshold}).")]
    return []


def _check_service_crash(rule, df, threshold, window, mc) -> list[dict]:
    crashes = df[mc.mask(_P_SERVICE_CRASH.pattern).values]
    if len(crashes) >= threshold:
        r = crashes.iloc[0]
        return [_make_finding(rule, r, f"{len(crashes)} service crash/restart events detected (threshold={threshold}).")]
    return []


def _check_rapid_actions(rule, df, threshold, window, mc) -> list[dict]:
    if len(df) >= threshold:
        r = df.iloc[0]
        return [_make_finding(rule, r, f"{len(df)} log entries detected — possible automated/rapid activity (threshold={threshold}).")]
    return []


def _check_mass_data(rule, df, threshold, window, mc) -> list[dict]:
    if len(df) >= threshold:
        r = df.iloc[0]
        return [_make_finding(rule, r, f"{len(df)} log entries indicate potential mass data access (threshold={threshold}).")]
    return []


def _check_resource_exhaustion(rule, df, threshold, window, mc) -> list[dict]:
    hits = df[mc.mask(_P_RESOURCE.pattern).values]
    if hits.empty:
        return []
    return [_make_finding(rule, hits.iloc[0], f"Resource exhaustion event: {hits.iloc[0]['raw'][:150]}")]


def _check_unexpected_shutdown(rule, df, threshold, window, mc) -> list[dict]:
    hits = df[mc.mask(_P_SHUTDOWN.pattern).values]
    if hits.empty:
        return []
    return [_make_finding(rule, hits.iloc[0], f"Unexpected shutdown/termination detected: {hits.iloc[0]['raw'][:150]}")]


def _check_config_change(rule, df, threshold, window, mc) -> list[dict]:
    hits = df[mc.mask(_P_CONFIG.pattern).values]
    if hits.empty:
        return []
    return [_make_finding(rule, hits.iloc[0], f"Configuration change detected: {hits.iloc[0]['raw'][:150]}")]


def _check_db_error(rule, df, threshold, window, mc) -> list[dict]:
    hits = df[mc.mask(_P_DB_ERROR.pattern).values]
    if len(hits) >= threshold:
        return [_make_finding(rule, hits.iloc[0], f"{len(hits)} database error events (threshold={threshold}).")]
    return []


def _check_unusual_hours(rule, df, mc) -> list[dict]:
    ts_col = df["timestamp"].dropna()
    if ts_col.empty:
        return []
    total = len(ts_col)
    outside = ts_col[(ts_col.dt.hour < 9) | (ts_col.dt.hour >= 17)]
    if total > 0 and (len(outside) / total) > 0.5:
        r = df.iloc[0]
        return [_make_finding(rule, r, f"{len(outside)}/{total} events ({len(outside)*100//total}%) outside business hours (09:00–17:00).")]
    return []


def _check_off_hours_access(rule, df, mc) -> list[dict]:
    success = df[mc.mask(_P_SUCCESS_LOGIN.pattern).values]
    ts_col = success["timestamp"].dropna()
    if ts_col.empty:
        return []
    night = ts_col[(ts_col.dt.hour >= 0) & (ts_col.dt.hour < 5)]
    if not night.empty:
        idx = night.index[0]
        r = success.loc[idx]
        return [_make_finding(rule, r, f"Successful login at {night.iloc[0].strftime('%H:%M:%S')} (off-hours: 00:00–05:00).")]
    return []


def _check_login_after_failures(rule, df, threshold, mc) -> list[dict]:
    # Select login-related rows with a username (vectorized), then walk per-user in
    # order over plain arrays. Iterating numpy arrays — instead of DataFrame.iterrows()
    # over the (potentially hundreds of thousands of) login rows — is the key speed-up.
    failed_mask = mc.mask(_P_FAILED_LOGIN.pattern).values
    success_mask = mc.mask(_P_SUCCESS_LOGIN.pattern).values
    sel = (failed_mask | success_mask) & df["username"].notna().values
    if not sel.any():
        return []

    cand = df[sel]
    is_fail = failed_mask[sel]          # a row matching "fail" is treated as a failure
    users = cand["username"].to_numpy()
    indices = cand.index.to_numpy()

    consecutive: dict = defaultdict(int)
    hits: list[tuple] = []  # (df_index, consecutive_fail_count)
    for user, fail, idx in zip(users, is_fail, indices):
        if fail:
            consecutive[user] += 1
        else:
            c = consecutive[user]
            if c >= threshold:
                hits.append((idx, c))
                if len(hits) >= MAX_FINDINGS_PER_RULE:
                    break
            consecutive[user] = 0

    findings = []
    for idx, c in hits:
        row = df.loc[idx]
        findings.append(_make_finding(
            rule, row,
            f"User '{row.get('username')}' logged in successfully after {c} consecutive failures.",
        ))
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
        # Concise per-rule action travels with the finding so the results panel / PDF
        # can show guidance even for new or admin-created rules with no code-dict entry.
        "recommended_action": getattr(rule, "recommended_action", None),
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
