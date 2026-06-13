import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from config.settings import (
    ENV_SMTP_HOST, ENV_SMTP_PORT, ENV_SMTP_USER,
    ENV_SMTP_PASS, ENV_SMTP_FROM_NAME, APP_NAME, now_ist,
)

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict | None:
    host = os.getenv(ENV_SMTP_HOST)
    port = os.getenv(ENV_SMTP_PORT, "587")
    user = os.getenv(ENV_SMTP_USER)
    password = os.getenv(ENV_SMTP_PASS)
    from_name = os.getenv(ENV_SMTP_FROM_NAME, APP_NAME)
    if not all([host, user, password]):
        return None
    return {"host": host, "port": int(port), "user": user, "password": password, "from_name": from_name}


def is_smtp_configured() -> bool:
    return _get_smtp_config() is not None


def test_smtp_connection() -> tuple[bool, str]:
    cfg = _get_smtp_config()
    if not cfg:
        return False, (
            "SMTP is not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASS in your .env file."
        )
    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
        return True, f"Connection to {cfg['host']}:{cfg['port']} successful. Login verified for {cfg['user']}."
    except smtplib.SMTPAuthenticationError:
        return False, f"Authentication failed for {cfg['user']}. Check SMTP_USER and SMTP_PASS."
    except smtplib.SMTPConnectError as exc:
        return False, f"Could not connect to {cfg['host']}:{cfg['port']}: {exc}"
    except smtplib.SMTPException as exc:
        return False, f"SMTP error: {exc}"
    except OSError as exc:
        return False, f"Network error connecting to {cfg['host']}:{cfg['port']}: {exc}"


def _send(msg: MIMEMultipart, cfg: dict) -> bool:
    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], msg["To"], msg.as_string())
        return True
    except smtplib.SMTPException as exc:
        logger.error("SMTP error sending email to %s: %s", msg.get("To"), exc)
        return False
    except Exception as exc:
        logger.error("Unexpected error sending email: %s", exc)
        return False


def send_temp_password_email(to_email: str, username: str, temp_password: str) -> bool:
    cfg = _get_smtp_config()
    if not cfg:
        logger.warning("SMTP not configured – cannot send temp password email.")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"] = to_email
    msg["Subject"] = f"[{APP_NAME}] Your Temporary Access Password"

    body = f"""Dear {username},

Your IT Owner account has been created in the {APP_NAME}.

Your temporary password is:

    {temp_password}

IMPORTANT:
- This password is valid for a single use only.
- You will be required to change it immediately upon your first login.
- Your new password must be at least 20 characters long and include
  uppercase letters, lowercase letters, numbers, and special characters.

Login at: http://localhost:8501

If you did not request this account, please contact your Administrator immediately.

Best Regards,
{APP_NAME}
"""
    msg.attach(MIMEText(body, "plain"))
    return _send(msg, cfg)


def send_forgot_password_email(to_email: str, username: str, temp_password: str) -> bool:
    cfg = _get_smtp_config()
    if not cfg:
        logger.warning("SMTP not configured – cannot send forgot-password email.")
        return False

    msg = MIMEMultipart()
    msg["From"] = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"] = to_email
    msg["Subject"] = f"[{APP_NAME}] Password Reset Request"

    body = f"""Dear {username},

A password reset was requested for your account in the {APP_NAME}.

Your new temporary password is:

    {temp_password}

IMPORTANT:
- This password is valid for a single use only.
- You will be required to set a new permanent password immediately upon login.
- Your new password must be at least 20 characters long.
- If you did NOT request this reset, change your password immediately
  and contact your Administrator.

Login at: http://localhost:8501

Best Regards,
{APP_NAME}
"""
    msg.attach(MIMEText(body, "plain"))
    return _send(msg, cfg)


def send_pdf_report_email(
    to_email: str,
    username: str,
    pdf_bytes: bytes,
    report_filename: str,
    summary: dict,
    analyzed_files: list[str],
    append_mode: bool = False,
) -> bool:
    cfg = _get_smtp_config()
    if not cfg:
        logger.warning("SMTP not configured – cannot send PDF report email.")
        return False

    now = now_ist()
    msg = MIMEMultipart()
    msg["From"] = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"] = to_email
    msg["Subject"] = f"[SECURITY REPORT] Log Analysis Report — {now.strftime('%Y-%m-%d')}"

    files_list = "\n".join(f"  {i+1}. {f}" for i, f in enumerate(analyzed_files))
    body = f"""Dear {username},

A security analysis report has been generated for the log file(s) you uploaded.

Report Details:
-----------------
Generated By:    {username} ({to_email})
Analysis Date:   {now.strftime('%Y-%m-%d %H:%M:%S')} IST
Append Mode:     {'ENABLED' if append_mode else 'DISABLED'}
Rules Applied:   Administrator-approved rule set (Static + Dynamic)

Files Analyzed:
-----------------
{files_list}

Threat Summary:
-----------------
Total Threats:  {summary.get('total', 0)}
Critical:       {summary.get('CRITICAL', 0)}
High:           {summary.get('HIGH', 0)}
Medium:         {summary.get('MEDIUM', 0)}
Low:            {summary.get('LOW', 0)}

The detailed report is attached to this email.

NOTE: This report is NOT stored on the server.
Please save a copy for your records.

Best Regards,
{APP_NAME}
"""
    msg.attach(MIMEText(body, "plain"))

    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(pdf_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=report_filename)
    msg.attach(attachment)

    return _send(msg, cfg)
