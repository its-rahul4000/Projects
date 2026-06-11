# Cybersecurity Log Intelligence System

A secure, role-based web application for automated threat detection in log files, featuring real-time dashboard visualizations, PDF report generation, and email delivery.

## Project Directory

```
PS C:\Users\rahul\Desktop\Github\Projects\Cybersecurity Log Intelligence System>
```

## Project Structure

```
Cybersecurity Log Intelligence System/
├── main.py                      # Entry point: python main.py
├── app.py                       # Streamlit application
├── .env                         # Your secrets (copy from .env.example)
├── .env.example                 # Environment variable template
├── requirements.txt
├── pytest.ini
├── config/
│   ├── settings.py              # App-wide constants
│   └── detection_rules.yaml    # Default detection rules (seeded to DB on startup)
├── database/
│   ├── models.py               # SQLAlchemy ORM models
│   ├── db.py                   # Engine and session factory
│   └── init_db.py              # DB init: tables + admin + rules
├── auth/
│   ├── password.py             # Argon2id hashing, policy enforcement
│   ├── session_manager.py      # Session CRUD and 15-min timeout
│   └── access_control.py      # Role-based guards
├── services/
│   ├── audit_service.py        # Audit logging
│   ├── email_service.py        # SMTP email with PDF attachment
│   ├── user_service.py         # User CRUD and authentication
│   ├── log_parser.py           # Multi-format log parsing
│   ├── threat_engine.py        # Static and dynamic rule evaluation
│   └── report_service.py      # ReportLab PDF generation
├── ui/
│   ├── components.py           # Shared widgets and charts
│   ├── login_page.py
│   ├── register_page.py
│   ├── dashboard_page.py
│   ├── upload_page.py
│   ├── results_page.py
│   ├── rules_page.py
│   ├── users_page.py
│   └── audit_page.py
├── utils/
│   ├── validators.py
│   ├── temp_file_manager.py
│   └── crypto_utils.py
├── tests/
│   ├── conftest.py
│   ├── test_password.py
│   ├── test_log_parser.py
│   ├── test_threat_engine.py
│   └── test_user_service.py
└── temp/                       # Temporary uploaded files (auto-cleaned)
```

---

# Complete Installation Script

## Step 1: Create Conda Environment

```bash
conda create -n cybersec python=3.12 -y
```

## Step 2: Activate Environment

```bash
conda activate cybersec
```

## Step 3: Upgrade pip

```bash
python -m pip install --upgrade pip
```

## Step 4: Install Core Packages

```bash
pip install streamlit==1.54.0 sqlalchemy==2.0.41 passlib==1.7.4 argon2-cffi==23.1.0 pandas==2.2.3 plotly==6.5.0 reportlab==4.3.1 pyyaml==6.0.2 email-validator==2.3.0 python-dotenv==1.2.2 bcrypt==4.3.0 itsdangerous==2.2.0 cryptography==46.0.7 watchdog==6.0.0 werkzeug==3.1.6
```

## Step 5: Install Development and Security Tools

```bash
pip install bandit==1.8.3 pip-audit==2.9.0
```

## Step 6: Install Testing Tools

```bash
pip install pytest==9.0.3 pytest-cov==6.1.1
```

## Step 7: Configure Environment Variables

Copy the environment template and fill in your values:

```bash
copy .env.example .env
```

Open `.env` and set your SMTP credentials:

```env
APP_SECRET_KEY=your_secure_random_key_here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_specific_password
SMTP_FROM_NAME=Cybersecurity Log Intelligence System
```

> **Gmail users:** Enable 2-Factor Authentication and create an App Password at https://myaccount.google.com/apppasswords

> **Note:** Email is optional for development. The system works without SMTP configured — PDF reports can still be downloaded via the browser.

## Step 8: Verify Installed Packages

```bash
pip list
```

## Step 9: Verify No Known Vulnerabilities

```bash
pip-audit
```

---

# To Delete the Existing Database

```powershell
Remove-Item cybersec.db -ErrorAction SilentlyContinue
```

Verify the database is deleted:

```powershell
Test-Path cybersec.db
```

The database is automatically recreated with the default admin account and all 31 detection rules on the next startup.

---

# Run the Application

```bash
python main.py
```

The application will automatically open in your browser at:

```
http://localhost:8501
```

The database is initialised automatically on first run — no manual setup required.

---

# Default Login Credentials

| Role      | Username        | Password                   | Email                                      |
|-----------|-----------------|----------------------------|--------------------------------------------|
| Admin     | admin@bosch1211 | Security@bosch#9693261348  | fixed-term.Rahul.Kumar@in.bosch.com        |

---

# How to Use the System

## IT Owner Workflow

### 1. Register an IT Owner Account

- Click **Register as IT Owner** on the login page.
- Enter a unique **Username** and your **Email Address**.
- The system generates a temporary password and emails it to you.

### 2. First Login

- Enter your username and the temporary password from your email.
- You are immediately prompted to set a new permanent password.
- Password requirements: minimum **20 characters**, uppercase, lowercase, digits, and special characters.

### 3. Upload a Log File

- Navigate to **Upload Log File**.
- Supported formats: `.log`, `.txt`, `.syslog`, `.cef`
- Check **Append Analysis** to merge results with previous uploads.
- Click **Analyze Log**.

### 4. Review Results

- Navigate to **Analysis Results** to view:
  - Severity summary cards (Critical / High / Medium / Low)
  - Severity pie chart and threat type bar chart
  - Threat timeline and top attack sources
  - Filterable detailed findings table

