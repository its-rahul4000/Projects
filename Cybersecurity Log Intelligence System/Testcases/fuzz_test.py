"""Fuzz-test the log-ingestion + threat-detection pipeline.

OFFLINE & SELF-CONTAINED — safe to run on a firewalled machine
--------------------------------------------------------------
This script makes NO network calls, downloads nothing, and depends on NO
third-party fuzzing library (no hypothesis / atheris). It uses only the Python
standard library plus the project's own modules and the packages already in
requirements.txt (pandas, pyyaml). The only file it touches on disk is one
scratch file under the project's ``temp/`` folder, which it deletes when done.

What it fuzzes
--------------
The untrusted-input surface of the app — everything an uploaded log file flows
through:

  1. services.log_parser.parse_log_file   (full parse of random/garbage files,
     including raw non-UTF-8 bytes)
  2. The low-level parsers / extractors    (_parse_ts, _detect_format,
     _extract_ip, _extract_username, and the per-format line parsers)
  3. services.threat_engine.run_analysis   (run against both the REAL rule set
     and randomly-generated rules, including deliberately broken regexes,
     odd group-by keys, and negative/None thresholds)

The contract being checked: the pipeline must NEVER raise an unhandled
exception on hostile input — it should degrade gracefully and always return a
well-formed result. Any crash is reported with the offending input and a full
traceback so it is reproducible.

Bounded runtime
---------------
Input sizes (line count, line length, blob size, random-regex complexity) are
capped so a single iteration can't blow up memory or trigger pathological
regex backtracking. Runs are reproducible: a fixed RNG seed is used unless you
pass your own.

Usage
-----
    conda run -n cybersec python "Testcases/fuzz_test.py"
    conda run -n cybersec python "Testcases/fuzz_test.py" <iterations> <seed>

Exit code is 0 when no crashes are found, 1 otherwise (CI-friendly).
"""

import os
import sys
import glob
import time
import random
import string
import traceback
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.abspath(__file__))   # Testcases/
PROJ = os.path.dirname(ROOT)
sys.path.insert(0, PROJ)

import yaml  # noqa: E402  (from requirements.txt)
from services.log_parser import (  # noqa: E402
    parse_log_file,
    _detect_format,
    _parse_ts,
    _extract_ip,
    _extract_username,
    _parse_apache_line,
    _parse_syslog_line,
    _parse_cef_line,
    _parse_generic_line,
)
from services.threat_engine import run_analysis  # noqa: E402

# ── Character pools used to build hostile inputs ─────────────────────────────
_PRINTABLE = string.ascii_letters + string.digits + string.punctuation + " \t"
# Valid Unicode scalars only (no surrogates) so text writes always encode.
_WEIRD = "".join(chr(c) for c in range(0, 32)) + "\x7f\x85\xa0—…✓€中𝔘"
_SPECIALS = [
    "../", "..\\", "%2e%2e/", "<script>", "</script>", "' OR 1=1--",
    "${jndi:ldap://127.0.0.1/a}", "\x00", "\\x", "%n", "%s", "|", ";", "&&",
    "`", "*)(uid=*", "‮", "{}", "[]", "()", "=" * 40, "A" * 200,
]

# Known behavioural condition keys + prefixed forms, to exercise the engine's
# dispatch tables alongside random garbage conditions.
_BEHAV_KEYS = [
    "brute_force", "repeated_failed_logins", "rapid_login_attempts",
    "multi_user_failures", "repeated_access_denials", "error_rate_spike",
    "service_crash_loop", "rapid_sequential_actions", "mass_data_access",
    "resource_exhaustion", "unexpected_shutdown", "configuration_change",
    "database_error_spike",
]
_PREFIXED = ["BEHAVIORAL:unusual_hours", "BEHAVIORAL:off_hours_access",
             "BEHAVIORAL:login_after_failures", "BEHAVIORAL:" + "x" * 5,
             "DYNAMIC:nonsense"]


# ── Random building blocks ───────────────────────────────────────────────────
def _rand_str(rng, n, weird_bias=0.3):
    out = []
    for _ in range(n):
        r = rng.random()
        if r < weird_bias:
            out.append(rng.choice(_WEIRD))
        elif r < weird_bias + 0.1:
            out.append(rng.choice(_SPECIALS))
        else:
            out.append(rng.choice(_PRINTABLE))
    return "".join(out)


def _rand_ip(rng):
    pick = rng.random()
    if pick < 0.2:                       # malformed octets
        return ".".join(str(rng.randint(-5, 999)) for _ in range(rng.randint(1, 5)))
    return ".".join(str(rng.randint(0, 255)) for _ in range(4))


