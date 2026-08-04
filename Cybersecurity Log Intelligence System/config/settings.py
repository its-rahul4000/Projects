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
ALLOWED_EXTENSIONS = {".log", ".txt", ".syslog", ".cef"}

# Analysis worker pool — heavy log analysis runs in separate OS processes so it
# never blocks the Streamlit server under concurrent load (avoids the GIL).
_CPU = os.cpu_count() or 2
# Cap concurrent worker processes so a burst of users can't exhaust CPU/RAM.
ANALYSIS_MAX_WORKERS = int(os.getenv("ANALYSIS_MAX_WORKERS", str(max(2, min(_CPU - 1, 8)))))
# Set USE_WORKER_PROCESS=0 to force in-process analysis (e.g. for debugging).
USE_WORKER_PROCESS = os.getenv("USE_WORKER_PROCESS", "1").strip().lower() not in ("0", "false", "no")

# Default admin credentials (stored hashed in DB, never in plain text at runtime)
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "fixed-term.Rahul.Kumar@in.bosch.com"
# First-boot seed only: hashed (Argon2id) into the DB during initial setup and never
# read at runtime afterwards. Overridable via the ADMIN_INITIAL_PASSWORD env var.
_ADMIN_INITIAL_PASSWORD = os.getenv(
    "ADMIN_INITIAL_PASSWORD", "Cybersecuritylogadmin@12798"
)

# Environment variable NAMES (values loaded from .env) — these are identifiers, not secrets.
ENV_SECRET_KEY = "APP_SECRET_KEY"  # nosec B105
ENV_SMTP_HOST = "SMTP_HOST"
ENV_SMTP_PORT = "SMTP_PORT"
ENV_SMTP_USER = "SMTP_USER"
ENV_SMTP_PASS = "SMTP_PASS"  # nosec B105
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

# Detection-rule kinds
RULE_TYPE_STATIC = "static"          # regex match on each log line
RULE_TYPE_BEHAVIORAL = "behavioral"  # built-in behavioural checker (metric key)
RULE_TYPE_CUSTOM = "custom"          # admin no-code rule: pattern + threshold + group-by

# Group-by options for the generic no-code custom-rule engine.
# Maps a UI label to the DataFrame column used for aggregation ("global" = whole file).
RULE_GROUP_BY_OPTIONS = {
    "Source IP": "source_ip",
    "Username": "username",
    "Whole file (total count)": "global",
}