### 5. Generate Report

- Click **Generate PDF Report** to download the report to your browser.
- Click **Email Report to Me** to receive the report as an email attachment.

### 6. View Detection Rules

- Navigate to **View Detection Rules** to see the active static and dynamic rules (read-only).

---

## Administrator Workflow

Administrators have all IT Owner capabilities plus:

### Rule Management

- Navigate to **Threat Detection Rules**.
- **Add** new static (regex-based) or dynamic (count-based) rules.
- **Enable / Disable** individual rules.
- **Edit** rule conditions, thresholds, and severity levels.
- **Delete** rules.
- All changes take effect immediately for all IT Owners.

### User Management

- Navigate to **User Management**.
- View all IT Owner accounts.
- **Activate / Deactivate** accounts.
- **Delete** accounts.

### Audit Logs

- Navigate to **Audit Logs**.
- Filter by user, action type, and date range.
- Export as CSV.

---

# Running Tests

```bash
pytest
```

Or with coverage report only:

```bash
pytest --no-cov
```

Run security static analysis:

```bash
bandit -r . -x tests/ -ll
```

---

# Detection Rules Overview

The system ships with **31 pre-configured detection rules** (18 static + 13 dynamic):

## Static Rules (Regex-Based)

| Rule | Severity |
|------|----------|
| SQL Injection Attempt | HIGH |
| Path Traversal Attempt | HIGH |
| Command Injection | CRITICAL |
| XSS Attempt | MEDIUM |
| Directory Scanning | MEDIUM |
| Abnormal HTTP Methods | HIGH |
| Dormant Account Activity | HIGH |
| Concurrent Sessions | HIGH |
| Geographic Anomaly | MEDIUM |
| Unusual Working Hours | LOW |
| Off-Hours Access | MEDIUM |
| Unauthorized Access Attempt | HIGH |
| Privilege Escalation | CRITICAL |
| Sensitive Resource Access | HIGH |
| API Key Misuse | MEDIUM |
| Session Hijacking Pattern | CRITICAL |
| Account Lockout Event | HIGH |
| Successful Login After Failures | MEDIUM |

## Dynamic Rules (Count-Based with Configurable Thresholds)

| Rule | Default Threshold | Severity |
|------|-------------------|----------|
| Brute Force Attack | >5 in 60 sec | CRITICAL |
| Repeated Failed Logins | >10 in 5 min | HIGH |
| Rapid Login Attempts | >20 in 10 sec | CRITICAL |
| Multiple User Failures | >5 in 5 min | HIGH |
| Repeated Access Denials | >10 in 5 min | HIGH |
| Error Rate Spike | >50 in 5 min | MEDIUM |
| Service Crash Loop | >3 in 2 min | HIGH |
| Rapid Sequential Actions | >50 in 1 min | MEDIUM |
| Mass Data Access | >1000 records | MEDIUM |
| Resource Exhaustion | Any occurrence | HIGH |
| Unexpected Shutdown | Any occurrence | HIGH |
| Configuration Change | Any occurrence | MEDIUM |
| Database Error Spike | >20 in 5 min | MEDIUM |

---

# Security Features

- **Argon2id** password hashing (time_cost=3, memory_cost=64MB)
- **Session timeout** after 15 minutes of inactivity
- **Password policy**: minimum 20 chars, mixed case, digits, special chars
- **Password expiry**: IT Owner passwords expire after 180 days
- **Password history**: last 5 passwords cannot be reused
- **Parameterised queries** via SQLAlchemy ORM (SQL injection prevention)
- **Input validation and sanitization** on all user inputs
- **Audit trail** for all security-sensitive actions (180-day retention)
- **Temporary file cleanup** on logout and session expiry
- **SMTP with STARTTLS** for secure email delivery
- **Role-Based Access Control** (Administrator / IT Owner)
- **Principle of Least Privilege** enforced at every page

---

# Data Retention Policy

| Data Type | Retention | Action After Expiry |
|-----------|-----------|---------------------|
| Audit Logs | 180 days | Auto-deleted on startup |
| IT Owner Passwords | 180 days | Force change at next login |
| Temporary Passwords | Single use | Invalidated after first login |
| Analysis Results | Session only | Cleared on logout / timeout |
| Uploaded Log Files | Session only | Deleted after analysis |
| PDF Reports | Not stored | Generated on-demand only |
| Detection Rules | Persistent | Admin-managed |

---

# Software Bill of Materials (SBOM)

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12 | Runtime |
| Streamlit | 1.54.0 | Web Dashboard |
| SQLAlchemy | 2.0.41 | ORM / Database |
| Pandas | 2.2.3 | Data Processing |
| Plotly | 6.5.0 | Visualizations |
| ReportLab | 4.3.1 | PDF Generation |
| PyYAML | 6.0.2 | Configuration |
| argon2-cffi | 23.1.0 | Argon2id Hashing |
| passlib | 1.7.4 | Password Utilities |
| python-dotenv | 1.2.2 | Secret Management |
| email-validator | 2.3.0 | Email Validation |
| itsdangerous | 2.2.0 | Secure Token Signing |
| cryptography | 46.0.7 | Encryption |
| werkzeug | 3.1.6 | WSGI Utilities |
| bcrypt | 4.3.0 | Password Hashing |
| watchdog | 6.0.0 | File Monitoring |
| bandit | 1.8.3 | Static Security Analysis |
| pip-audit | 2.9.0 | Dependency Scanning |
| pytest | 9.0.3 | Testing |
| pytest-cov | 6.1.1 | Coverage Reporting |
