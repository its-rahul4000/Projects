import os
import datetime as _dt
from pathlib import Path
from zoneinfo import ZoneInfo

# Indian Standard Time (UTC+5:30)
IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> _dt.datetime:
    """Return current naive datetime in IST (UTC+5:30)."""
    return _dt.datetime.now(IST).replace(tzinfo=None)


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp"
DB_PATH = str(BASE_DIR / "cybersec.db")
DETECTION_RULES_YAML = str(BASE_DIR / "config" / "detection_rules.yaml")

# Session
SESSION_TIMEOUT_SECONDS = 900  # 15 minutes

# Password policy
PASSWORD_MIN_LENGTH = 20
PASSWORD_EXPIRY_DAYS = 180
PASSWORD_HISTORY_DEPTH = 5
TEMP_PASSWORD_LENGTH = 24

# Data retention
AUDIT_LOG_RETENTION_DAYS = 180

# File upload
MAX_UPLOAD_SIZE_MB = 50
ALLOWED_EXTENSIONS = {".log", ".txt", ".syslog", ".cef"}

# Default admin credentials (stored hashed in DB, never in plain text at runtime)
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "fixed-term.Rahul.Kumar@in.bosch.com"
_ADMIN_INITIAL_PASSWORD = "Cybersecuritylogadmin@12798"  # only used once during DB init

# Environment variable names (values loaded from .env)
ENV_SECRET_KEY = "APP_SECRET_KEY"
ENV_SMTP_HOST = "SMTP_HOST"
ENV_SMTP_PORT = "SMTP_PORT"
ENV_SMTP_USER = "SMTP_USER"
ENV_SMTP_PASS = "SMTP_PASS"
ENV_SMTP_FROM_NAME = "SMTP_FROM_NAME"

# Database
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Application info
APP_NAME = "Cybersecurity Log Intelligence System"
APP_VERSION = "2.0.0"

# Severity levels (ordered by priority)
SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
SEVERITY_COLORS = {
    "CRITICAL": "#ff4040",
    "HIGH": "#ff8c00",
    "MEDIUM": "#ffcc00",
    "LOW": "#36d68c",
    "INFO": "#00c8ff",
}

# Role constants
ROLE_ADMIN = "admin"
ROLE_IT_OWNER = "it_owner"
