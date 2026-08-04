# Cybersecurity Log Intelligence System

## Default Admin Credential
```
Admin id- admin
Password- Cybersecuritylogadmin@12798
```

---

## Project Directory

```
PS C:\Users\rahul\Desktop\Github\Projects\Cybersecurity Log Intelligence System>
```

## Project Structure

```
Cybersecurity Log Intelligence System/
├── main.py                      # Entry point: python main.py
├── app.py                       # Streamlit application routing
├── .env                         # Your secrets (copy from .env.example)
├── .env.example                 # Environment variable template
├── .gitignore
├── requirements.txt
├── .bandit                      # Bandit security-scan config (excludes tests/ and Testcases/)
├── .streamlit/
│   └── config.toml              # Streamlit theme + server config (light theme)
├── config/
│   ├── settings.py              # App-wide constants + IST timezone helper
│   └── detection_rules.yaml     # Default detection rules (seeded to DB on startup)
├── database/
│   ├── models.py                # SQLAlchemy ORM models
│   ├── db.py                    # Engine and session factory
│   └── init_db.py               # DB init: tables + admin + rules
├── auth/
│   ├── password.py              # Argon2id hashing, policy enforcement
│   ├── session_manager.py       # Session CRUD and 15-min timeout
│   └── access_control.py        # Role-based guards
├── services/
│   ├── audit_service.py         # Audit logging (IST timestamps)
│   ├── email_service.py         # SMTP email with PDF attachment
│   ├── user_service.py          # User CRUD, authentication, forgot password
│   ├── log_parser.py            # Multi-format log parsing
│   ├── threat_engine.py         # Static + behavioral rule evaluation (multi-core)
│   ├── _static_match.py         # Stdlib-only regex matcher run in spawned workers (light startup)
│   ├── analysis_runner.py       # Submits jobs to process-isolated workers; bounds concurrency
│   ├── analysis_worker.py       # Process-isolated analysis worker (python -m services.analysis_worker)
│   ├── recommendations.py       # Per-rule remediation guidance
│   └── report_service.py        #ReportLab PDF generation (in-memory only)
├── ui/
│   ├── components.py            # Light theme CSS, full-bleed top nav, shared widgets, charts
│   ├── login_page.py            # Login + Forgot Password + Admin Setup
│   ├── register_page.py
│   ├── dashboard_page.py        # Home: upload + analyze + results (all-in-one workspace)
│   ├── rules_page.py            # Rules cards 
│   ├── users_page.py
│   ├── settings_page.py         # SMTP config (admin) + Change Password (all roles)
│   └── audit_page.py            # IST timestamps
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
├── Testcases/                  # One sample .log per detection rule (validate each rule)
│   └── <Rule Name>.log         # e.g. "Brute Force Attack.log", "SQL Injection Attempt.log"
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
pip install streamlit==1.54.0 sqlalchemy==2.0.41 passlib==1.7.4 argon2-cffi==23.1.0 pandas==2.2.3 plotly==6.5.0 reportlab==4.3.1 pyyaml==6.0.2 email-validator==2.3.0 python-dotenv==1.2.2 bcrypt==4.3.0 itsdangerous==2.2.0 cryptography==48.0.1 watchdog==6.0.0 tzdata==2026.2 msgpack==1.2.1
```


> **Tip:** You can install everything in one go with `pip install -r requirements.txt` instead of Steps 4–6.

## Step 5: Install Development and Security Tools

```bash
pip install bandit==1.8.3 pip-audit==2.9.0
```

## Step 6: Install Testing Tools

```bash
pip install pytest==9.0.3 pytest-cov==6.1.1
```

## Step 7: Configure Environment Variables

Open the `.env` file and configure the required values:

* **Generate a secure `APP_SECRET_KEY`:** Run the following command in your terminal:

  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

* **Set `SMTP_USER`:** Enter your Gmail email address.

* **Generate a 16-character `SMTP_PASS` (Gmail App Password):**

  1. Verify that **2-Step Verification (2FA)** is enabled on your Gmail account.
  2. Navigate to `https://myaccount.google.com/apppasswords`
  3. Enter a name for the app (e.g., **"Cybersecurity Log System"**).
  4. Click **Create** to generate a **16-character App Password**.
  5. Copy the generated App Password and paste it as `SMTP_PASS` in your `.env` file.

> **Important:** Use the generated **App Password**, **not** your regular Gmail account password.

## Step 8: Verify Installed Packages

```bash
pip list
```

## Step 9: Verify No Known Vulnerabilities

```bash
pip-audit
```

---

# Delete Existing Database (If Needed)

Delete the existing database:

```powershell
Remove-Item cybersec.db -ErrorAction SilentlyContinue
```

Verify that it has been deleted:

```powershell
Test-Path cybersec.db
```

> **Note:** The database is automatically recreated with the default administrator account and all pre-configured threat detection rules on the next application startup.

---

# Run the Application

```bash
python main.py
```

The application will automatically open in your browser at:

