# Cybersecurity Log Intelligence System

## Admin Credential
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
├── requirements.txt
├── pytest.ini
├── config/
│   ├── settings.py              # App-wide constants + IST timezone helper
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
│   ├── audit_service.py        # Audit logging (IST timestamps)
│   ├── email_service.py        # SMTP email with PDF attachment
│   ├── user_service.py         # User CRUD, authentication, forgot password
│   ├── log_parser.py           # Multi-format log parsing
│   ├── threat_engine.py        # Static and dynamic rule evaluation
│   ├── recommendations.py      # Per-rule remediation guidance
│   └── report_service.py      # ReportLab PDF generation (in-memory only)
├── ui/
│   ├── components.py           # Light theme CSS, full-bleed top nav, shared widgets, charts
│   ├── login_page.py           # Login + Forgot Password + Admin Setup
│   ├── register_page.py
│   ├── dashboard_page.py
│   ├── upload_page.py          # Single/multi-file upload
│   ├── results_page.py         # Results + Recommended Actions panel
│   ├── rules_page.py           # Rules with plain-language descriptions
│   ├── users_page.py
│   ├── settings_page.py        # SMTP config (admin) + Change Password (all roles)
│   └── audit_page.py           # IST timestamps
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

Open the `.env` file and configure the required values:

* **Generate a secure `APP_SECRET_KEY`:** Run the following command in your terminal:

  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

* **Set `SMTP_USER`:** Enter your Gmail email address.

* **Generate a 16-character `SMTP_PASS` (Gmail App Password):**

  1. Verify that **2-Step Verification (2FA)** is enabled on your Gmail account.
  2. Navigate to `https://myaccount.google.com/apppasswords`.
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



# How to Use the System

## IT Owner Workflow

### 1. Register an IT Owner Account

- Click **Register as IT Owner** on the login page.
- Enter a unique **Username** and your **Email Address**.
- The system generates a temporary password and emails it (or shows it on screen only if email is not configured).
- You are redirected to the login page with your username already filled in — just enter the temporary password.

### 2. First Login

- Enter your username and the temporary password.
- You are immediately prompted to set a new permanent password.
- Password requirements: minimum **20 characters**, uppercase, lowercase, digits, and special characters.

### 3. Upload a Log File

- Navigate to **Upload Log File**.
- Supported formats: `.log`, `.txt`, `.syslog`, `.cef`
- Enable **Append Mode** to upload multiple files and merge their analysis.
- Click **Analyze Log File**.

### 4. Review Results

- Navigate to **Analysis Results** to view:
  - Severity summary cards (Critical / High / Medium / Low)
  - **Recommended Actions** panel with per-rule remediation guidance
  - Severity pie chart and threat type bar chart
  - Threat timeline and top attack sources
  - Filterable detailed findings table

### 5. Generate Report

- Click **Generate PDF Report** to download the report to your browser.
- Click **Email Report to Me** to receive the report as an email attachment (requires SMTP).

### 6. View Detection Rules

- Navigate to **Rules** to see all active rules (read-only) with plain-language explanations.

### 7. Change Password

- Open the **Settings** page and use the **Change Your Password** section at any time.

---


# Running Tests

```bash
pytest
```

Run security static analysis:

```bash
bandit -r . -x tests/ -ll
```

---

