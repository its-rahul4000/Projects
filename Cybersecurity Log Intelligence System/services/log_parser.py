import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ── Timestamp patterns ─────────────────────────────────────────────────────
_TS_PATTERNS = [
    (r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", "%Y-%m-%dT%H:%M:%S"),
    (r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S"),
    (r"\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}", "%d/%b/%Y:%H:%M:%S"),
    (r"\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}", "%b %d %H:%M:%S"),
    (r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}", "%m/%d/%Y %H:%M:%S"),
]

# ── Compiled regexes ────────────────────────────────────────────────────────
_RE_APACHE = re.compile(
    r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+\S+\s+(?P<user>\S+)\s+'
    r'\[(?P<ts>[^\]]+)\]\s+"(?P<method>\w+)\s+(?P<url>\S+)[^"]*"\s+'
    r'(?P<status>\d{3})\s+(?P<size>\S+)'
)
_RE_SYSLOG = re.compile(
    r'(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<host>\S+)\s+(?P<prog>[^\[:\s]+)(?:\[(?P<pid>\d+)\])?:\s+(?P<msg>.+)'
)
_RE_ISO_LOG = re.compile(
    r'(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
    r'(?P<level>CRITICAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE|FATAL|NOTICE)?\s*'
    r'(?P<msg>.+)'
)
_RE_CEF = re.compile(
    r'CEF:(?P<version>\d+)\|(?P<vendor>[^|]*)\|(?P<product>[^|]*)\|(?P<dev_version>[^|]*)\|'
    r'(?P<event_id>[^|]*)\|(?P<event_name>[^|]*)\|(?P<severity>[^|]*)\|(?P<ext>.*)'
)
_RE_IP = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
_RE_LEVEL = re.compile(r'\b(CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE|NOTICE)\b', re.I)
_RE_USER = re.compile(r'\b(?:user|username|user_id|account|login)\s*[=:]\s*["\']?(\w[\w@.\-]{1,50})', re.I)


def _parse_ts(raw_ts: str) -> Optional[datetime]:
    raw_ts = re.sub(r'[+-]\d{4}$', '', raw_ts).strip()
    for pattern, fmt in _TS_PATTERNS:
        m = re.search(pattern, raw_ts)
        if m:
            try:
                return datetime.strptime(m.group(), fmt.replace("T", " ").replace("T", "T"))
            except ValueError:
                pass
    # Try strptime directly with common formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%b/%Y:%H:%M:%S", "%b %d %H:%M:%S"):
        try:
            return datetime.strptime(raw_ts, fmt)
        except ValueError:
            continue
    return None


def _extract_ip(text: str) -> Optional[str]:
    m = _RE_IP.search(text)
    return m.group(1) if m else None


def _extract_level(text: str) -> str:
    m = _RE_LEVEL.search(text)
    if not m:
        return "INFO"
    lvl = m.group(1).upper()
    return "WARNING" if lvl == "WARN" else lvl


def _extract_username(text: str) -> Optional[str]:
    m = _RE_USER.search(text)
    return m.group(1) if m else None


def _parse_apache_line(line: str) -> Optional[dict]:
    m = _RE_APACHE.match(line.strip())
    if not m:
        return None
    ts = _parse_ts(m.group("ts"))
    return {
        "timestamp": ts,
        "level": _status_to_level(m.group("status")),
        "source_ip": m.group("ip"),
        "username": m.group("user") if m.group("user") != "-" else None,
        "method": m.group("method"),
        "url": m.group("url"),
        "status_code": int(m.group("status")),
        "message": f'{m.group("method")} {m.group("url")} {m.group("status")}',
        "format": "apache",
    }


def _parse_syslog_line(line: str) -> Optional[dict]:
    m = _RE_SYSLOG.match(line.strip())
    if not m:
        return None
    ts = _parse_ts(m.group("ts"))
    msg = m.group("msg")
    return {
        "timestamp": ts,
        "level": _extract_level(msg),
        "source_ip": _extract_ip(msg),
        "username": _extract_username(msg),
        "method": None,
        "url": None,
        "status_code": None,
        "message": msg,
        "format": "syslog",
    }


def _parse_cef_line(line: str) -> Optional[dict]:
    m = _RE_CEF.search(line.strip())
    if not m:
        return None
    ext_str = m.group("ext")
    ext = dict(re.findall(r'(\w+)=([^\s|]+)', ext_str))
    ts_raw = ext.get("rt") or ext.get("start") or ext.get("end")
    ts = _parse_ts(ts_raw) if ts_raw else None
    return {
        "timestamp": ts,
        "level": _cef_severity_to_level(m.group("severity")),
        "source_ip": ext.get("src") or ext.get("sourceAddress"),
        "username": ext.get("suser") or ext.get("sourceUserName"),
        "method": None,
        "url": ext.get("request"),
        "status_code": None,
        "message": m.group("event_name"),
        "format": "cef",
    }


def _parse_generic_line(line: str) -> dict:
    m = _RE_ISO_LOG.match(line.strip())
    if m:
        ts = _parse_ts(m.group("ts"))
        lvl = m.group("level") or _extract_level(line)
        msg = m.group("msg")
    else:
        ts = None
        lvl = _extract_level(line)
        msg = line.strip()

    return {
        "timestamp": ts,
        "level": lvl.upper(),
        "source_ip": _extract_ip(line),
        "username": _extract_username(line),
        "method": None,
        "url": None,
        "status_code": None,
        "message": msg,
        "format": "generic",
    }


def _status_to_level(status: str) -> str:
    code = int(status)
    if code >= 500:
        return "ERROR"
    if code >= 400:
        return "WARNING"
    return "INFO"


def _cef_severity_to_level(sev: str) -> str:
    try:
        s = int(sev)
        if s >= 8:
            return "CRITICAL"
        if s >= 6:
            return "ERROR"
        if s >= 4:
            return "WARNING"
        return "INFO"
    except ValueError:
        return _extract_level(sev)


def _detect_format(lines: list[str]) -> str:
    sample = "\n".join(lines[:20])
    if "CEF:" in sample:
        return "cef"
    if _RE_APACHE.search(sample):
        return "apache"
    if _RE_SYSLOG.search(sample):
        return "syslog"
    return "generic"


_PARSERS = {
    "apache": _parse_apache_line,
    "syslog": _parse_syslog_line,
    "cef": _parse_cef_line,
    "generic": _parse_generic_line,
}


def parse_log_file(file_path: str, progress_cb=None) -> pd.DataFrame:
    """Parse a log file into a normalised DataFrame.

    Parsing is single-process (it is already fast — a few seconds even for hundreds of
    thousands of lines, and vectorized type-coercion handles timestamps/status codes).
    The CPU-heavy work that benefits from multiple cores is rule evaluation, which the
    analysis worker parallelizes. progress_cb, if given, is called with
    (fraction in [0,1], entries-so-far).
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        logger.error("Cannot read log file %s: %s", file_path, exc)
        return pd.DataFrame()

    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return pd.DataFrame()

    fmt = _detect_format(non_empty)
    parser = _PARSERS[fmt]

    total_lines = len(lines)
    report_every = max(total_lines // 200, 1)  # ~200 progress updates → smooth counter/bar
    rows = []
    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        row = parser(line)
        if row is None:
            row = _parse_generic_line(line)
        row["raw"] = line.rstrip()
        row["line_num"] = i
        rows.append(row)
        if progress_cb and (i % report_every == 0):
            progress_cb(i / total_lines, len(rows))

    if progress_cb:
        progress_cb(1.0, len(rows))

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["status_code"] = pd.to_numeric(df["status_code"], errors="coerce").astype("Int64")
    return df


def merge_dataframes(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Concatenate two log DataFrames and reset line numbers."""
    if existing is None or existing.empty:
        return new
    if new is None or new.empty:
        return existing
    merged = pd.concat([existing, new], ignore_index=True)
    merged["line_num"] = range(1, len(merged) + 1)
    return merged