```text
http://localhost:8501
```

> **Automatic Initialization:** The database is initialized automatically on first run. No manual setup is required.

---
# To Terminate the session
```bash
Ctrl + C  in Powershell terminal
```
---

# Concurrency & Performance

Log analysis (parsing + rule evaluation) runs in **separate worker processes**, not in the
Streamlit server process. This keeps the dashboard responsive for all IT Owners even while a
large log file is being analysed, and isolates crashes from the web server.

- Rule evaluation is **vectorized** (each regex mask computed once) **and runs across multiple CPU
  cores** — static (per-line) rules are matched on row-chunks in parallel inside the worker, while
  behavioral rules aggregate over the whole file. The parallel match workers are **import-light**
  (they load only the standard-library `re`, never pandas), so each spawned process starts in
  milliseconds — this is what makes multi-core matching a net win on every machine.
- A **bounded pool** caps how many analyses run at once so a burst of users cannot exhaust CPU/RAM;
  extra jobs queue until a worker frees up.
- An analysis **keeps running if you navigate to another page and come back** — it executes in a
  detached background worker, shows a **live entry counter** while it runs, and offers a
  **Stop analysis** button to cancel it.
- If a worker process cannot be launched, the system **falls back to in-process analysis** automatically.

Optional environment variables (in `.env`):

```env
# Max concurrent analysis worker processes (default: CPU count - 1, capped at 8)
ANALYSIS_MAX_WORKERS=8
# Set to 0 to force in-process analysis (debugging only)
USE_WORKER_PROCESS=1
```

> For very large deployments needing guaranteed throughput across machines, the worker layer
> (`services/analysis_runner.py` + `services/analysis_worker.py`) can be swapped for an external
> queue (Celery/RQ + Redis) without touching the UI.

---

# How to Use the System

## IT Owner Workflow

### 1. Register an IT Owner Account

- Click **Register as IT Owner** on the login page.
- Enter a unique **Username** and your **Email Address**.
- The system generates a temporary password and emails it (or shows it on screen once if email delivery is unavailable).
- **No account is created yet** — the registration is held as *pending*. You are redirected to the login page with your username already filled in.

### 2. First Login (activates the account)

- Enter your username and the temporary password.
- You are prompted to **set a permanent password — this is what creates and activates your account**. If you abandon registration before this step, no account is left behind.
- Password requirements: minimum **20 characters**, uppercase, lowercase, digits, and special characters.

### 3. Upload & Analyze a Log File (on the Home page)

- Everything happens on the **Home** page — no page hopping.
- **Set the context first (mandatory for IT Owners):** fill in **Application / Product** and
  **LeanIX ID / PIF ID** (both marked with a red `*`). The **Analyze** button stays disabled until
  both are filled, and the two fields **lock once an analysis exists** so every file in the run
  shares the same Application/LeanIX combo. These values flow into the audit trail, the PDF report,
  and the email subject/body. *(Administrators don't see these fields — see the note below.)*
- Your Application/LeanIX entries and any files already in the drop box **persist if you navigate to
  another page and come back** — nothing is lost until you click **Clear & New Analysis**.
- Supported formats: `.log`, `.txt`, `.syslog`, `.cef`
- Drop **one or more files** — Analyze processes everything currently in the uploader together.
  Staged files appear in a collapsible **View / remove files** list where you can drop individual
  files with the ✕ before analyzing.
- Click **Analyze Log File**. A real progress bar tracks parsing and rule evaluation and shows a
  **live count of entries** processed.
- You can **switch to other pages and come back without stopping the analysis** — it runs in the
  background. Use the **Stop analysis** button to cancel a run.

### 4. Review Results (inline, below the uploader)

- Severity summary cards (Critical / High / Medium / Low)
- **Recommended Actions** panel with per-rule remediation guidance
- **Findings Table** with a severity filter, a **search box** (IP, username, rule, description) with an inline clear (✕), and a **Download findings (CSV)** button for the full data
- **Visualizations**: severity pie, threat types, timeline, top attack sources, top involved users, findings by rule type, and a "Threats by Rule" table
- **Raw Log Data** tab

### 5. Generate / Email Report

- Click **Generate PDF Report** to download the report to your browser.
- Click **Email Report** to receive it by email (requires SMTP). The email carries **two
  attachments**: the **PDF report** and the full **findings table as a CSV**.
  - When an **IT Owner** runs it, the report is emailed to **that IT Owner and the Administrator**.
  - When the **Administrator** runs it, the report is emailed to **the Administrator only**.


### 7. Change Password

- Open the **Settings** page and use the **Change Your Password** section at any time.

---


# To Run Test Suite and Static Analysis

Run the unit test suite (43 tests):

```bash
pytest
```

Run security static analysis on the application code:

```bash
bandit -r .
```

> The project-level `.bandit` config excludes the `tests/` and `Testcases/` trees (unit
> tests, fuzz harness, and log-generator fixtures), so a clean run reports
> **No issues identified**. Application code is fully scanned.

---


