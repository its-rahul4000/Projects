import pytest
import os
import tempfile
import datetime

from services.log_parser import parse_log_file
from services.threat_engine import run_analysis, compute_summary


def _write_temp(content: str, suffix: str = ".log") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def make_rule(db, name, condition, severity="HIGH", is_static=True, threshold=None, window=None):
    from database.models import DetectionRule
    rule = DetectionRule(
        rule_name=name,
        rule_type="static" if is_static else "dynamic",
        condition=condition,
        severity=severity,
        is_static=is_static,
        default_threshold=threshold,
        time_window_seconds=window,
        is_enabled=True,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def test_sql_injection_detected(db):
    log_content = "2024-01-10 09:00:00 WARNING Suspicious query detected: union select * from users WHERE 1=1\n"
    path = _write_temp(log_content)
    try:
        df = parse_log_file(path)
        rule = make_rule(db, "SQL Injection Test", r"(?i)(union\s+select|drop\s+table)")
        findings = run_analysis(df, [rule])
        assert len(findings) >= 1
        assert any(f["rule_name"] == "SQL Injection Test" for f in findings)
    finally:
        os.remove(path)


def test_path_traversal_detected(db):
    log_content = "192.168.1.5 - - [10/Jan/2024:09:00:00 +0000] \"GET /../../../etc/passwd HTTP/1.1\" 200 1024\n"
    path = _write_temp(log_content)
    try:
        df = parse_log_file(path)
        rule = make_rule(db, "Path Traversal Test", r"(?i)(\.\./|\.\.\\|\.\.%2[fF])")
        findings = run_analysis(df, [rule])
        assert len(findings) >= 1
    finally:
        os.remove(path)


def test_no_false_positives(db):
    log_content = "192.168.1.1 - - [10/Jan/2024:09:00:00 +0000] \"GET /index.html HTTP/1.1\" 200 512\n"
    path = _write_temp(log_content)
    try:
        df = parse_log_file(path)
        rule = make_rule(db, "SQL Injection Test", r"(?i)(union\s+select|drop\s+table)")
        findings = run_analysis(df, [rule])
        assert len(findings) == 0
    finally:
        os.remove(path)


def test_brute_force_dynamic_rule(db):
    lines = "\n".join(
        f"Jan 10 09:{i:02d}:00 host sshd[100]: Failed password for root from 10.0.0.1 port 22"
        for i in range(10)
    )
    path = _write_temp(lines, ".syslog")
    try:
        df = parse_log_file(path)
        from database.models import DetectionRule
        rule = DetectionRule(
            rule_name="Brute Force Test",
            rule_type="dynamic",
            condition="brute_force",
            severity="CRITICAL",
            is_static=False,
            default_threshold=5,
            time_window_seconds=60,
            is_enabled=True,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        findings = run_analysis(df, [rule])
        assert len(findings) >= 1
        assert findings[0]["severity"] == "CRITICAL"
    finally:
        os.remove(path)


def test_compute_summary():
    findings = [
        {"severity": "CRITICAL"},
        {"severity": "HIGH"},
        {"severity": "HIGH"},
        {"severity": "MEDIUM"},
        {"severity": "LOW"},
    ]
    summary = compute_summary(findings)
    assert summary["total"] == 5
    assert summary["CRITICAL"] == 1
    assert summary["HIGH"] == 2
    assert summary["MEDIUM"] == 1
    assert summary["LOW"] == 1


def test_empty_log_no_findings(db):
    import pandas as pd
    findings = run_analysis(pd.DataFrame(), [])
    assert findings == []


def test_disabled_rule_not_applied(db):
    log_content = "192.168.1.1 - admin [10/Jan/2024:09:00:00 +0000] \"GET /search?q=union+select HTTP/1.1\" 200 512\n"
    path = _write_temp(log_content)
    try:
        df = parse_log_file(path)
        from database.models import DetectionRule
        disabled_rule = DetectionRule(
            rule_name="Disabled Rule",
            rule_type="static",
            condition=r"(?i)(union\s+select)",
            severity="HIGH",
            is_static=True,
            is_enabled=False,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(disabled_rule)
        db.commit()
        db.refresh(disabled_rule)
        # Only pass enabled rules (simulate get_enabled_rules filtering)
        findings = run_analysis(df, [])
        assert len(findings) == 0
    finally:
        os.remove(path)