def _rand_ts(rng):
    fmts = [
        lambda: f"2024-{rng.randint(0, 20):02d}-{rng.randint(0, 40):02d} "
                f"{rng.randint(0, 30):02d}:{rng.randint(0, 99):02d}:{rng.randint(0, 99):02d}",
        lambda: f"{rng.randint(1, 40)}/Foo/{rng.randint(0, 9999)}:99:99:99",
        lambda: f"Xxx {rng.randint(0, 99)} {rng.randint(0, 99)}:{rng.randint(0, 99)}:00",
        lambda: _rand_str(rng, rng.randint(0, 25)),
        lambda: "",
    ]
    return rng.choice(fmts)()


def _structured_line(rng):
    """A line that loosely mimics a real format but with random/missing/oversized
    fields, to stress the structured parsers' group extraction."""
    kind = rng.choice(["apache", "syslog", "cef", "iso", "kv"])
    tok = lambda: _rand_str(rng, rng.randint(0, 12), weird_bias=0.15)
    if kind == "apache":
        return (f'{_rand_ip(rng)} - {tok()} [{_rand_ts(rng)}] '
                f'"{tok()} /{tok()} HTTP/1.1" {rng.randint(-1, 999)} {tok()}')
    if kind == "syslog":
        return (f"Jan {rng.randint(0, 99)} {rng.randint(0, 99)}:00:00 host{tok()} "
                f"{tok()}[{rng.randint(0, 99999)}]: {_rand_str(rng, rng.randint(0, 60))}")
    if kind == "cef":
        bars = "|".join(tok() for _ in range(rng.randint(0, 9)))
        return f"CEF:{rng.randint(0, 9)}|{bars} src={_rand_ip(rng)} suser={tok()}"
    if kind == "iso":
        lvl = rng.choice(["INFO", "WARN", "ERROR", "CRITICAL", "", tok()])
        return (f"{_rand_ts(rng)} {lvl} {_rand_str(rng, rng.randint(0, 80))} "
                f"user={tok()} client={_rand_ip(rng)}")
    return f"user={tok()} ip={_rand_ip(rng)} {_rand_str(rng, rng.randint(0, 40))}"


def _make_line(rng, seeds):
    r = rng.random()
    if r < 0.25 and seeds:
        return _mutate(rng, rng.choice(seeds))
    if r < 0.55:
        return _structured_line(rng)
    if r < 0.7:
        return _rand_str(rng, rng.randint(0, 2000))      # occasional long line
    return _rand_str(rng, rng.randint(0, 120))


def _mutate(rng, line):
    """Byte/char-level mutation of a seed line."""
    s = list(line)
    for _ in range(rng.randint(1, 6)):
        if not s:
            s = list(_rand_str(rng, rng.randint(1, 20)))
        op = rng.randint(0, 4)
        i = rng.randrange(len(s))
        if op == 0:
            s[i] = rng.choice(_PRINTABLE + _WEIRD)
        elif op == 1:
            s.insert(i, rng.choice(_SPECIALS))
        elif op == 2:
            del s[i]
        elif op == 3:
            s[i:i] = s[i] * rng.randint(2, 50)           # duplicate run
        else:
            s = s[:i]                                    # truncate
    return "".join(s)


def _build_input(rng, seeds):
    """Return (content, is_bytes). Sometimes raw non-UTF-8 bytes to exercise the
    parser's errors='replace' decode path."""
    if rng.random() < 0.15:
        return bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 8192))), True
    nlines = rng.randint(0, 200)
    return "\n".join(_make_line(rng, seeds) for _ in range(nlines)), False


# ── Random rules (fuzz the rule-evaluation engine itself) ────────────────────
def _rand_regex(rng):
    """A SHORT pattern (no nested quantifiers) — kept simple on purpose so the
    fuzzer can't induce catastrophic backtracking against itself."""
    parts = []
    for _ in range(rng.randint(1, 4)):
        parts.append(rng.choice([
            rng.choice(_PRINTABLE), r"\d", r"\w", r"\s", ".", "[a-z]",
            "(?i)", "|", rng.choice(_SPECIALS)[:3],
            rng.choice(["", "+", "*", "?"]),
        ]))
    return "".join(parts)


def _random_rules(rng):
    rules = []
    for _ in range(rng.randint(1, 8)):
        rtype = rng.choice(["static", "behavioral", "custom", "dynamic"])
        cond_pick = rng.random()
        if cond_pick < 0.3:
            cond = rng.choice(_BEHAV_KEYS)
        elif cond_pick < 0.5:
            cond = rng.choice(_PREFIXED)
        else:
            cond = _rand_regex(rng)
        rules.append(SimpleNamespace(
            rule_name=f"fuzz_{rng.randint(0, 9999)}",
            rule_type=rtype,
            condition=cond,
            severity=rng.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW", "weird", ""]),
            default_threshold=rng.choice([None, 0, -3, 1, 5, 99999]),
            time_window_seconds=rng.choice([None, 0, -1, 60, 999999]),
            group_by=rng.choice(["source_ip", "username", "global", "nope", None]),
            recommended_action=None,
            is_enabled=True,
            is_propagated=True,
        ))
    return rules


