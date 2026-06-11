# Cybersecurity Log Intelligence System

## Project Directory

The parent project folder should be:

```powershell
PS C:\Users\RFM5KOR\Downloads\Cybersecurity Log Intelligence System>
```

Create the project directory structure by running the following PowerShell command:

```powershell
New-Item -ItemType Directory -Force -Path "config", "app", "data/temp", "tests", "scripts" | Out-Null; New-Item -ItemType File -Force -Path "main.py", "README.md", ".env", "config/security.yaml", "config/email.yaml", "config/rules.yaml", "app/__init__.py", "app/database.py", "app/auth.py", "app/security.py", "app/rules.py", "app/processor.py", "app/reporter.py", "app/ui.py", "tests/test_auth.py", "tests/test_rules.py", "tests/test_processor.py", "scripts/init_db.py", "scripts/cleanup.py" | Out-Null; Write-Host "Directory structure created successfully!" -ForegroundColor Green
```

After running the above command, the project structure will be:

```text
Cybersecurity Log Intelligence System/
│
├── main.py
├── README.md
├── .env
│
├── config/
│   ├── security.yaml
│   ├── email.yaml
│   └── rules.yaml
│
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── auth.py
│   ├── security.py
│   ├── rules.py
│   ├── processor.py
│   ├── reporter.py
│   └── ui.py
│
├── data/
│   └── temp/
│
├── tests/
│   ├── test_auth.py
│   ├── test_rules.py
│   └── test_processor.py
│
└── scripts/
    ├── init_db.py
    └── cleanup.py
```

# Complete Installation Script

Go to the project directory:

```powershell
PS C:\Users\RFM5KOR\Downloads\Cybersecurity Log Intelligence System>
```

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

## Step 7: Verify Vulnerabilities

```bash
pip-audit
```

## Step 8: Verify Installed Packages

```bash
pip list
```


# To Delete Existing database
```
Remove-Item -Path "data\cybersec.db" -Force -ErrorAction SilentlyContinue
```
Verify the database is deleted
```
Test-Path "data\cybersec.db"
```

# Run the Application
```bash
python main.py
```

The application will automatically open in your browser at:

```text
http://localhost:8501
```

# Default Login Credentials

| Role  | Username        | Password                  | Email                                                                             |
| ----- | --------------- | ------------------------- | --------------------------------------------------------------------------------- |
| Admin | admin@bosch1211 | Security@bosch#9693261348 | [fixed-term.Rahul.Kumar@in.bosch.com](mailto:fixed-term.Rahul.Kumar@in.bosch.com) |

# How to Use the System

## IT Owner Workflow

1. Login using IT Owner credentials.

```text
Username: sampleid
Password: samplepass
```

2. Upload a log file using **📁 Upload Log File**.

3. Review the uploaded log preview.

4. Click **🔍 Analyze Log**.

5. View the analysis results:

   * Threat summary cards
   * Severity distribution pie chart
   * Threat timeline graph
   * Detailed threat table

6. Generate reports:

   * Click **📄 Generate Report**
   * PDF report downloads automatically
   * Report is emailed to the Admin/IT Owner.
