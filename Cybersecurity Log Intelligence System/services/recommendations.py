"""
Threat remediation recommendations for each detection rule.
Used by the results page panel and PDF report.
"""

_RULE_ACTIONS: dict[str, dict] = {
    "SQL Injection Attempt": {
        "why": "SQL injection allows attackers to manipulate database queries to read, modify, or delete data they shouldn't access.",
        "impact": "Full database compromise, data exfiltration, authentication bypass, data destruction.",
        "actions": [
            "Replace all dynamic SQL with parameterized queries or prepared statements",
            "Deploy / update Web Application Firewall (WAF) with SQL injection ruleset",
            "Audit and revoke excessive database user privileges (principle of least privilege)",
            "Review application logs for successful injection — check for data exfiltration",
            "Apply input validation and allowlisting on all user-supplied fields",
            "Patch or upgrade the affected application framework to the latest version",
        ],
    },
    "Command Injection": {
        "why": "Command injection lets an attacker run arbitrary OS commands with the privileges of the application server.",
        "impact": "Full system compromise, data theft, lateral movement, ransomware deployment.",
        "actions": [
            "Isolate the affected server from the network immediately",
            "Never pass user input directly to shell commands — use allowlists",
            "Enforce least-privilege for web server and application accounts",
            "Review process execution logs for unauthorized commands run",
            "Apply OS and application security patches",
            "Implement runtime application self-protection (RASP) or WAF rule",
        ],
    },
    "XSS Attempt": {
        "why": "XSS allows attackers to inject malicious scripts into pages viewed by other users, enabling session hijacking.",
        "impact": "Session token theft, credential harvesting, malware distribution, defacement.",
        "actions": [
            "Encode all output rendered in the browser (HTML, JS, URL, CSS contexts)",
            "Implement a strict Content-Security-Policy (CSP) header",
            "Use HttpOnly and Secure flags on session cookies",
            "Deploy WAF with XSS signature rules",
            "Validate and sanitize all user input at the server side",
        ],
    },
    "Path Traversal Attempt": {
        "why": "Path traversal lets attackers read files outside the intended directory, including system credentials.",
        "impact": "Disclosure of /etc/passwd, private keys, config files, and application source code.",
        "actions": [
            "Validate file paths with a strict allowlist of permitted directories",
            "Resolve symlinks and canonicalize paths before access",
            "Apply chroot jail or container file system isolation to the application",
            "Ensure web server cannot serve files outside the web root",
            "Deploy WAF rules to block traversal sequences (../, %2e%2e, etc.)",
        ],
    },
    "Directory Scanning": {
        "why": "Directory scanning reveals hidden admin panels, backup files, and configuration files useful for further attacks.",
        "impact": "Intelligence gathering enabling targeted exploitation of discovered endpoints.",
        "actions": [
            "Remove or restrict access to sensitive directories (/admin, /backup, /.git)",
            "Return generic 404 for all unlisted paths to avoid revealing directory structure",
            "Block or rate-limit the scanning source IP at the firewall/WAF",
            "Enable access logging and alerting for sensitive path requests",
            "Conduct a security audit of exposed endpoints",
        ],
    },
    "Abnormal HTTP Methods": {
        "why": "Non-standard HTTP methods (TRACE, CONNECT, WebDAV) are used in reconnaissance and can expose server information.",
        "impact": "Cross-Site Tracing (XST) attacks, proxy bypasses, unauthorized file operations.",
        "actions": [
            "Disable TRACE, CONNECT, and WebDAV methods in the web server config",
            "Whitelist only GET, POST (and PUT/DELETE if needed) at the WAF",
            "Investigate the source IP for additional reconnaissance activity",
            "Review server response headers for information disclosure",
        ],
    },
    "Dormant Account Activity": {
        "why": "Dormant accounts are often compromised via credential dumps and used for stealthy long-term access.",
        "impact": "Persistent unauthorized access, data theft, insider threat vector.",
        "actions": [
            "Immediately disable the dormant account and investigate all recent activity",
            "Force a password reset and enable MFA before allowing re-access",
            "Review access logs for data accessed during the dormant period",
            "Implement an automated account deactivation policy for accounts idle >90 days",
            "Conduct a full credentials audit against known breach databases",
        ],
    },
    "Concurrent Sessions": {
        "why": "Multiple simultaneous sessions from different locations suggest credential sharing or active session hijacking.",
        "impact": "Unauthorized data access, privilege abuse, compliance violations.",
        "actions": [
            "Enforce single-session policy — invalidate older sessions on new login",
            "Alert users and admins on concurrent session detection",
            "Investigate the secondary session's source IP and activity",
            "Enable MFA to prevent credential-based concurrent access",
            "Review session management code for fixation vulnerabilities",
        ],
    },
    "Geographic Anomaly": {
        "why": "A login from an unusual country or impossible travel distance suggests credential compromise.",
        "impact": "Account takeover, data exfiltration, fraudulent actions performed as the victim.",
        "actions": [
            "Temporarily lock the account and notify the legitimate user",
            "Enable MFA with device enrollment to prevent account takeover",
            "Review all actions taken during the anomalous session",
            "Implement geo-fencing policies blocking logins from unexpected regions",
            "Check for any data downloads or privilege changes made during that session",
        ],
    },
    "Unusual Working Hours": {
        "why": "Consistent activity outside business hours (09:00–17:00) may indicate automated exfiltration or an insider threat.",
        "impact": "Undetected data theft, policy violations, compromised accounts used when monitoring is low.",
        "actions": [
            "Review the specific actions taken during the flagged off-hours period",
            "Implement time-based access policies with approval required for off-hours access",
            "Set up automated alerts for off-hours logins from this account",
            "Verify with the employee whether activity was intentional",
            "Enable enhanced logging for this account for 30 days",
        ],
    },
    "Off-Hours Access": {
        "why": "Successful logins between midnight and 05:00 are unusual and may indicate a compromised account.",
        "impact": "Stealthy data theft, system reconfiguration, backdoor installation while staff are absent.",
        "actions": [
            "Verify with the account owner whether the 00:00–05:00 login was intentional",
            "Review all actions performed during the off-hours session",
            "Require MFA and manager approval for access outside business hours",
            "Consider temporary account lock pending investigation",
            "Increase audit logging for this account",
        ],
    },
    "Unauthorized Access Attempt": {
        "why": "HTTP 403/401 errors indicate attempts to access resources the requester is not permitted to see.",
        "impact": "Access control bypass if misconfigured, information exposure, brute-force of ACL gaps.",
        "actions": [
            "Review the targeted resource's access control configuration",
            "Block the source IP if repeated 403/401 responses are systematic",
            "Ensure principle of least privilege is enforced on the protected resource",
            "Review authentication/authorization middleware for logic flaws",
            "Enable rate limiting to prevent systematic ACL probing",
        ],
    },
    "Privilege Escalation": {
        "why": "Privilege escalation attacks gain higher system access (root/admin) from a lower-privileged starting point.",
        "impact": "Full system takeover, data destruction, ransomware deployment, persistent backdoors.",
        "actions": [
            "Immediately isolate the affected system from the network",
            "Revoke the elevated privileges and audit the full activity log",
            "Patch the exploited vulnerability (SUID binaries, kernel exploits, misconfigs)",
            "Enforce strict sudoers policy — require explicit per-command approvals",
            "Deploy Privileged Access Management (PAM) with session recording",
            "Conduct forensic investigation of all commands run as root/admin",
        ],
    },
    "Sensitive Resource Access": {
        "why": "Access to /etc/passwd, SSH keys, and credential files enables lateral movement and persistent access.",
        "impact": "Credential theft, full system compromise, persistent backdoor establishment.",
        "actions": [
            "Restrict read permissions on sensitive files to root/application owner only",
            "Alert and review every access to /etc/shadow, .ssh/, *.pem, *.key",
            "Rotate any credentials that may have been viewed",
            "Implement file integrity monitoring (FIM) on sensitive paths",
            "Review whether the accessing process/user is authorized",
        ],
    },
    "API Key Misuse": {
        "why": "Invalid or expired API keys indicate credential testing, key rotation failures, or active compromise.",
        "impact": "Unauthorized API access, service abuse, data exfiltration via API endpoints.",
        "actions": [
            "Immediately rotate the suspected compromised API key",
            "Review all API calls made with the flagged key for unauthorized actions",
            "Implement API key scoping — restrict keys to minimum required permissions",
            "Enable rate limiting and anomaly detection on API gateway",
            "Consider short-lived tokens (e.g., OAuth2) instead of static API keys",
        ],
    },
    "Session Hijacking Pattern": {
        "why": "Session fixation, CSRF, and session token mismatches suggest an active attempt to take over an authenticated session.",
        "impact": "Complete account takeover without needing credentials.",
        "actions": [
            "Invalidate all active sessions for the affected user immediately",
            "Enforce HTTPS across the entire application (HSTS header)",
            "Use SameSite=Strict and Secure attributes on all cookies",
            "Implement CSRF tokens on all state-changing requests",
            "Regenerate session IDs after authentication and privilege changes",
        ],
    },
    "Account Lockout Event": {
        "why": "Account lockouts triggered by failed attempts signal brute-force or credential stuffing attacks.",
        "impact": "Denial of service to the legitimate user; successful login if the correct password is eventually found.",
        "actions": [
            "Investigate the source IP(s) triggering the lockout",
            "Block offending IPs at the firewall if automated attack confirmed",
            "Notify the affected user and confirm the account is secure",
            "Enable MFA to make brute-force attacks ineffective",
            "Review lockout threshold settings — too-high thresholds increase risk",
        ],
    },
    "Successful Login After Failures": {
        "why": "A successful login following several failures may indicate a successful brute-force or password-spray attack.",
        "impact": "Account compromise — attacker now has authenticated access.",
        "actions": [
            "Verify with the account owner that they performed the login",
            "Review all actions taken in the session immediately following the failed attempts",
            "Force a password reset if compromise is suspected",
            "Enable MFA to prevent future credential-based attacks",
            "Block the source IP if the failures came from an unusual location",
        ],
    },
    "Brute Force Attack": {
        "why": "Repeated password guessing from a single IP attempts to crack account credentials by exhaustion.",
        "impact": "Account compromise if successful; account lockout causing denial of service.",
        "actions": [
            "Block the attacking IP at the firewall or WAF immediately",
            "Enable account lockout after 5 failed attempts",
            "Deploy fail2ban or equivalent automated IP banning",
            "Require MFA on all accounts to render brute-force attacks ineffective",
            "Review whether any attempts succeeded — check successful logins from the same IP",
            "Consider CAPTCHA on the login page for repeated failures",
        ],
    },
    "Repeated Failed Logins": {
        "why": "Multiple failed logins for the same username indicate targeted password-guessing of that specific account.",
        "impact": "Account compromise if threshold not enforced; lockout causing DoS.",
        "actions": [
            "Enforce account lockout after the configured failure threshold",
            "Notify the account owner of the failed login attempts",
            "Require MFA on the targeted account",
            "Investigate whether the username was obtained via a data breach",
            "Block the offending source IP(s)",
        ],
    },
    "Rapid Login Attempts": {
        "why": "High-velocity login attempts indicate an automated attack tool is attempting to compromise accounts.",
        "impact": "Account compromise, denial of service, credential stuffing.",
        "actions": [
            "Enable rate limiting on the login endpoint (e.g., 10 attempts per minute per IP)",
            "Deploy CAPTCHA to stop automated tools",
            "Block the source IP range immediately",
            "Enable MFA platform-wide",
            "Review whether any attempts resulted in successful authentication",
        ],
    },
    "Multiple User Failures": {
        "why": "Failed logins for many different usernames from one IP is a credential stuffing attack using a breached database.",
        "impact": "Mass account compromise if any credential pair matches.",
        "actions": [
            "Immediately block the source IP at the perimeter firewall",
            "Check all accounts targeted for any successful login from that IP",
            "Force password resets on all accounts that had failed attempts",
            "Cross-reference your user base against publicly known breach databases (HaveIBeenPwned)",
            "Enforce MFA platform-wide",
            "Enable bot detection (device fingerprinting, behavioral analytics)",
        ],
    },
    "Repeated Access Denials": {
        "why": "Systematic 403/401 responses from one source suggest probing for accessible resources or ACL bypass attempts.",
        "impact": "Discovery of misconfigured access controls, prelude to exploitation.",
        "actions": [
            "Block the probing IP at WAF or firewall",
            "Audit the targeted resources' access control settings",
            "Verify no resources are inadvertently accessible to the probing user/IP",
            "Enable enhanced alerting for repeated denial events",
        ],
    },
    "Error Rate Spike": {
        "why": "A sudden surge in application errors may indicate an attack, a bug, or abnormal input being processed.",
        "impact": "System instability, potential information disclosure via error messages, application unavailability.",
        "actions": [
            "Investigate the root cause: application bug, unexpected input, or attack?",
            "Disable detailed error messages / stack traces in production",
            "Review error logs for patterns pointing to injection or fuzzing",
            "Scale up or restart affected services if availability is impacted",
            "Set up automated alerting for error rate thresholds",
        ],
    },
    "Service Crash Loop": {
        "why": "Repeated crash-restart cycles may be caused by a vulnerability exploit, resource exhaustion, or a malicious payload.",
        "impact": "Service unavailability (DoS), potential code execution if exploit is triggering the crash.",
        "actions": [
            "Investigate crash dumps/core dumps for exploitation evidence",
            "Apply available security patches for the affected service",
            "Isolate the service from the network while investigating",
            "Review recent deployments and configuration changes",
            "Enable resource limits and circuit breaker patterns",
        ],
    },
    "Rapid Sequential Actions": {
        "why": "An unusually high action rate from a single account suggests bot activity, automated exfiltration, or a compromised session.",
        "impact": "Mass data access, API abuse, resource exhaustion, policy violations.",
        "actions": [
            "Implement API/action rate limiting per user account",
            "Temporarily suspend the account and investigate the activity",
            "Deploy behavioral analytics to baseline normal user activity rates",
            "Review what data was accessed during the high-rate period",
            "Require re-authentication if unusual activity is detected",
        ],
    },
    "Mass Data Access": {
        "why": "Accessing an unusually large number of records in a short period is a primary indicator of data exfiltration.",
        "impact": "Large-scale data breach, privacy violations, intellectual property theft.",
        "actions": [
            "Immediately suspend the account pending investigation",
            "Determine what records were accessed and assess exposure",
            "Implement Data Loss Prevention (DLP) controls",
            "Enable row-level access auditing in the database",
            "Apply per-query result size limits to prevent bulk dumps",
            "Initiate data breach notification procedures if PII was involved",
        ],
    },
    "Resource Exhaustion": {
        "why": "Out-of-memory, disk-full, and similar events may be caused by a DoS attack, misconfiguration, or runaway process.",
        "impact": "Service unavailability, data loss, system instability.",
        "actions": [
            "Identify the process consuming excessive resources and terminate if malicious",
            "Expand or provision additional resources as an immediate mitigation",
            "Investigate whether the exhaustion is intentional (DoS) or accidental",
            "Implement resource quotas and alerts at 80% utilization threshold",
            "Review recent deployments for resource leaks",
        ],
    },
    "Unexpected Shutdown": {
        "why": "Unplanned shutdowns may indicate kill commands injected by an attacker, kernel panics from exploits, or hardware failure.",
        "impact": "Service disruption, potential data corruption, loss of forensic evidence.",
        "actions": [
            "Review shutdown logs to determine cause (manual kill, OOM, kernel panic, attack)",
            "Preserve a forensic image of the system state before restarting",
            "Check for recently created cron jobs, init scripts, or systemd services",
            "Ensure all system and service logs were not tampered with before the shutdown",
            "Validate system integrity via file hash verification before returning to service",
        ],
    },
    "Configuration Change": {
        "why": "Unauthorized configuration changes can create security gaps — opening firewall ports, disabling logging, adding accounts.",
        "impact": "Persistent backdoor establishment, privilege escalation, audit trail tampering.",
        "actions": [
            "Compare the current configuration against the last known-good baseline",
            "Verify the change was authorized via the change management process",
            "Roll back unauthorized changes immediately",
            "Implement configuration drift detection with alerts",
            "Restrict who can make configuration changes using RBAC and PAM",
        ],
    },
    "Database Error Spike": {
        "why": "A surge in DB errors may indicate active SQL injection, connection pool exhaustion under a DoS, or DB instability.",
        "impact": "Data unavailability, potential data corruption, query-based exfiltration if combined with injection.",
        "actions": [
            "Check the database server health — CPU, memory, connections, query log",
            "Look for concurrent SQL injection attempts that may be causing errors",
            "Increase connection pool size or implement connection queuing",
            "Review slow query log for runaway queries",
            "Apply database patches if known vulnerability is being exploited",
        ],
    },
    "Log4Shell / JNDI Injection": {
        "why": "A ${jndi:...} lookup makes a vulnerable Log4j instance fetch and execute attacker-controlled code (CVE-2021-44228).",
        "impact": "Unauthenticated remote code execution and full server compromise.",
        "actions": [
            "Patch Log4j to a fixed version (2.17.1+) or apply the documented mitigation",
            "Block outbound LDAP/RMI/DNS from application servers at the firewall",
            "Hunt for outbound callbacks and dropped payloads from the affected host",
            "Set log4j2.formatMsgNoLookups=true as an interim control",
            "Rotate any credentials reachable from the compromised process",
        ],
    },
    "Web Shell Upload / Access": {
        "why": "A web shell gives an attacker an interactive backdoor to run commands through the web server.",
        "impact": "Persistent remote access, data theft, lateral movement, and further malware deployment.",
        "actions": [
            "Quarantine the host and remove the web shell file",
            "Scan the entire web root and upload directories for additional backdoors",
            "Block execution of scripts in upload directories",
            "Review access logs for commands run through the shell",
            "Rotate credentials and secrets accessible from the web server",
        ],
    },
    "PowerShell Encoded Command": {
        "why": "Encoded/hidden PowerShell is a hallmark of fileless malware and download-and-execute attacks.",
        "impact": "Code execution, persistence, and credential theft without dropping files to disk.",
        "actions": [
            "Decode the command (base64) and analyse what it does",
            "Enable PowerShell script-block and module logging",
            "Apply Constrained Language Mode and AMSI where possible",
            "Isolate the host if the payload is confirmed malicious",
            "Hunt for persistence (scheduled tasks, run keys, services)",
        ],
    },
    "Credential Dumping": {
        "why": "Dumping LSASS, SAM, or NTDS.dit harvests password hashes/tickets enabling domain-wide compromise.",
        "impact": "Mass credential theft, pass-the-hash, and full Active Directory takeover.",
        "actions": [
            "Isolate the host from the network immediately",
            "Force a domain-wide credential reset (including krbtgt twice)",
            "Investigate for lateral movement using the stolen credentials",
            "Enable Credential Guard / LSASS protection (RunAsPPL)",
            "Preserve memory and disk images for forensics",
        ],
    },
    "Reverse Shell Indicator": {
        "why": "Reverse-shell one-liners open an outbound interactive session, giving the attacker command access to the host.",
        "impact": "Full remote control of the host, data theft, and lateral movement.",
        "actions": [
            "Isolate the host and terminate the malicious connection",
            "Identify the listener (C2) IP/port and block it at the perimeter",
            "Hunt for persistence and any dropped tooling",
            "Restrict egress so internal hosts cannot dial out arbitrarily",
            "Image the host before remediation for forensics",
        ],
    },
    "DNS Tunneling / Exfiltration": {
        "why": "Encoding data into DNS queries lets an attacker bypass egress filtering to exfiltrate data or run C2.",
        "impact": "Covert data exfiltration and command-and-control over a normally-trusted protocol.",
        "actions": [
            "Block the offending domain and route DNS through a monitored resolver",
            "Inspect the host for data staging and beaconing processes",
            "Alert on long/high-entropy subdomains and abnormal TXT-query volume",
            "Restrict which hosts may query external DNS directly",
            "Preserve DNS logs for scope assessment",
        ],
    },
    "Cloud Metadata SSRF": {
        "why": "Reaching the instance metadata endpoint via SSRF can expose temporary cloud credentials.",
        "impact": "Theft of instance-role credentials leading to cloud account compromise.",
        "actions": [
            "Enforce IMDSv2 (token-required) and disable IMDSv1",
            "Rotate/revoke the instance role credentials immediately",
            "Add egress filtering blocking 169.254.169.254 from app code",
            "Validate and allowlist server-side URL fetches",
            "Review CloudTrail/activity logs for use of the leaked credentials",
        ],
    },
    "Ransomware File Activity": {
        "why": "Mass file renaming to crypto extensions and ransom notes indicate active ransomware encryption.",
        "impact": "Widespread data loss, operational outage, and extortion.",
        "actions": [
            "Isolate the host from the network and disable shared drives now",
            "Identify and kill the encrypting process; preserve a sample",
            "Restore affected data from known-clean offline backups",
            "Determine the entry vector and contain other hosts",
            "Engage incident response and follow breach-notification duties",
        ],
    },
    "XML External Entity (XXE)": {
        "why": "External entity processing lets an attacker read local files or trigger SSRF via crafted XML.",
        "impact": "Disclosure of local files (/etc/passwd, secrets), SSRF, and possible RCE.",
        "actions": [
            "Disable DTD and external-entity resolution in the XML parser",
            "Validate and allowlist inbound XML against a strict schema",
            "Patch/upgrade the affected XML library",
            "Review logs for files accessed via file:// payloads",
            "Apply least privilege to the parsing service account",
        ],
    },
    "LDAP Injection": {
        "why": "LDAP filter metacharacters can bypass authentication or enumerate directory data.",
        "impact": "Authentication bypass and disclosure of directory/user information.",
        "actions": [
            "Escape LDAP special characters and use parameterised filters",
            "Apply least-privilege bind accounts for directory queries",
            "Validate and allowlist user-supplied filter input",
            "Review directory logs for anomalous queries",
            "Add a WAF rule for LDAP filter metacharacters",
        ],
    },
    "Server-Side Request Forgery (SSRF)": {
        "why": "A user-controlled URL pointing at internal addresses lets an attacker pivot into the internal network.",
        "impact": "Access to internal services, cloud metadata, and otherwise unreachable systems.",
        "actions": [
            "Allowlist outbound destinations and block internal/loopback ranges",
            "Resolve and validate URLs server-side before fetching",
            "Disable unused URL schemes (file://, gopher://, dict://)",
            "Segment the network so app servers cannot reach sensitive internals",
            "Log and alert on outbound requests to private ranges",
        ],
    },
    "Security Scanner Activity": {
        "why": "Signature-matching scanner traffic indicates active reconnaissance or vulnerability probing.",
        "impact": "Mapping of attack surface that typically precedes targeted exploitation.",
        "actions": [
            "Block and rate-limit the scanning source",
            "Confirm the activity is unauthorised (not an approved scan)",
            "Watch the source for follow-on exploitation attempts",
            "Ensure exposed services are patched and hardened",
            "Tune WAF/IDS signatures for the observed tooling",
        ],
    },
    "OAuth / Token Abuse": {
        "why": "Refresh-token reuse, bad redirect_uri, or consent phishing indicate attempts to hijack delegated access.",
        "impact": "Account takeover and persistent API access without the user's password.",
        "actions": [
            "Revoke the affected tokens and require re-authentication",
            "Tighten redirect_uri allowlists and enforce PKCE",
            "Alert users on suspicious consent grants and review app permissions",
            "Monitor for refresh-token reuse and rotate on every use",
            "Audit the OAuth client configuration for misconfigurations",
        ],
    },
    "MFA Fatigue / Push Bombing": {
        "why": "Flooding a user with MFA prompts aims to make them approve one by accident or annoyance.",
        "impact": "Account takeover once a single prompt is approved.",
        "actions": [
            "Confirm the prompts with the user and reset credentials if unrecognised",
            "Enable number-matching / challenge-based MFA",
            "Rate-limit MFA push requests per account",
            "Temporarily lock the account if bombing is active",
            "Review the source of the authentication attempts",
        ],
    },
}

