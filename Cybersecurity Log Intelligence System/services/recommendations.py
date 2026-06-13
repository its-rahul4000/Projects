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
        "urgency": "Immediate",
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
        "urgency": "Immediate",
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
        "urgency": "High",
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
        "urgency": "High",
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
        "urgency": "Medium",
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
        "urgency": "Medium",
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
        "urgency": "High",
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
        "urgency": "Medium",
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
        "urgency": "High",
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
        "urgency": "Low",
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
        "urgency": "Medium",
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
        "urgency": "Medium",
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
        "urgency": "Immediate",
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
        "urgency": "Immediate",
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
        "urgency": "High",
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
        "urgency": "Immediate",
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
        "urgency": "High",
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
        "urgency": "High",
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
        "urgency": "Immediate",
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
        "urgency": "High",
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
        "urgency": "Immediate",
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
        "urgency": "Immediate",
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
        "urgency": "Medium",
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
        "urgency": "Medium",
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
        "urgency": "High",
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
        "urgency": "Medium",
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
        "urgency": "Immediate",
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
        "urgency": "High",
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
        "urgency": "High",
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
        "urgency": "Medium",
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
        "urgency": "Medium",
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
    """Return deduplicated per-rule recommendations for the detected findings."""
    seen: set[str] = set()
    result = []
    for f in findings:
        rule_name = f.get("rule_name", "")
        if rule_name in seen:
            continue
        seen.add(rule_name)
        rec = _RULE_ACTIONS.get(rule_name)
        if rec:
            result.append({
                "rule_name": rule_name,
                "severity": f.get("severity", "INFO"),
                **rec,
                # Keep it concise and to the point: only the top 3 actions
                "actions": rec.get("actions", [])[:3],
            })
    # Sort by severity
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    result.sort(key=lambda r: sev_order.get(r["severity"], 5))
    return result


def get_general_actions(summary: dict) -> list[str]:
    """Return general severity-based response actions."""
    for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if summary.get(sev, 0) > 0:
            return _SEVERITY_ACTIONS[sev]
    return []