# ── Real rule set + seed corpus ──────────────────────────────────────────────
def _load_real_rules():
    with open(os.path.join(PROJ, "config", "detection_rules.yaml"), encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    rules = []
    for section in ("static_rules", "behavioral_rules", "custom_rules"):
        for r in cfg.get(section, []):
            rules.append(SimpleNamespace(
                rule_name=r["rule_name"], rule_type=r["rule_type"],
                condition=r["condition"], severity=r["severity"],
                default_threshold=r.get("default_threshold"),
                time_window_seconds=r.get("time_window_seconds"),
                group_by=r.get("group_by", "global"),
                recommended_action=r.get("recommended_action"),
                is_enabled=True, is_propagated=True,
            ))
    return rules


def _load_seed_corpus(rng):
    """A few representative valid lines + a sample of the local .log testcases (if
    present). Purely local file reads — no network."""
    seeds = [
        '192.168.1.42 - alice [15/Jan/2024:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1024',
        "Jan 15 10:00:00 web01 sshd[2451]: Failed password for root from 203.0.113.22 port 52000 ssh2",
        "CEF:0|Vendor|Product|1.0|100|Login Failed|5|src=10.0.0.1 suser=bob",
        "2024-01-15 10:01:01 WARN [api] GET /search?q=test 200 user=carol client=192.168.1.20",
    ]
    for path in glob.glob(os.path.join(ROOT, "*.log")):
        try:
            if os.path.getsize(path) > 1_000_000:        # skip the big combined file
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = [ln.rstrip("\n") for ln in fh if ln.strip()]
            seeds += rng.sample(lines, min(3, len(lines)))
        except OSError:
            continue
    return seeds


# ── Fuzz phases ───────────────────────────────────────────────────────────────
def _record(crashes, label, ident, payload, limit=15):
    if len(crashes) < limit:
        crashes.append((label, ident, repr(payload)[:300], traceback.format_exc()))


def fuzz_units(iterations, seed):
    """Hammer the low-level parsers/extractors with raw random strings."""
    rng = random.Random(seed ^ 0x5BD1E995)
    crashes = []
    for i in range(iterations):
        s = _rand_str(rng, rng.randint(0, 300))
        try:
            _parse_ts(s)
            _extract_ip(s)
            _extract_username(s)
            _parse_apache_line(s)
            _parse_syslog_line(s)
            _parse_cef_line(s)
            r = _parse_generic_line(s)        # the fallback must never return None
            assert r is not None and "message" in r
            _detect_format([s, s])
        except Exception:
            _record(crashes, "unit", i, s)
    return crashes


def fuzz_pipeline(iterations, seed):
    """End-to-end: write a random file, parse it, then analyse with real + random rules."""
    rng = random.Random(seed)
    crashes = []
    real_rules = _load_real_rules()
    seeds = _load_seed_corpus(rng)
    tmp = os.path.join(PROJ, "temp", "_fuzz_input.log")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)

    try:
        for i in range(iterations):
            content, is_bytes = _build_input(rng, seeds)
            try:
                if is_bytes:
                    with open(tmp, "wb") as fh:
                        fh.write(content)
                else:
                    with open(tmp, "w", encoding="utf-8", newline="") as fh:
                        fh.write(content)

                df = parse_log_file(tmp)
                # Parser contract: always a DataFrame with the normalised columns.
                assert df is not None
                if not df.empty:
                    for col in ("raw", "timestamp", "source_ip", "username"):
                        assert col in df.columns, f"missing column {col}"

                findings = run_analysis(df, real_rules)
                assert isinstance(findings, list)
                if rng.random() < 0.5:
                    assert isinstance(run_analysis(df, _random_rules(rng)), list)
            except Exception:
                _record(crashes, "pipeline", i, content)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return crashes


def main():
    pipe_iters = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1337
    unit_iters = pipe_iters * 10

    print(f"Fuzzing with seed={seed}  (pass a different seed as 2nd arg to vary)")
    print(f"  unit phase     : {unit_iters} iterations")
    print(f"  pipeline phase : {pipe_iters} iterations")
    print("-" * 60)

    t0 = time.time()
    crashes = fuzz_units(unit_iters, seed)
    crashes += fuzz_pipeline(pipe_iters, seed)
    elapsed = time.time() - t0

    print(f"Completed {unit_iters + pipe_iters} iterations in {elapsed:.1f}s")
    if not crashes:
        print("RESULT: PASS — no crashes; the pipeline survived all hostile input.")
        sys.exit(0)

    print(f"RESULT: FAIL — {len(crashes)} crash(es) found (showing up to 15):\n")
    for label, ident, payload, tb in crashes:
        print(f"[{label} #{ident}] input={payload}")
        print(tb)
        print("-" * 60)
    print(f"Reproduce with the same seed: python fuzz_test.py {pipe_iters} {seed}")
    sys.exit(1)


if __name__ == "__main__":
    main()