_SEVERITY_ACTIONS: dict[str, list[str]] = {
    "CRITICAL": [
        "Activate Incident Response Plan (IRP) immediately — do not wait",
        "Isolate affected systems from the network to prevent lateral movement",
        "Preserve forensic evidence — snapshot VM / copy logs before any changes",
        "Notify the Security Operations Center (SOC) and CISO immediately",
        "Escalate to management and legal if data breach is suspected",
        "Document ALL containment actions with timestamps for post-incident review",
        "Consider engaging external incident response specialists",
    ],
    "HIGH": [
        "Begin investigation within 1 hour of detection",
        "Increase monitoring and logging verbosity on affected systems",
        "Block confirmed malicious source IPs at the perimeter firewall",
        "Notify the security team lead and relevant system owner",
        "Consider temporary service restriction to reduce blast radius",
        "Review the last 24 hours of access logs for the affected system",
    ],
    "MEDIUM": [
        "Schedule a detailed investigation within 4 hours",
        "Review associated log context to determine if this is a true positive",
        "Apply relevant security patches / hardening if the vector is known",
        "Update detection rules to capture related indicators",
        "Document findings in the security log",
    ],
    "LOW": [
        "Review within the next business day",
        "Verify this is not a false positive based on normal user activity",
        "Update behavioral baselines if this is legitimate activity",
        "Add to security awareness training materials if applicable",
    ],
}


def get_recommendations(findings: list[dict]) -> list[dict]:
    """Return one concise recommendation per detected rule.

    Each recommendation is deliberately just two facts so it reads in a glance:
      • issue  — what was detected / why it is dangerous (one sentence)
      • action — the single most important step to take. This is the rule's live,
                 admin-editable recommended action (the same text shown on the Rules
                 page), so the panel, the PDF and the Rules page always agree.
    """
    seen: set[str] = set()
    result = []
    for f in findings:
        rule_name = f.get("rule_name", "")
        if rule_name in seen:
            continue
        seen.add(rule_name)

        rec = _RULE_ACTIONS.get(rule_name)
        live_action = (f.get("recommended_action") or "").strip()
        if rec:
            issue = rec.get("why", "")
            # Prefer the live recommended action; fall back to the library's first step.
            action = live_action or (rec.get("actions") or [""])[0]
        else:
            # New or admin-created rule with no library entry: describe what fired.
            issue = f.get("description", "")
            action = live_action

        if not issue and not action:
            continue
        result.append({
            "rule_name": rule_name,
            "severity": f.get("severity", "INFO"),
            "issue": issue,
            "action": action,
        })

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    result.sort(key=lambda r: sev_order.get(r["severity"], 5))
    return result


def get_general_actions(summary: dict) -> list[str]:
    """Return the top-5 immediate-response actions for the highest severity present
    (ordered most-critical first), trimmed so the summary stays focused."""
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if summary.get(sev, 0) > 0:
            return _SEVERITY_ACTIONS[sev][:5]
    return []
