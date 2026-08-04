import os
import html as _html
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
        # msg["To"] may contain several comma-separated addresses — deliver to each.
        to_addrs = [a.strip() for a in str(msg["To"]).split(",") if a.strip()]
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["user"], to_addrs, msg.as_string())
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


def _report_html(intro: str, generated_by: str, now,
                 summary: dict, analyzed_files: list[str],
                 application: str = "", leanix_id: str = "") -> str:
    """Shared HTML body for a report email. `intro` is the recipient-specific opening
    (greeting + context) that precedes the common Report Details / Summary blocks. The
    full findings travel as the attached PDF and CSV (not embedded in the body)."""
    files_rows = "".join(f"<li>{_html.escape(str(f))}</li>" for f in analyzed_files) or "<li>N/A</li>"

    def _meta(label, value):
        return (f'<tr><td style="padding:3px 16px 3px 0;color:#555;white-space:nowrap;">{label}</td>'
                f'<td style="padding:3px 0;color:#1a202c;">{_html.escape(str(value))}</td></tr>')

    # Application/Product + LeanIX/PIF ID (and the "Rules Applied" note) appear only for IT
    # Owner reports, which always carry that context. Admin test reports have neither.
    has_context = bool(application or leanix_id)
    context_rows = (
        _meta("Application/Product:", application or "N/A")
        + _meta("LeanIX ID / PIF ID:", leanix_id or "N/A")
    ) if has_context else ""
    rules_row = _meta("Rules Applied:", "Administrator-approved rule set (Static + Behavioral)") if has_context else ""

    def _sev(label, value, color):
        return (f'<tr>'
                f'<td style="padding:6px 24px 6px 12px;border-top:1px solid #edf0f4;">{label}</td>'
                f'<td style="padding:6px 16px;border-top:1px solid #edf0f4;text-align:right;'
                f'font-weight:700;color:{color};">{value}</td></tr>')

    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1a202c;line-height:1.55;">
  {intro}

  <p style="margin:16px 0 4px;"><strong>Report Details</strong></p>
  <table style="border-collapse:collapse;">
    {context_rows}
    {_meta("Generated By:", generated_by)}
    {_meta("Analysis Date:", now.strftime('%d-%m-%Y %H:%M:%S') + " IST")}
    {rules_row}
  </table>

  <p style="margin:16px 0 4px;"><strong>Files Analyzed</strong></p>
  <ul style="margin:0 0 8px 18px;padding:0;">{files_rows}</ul>

  <p style="margin:16px 0 4px;"><strong>Threat Summary</strong></p>
  <table style="border-collapse:collapse;border:1px solid #e2e8f0;border-radius:6px;min-width:260px;">
    <tr style="background:#003366;color:#ffffff;">
      <th style="text-align:left;padding:6px 24px 6px 12px;">Severity</th>
      <th style="text-align:right;padding:6px 16px;">Count</th>
    </tr>
    {_sev("Total Threats", summary.get('total', 0), "#003366")}
    {_sev("Critical", summary.get('CRITICAL', 0), "#dc3545")}
    {_sev("High", summary.get('HIGH', 0), "#fd7e14")}
    {_sev("Medium", summary.get('MEDIUM', 0), "#d39e00")}
    {_sev("Low", summary.get('LOW', 0), "#28a745")}
  </table>

  <p style="margin-top:16px;">For detailed results, please refer to the attached PDF report
  and the complete findings table in CSV format.</p>
  <p style="color:#888;font-size:12px;margin-top:12px;">Note: This report is NOT stored on the server. Please save a copy for your records.</p>
  <p style="margin-top:14px;">Best Regards,<br/>{_html.escape(APP_NAME)}</p>
</div>"""


def _report_message(cfg: dict, to_email: str, subject: str, html_body: str,
                    pdf_bytes: bytes, report_filename: str,
                    csv_bytes: "bytes | None" = None,
                    csv_filename: "str | None" = None) -> MIMEMultipart:
    """Build a single report email for one recipient: HTML body + PDF attachment, plus
    the full findings table as a CSV attachment when provided."""
    msg = MIMEMultipart()
    msg["From"] = f"{cfg['from_name']} <{cfg['user']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    attachment = MIMEBase("application", "pdf")
    attachment.set_payload(pdf_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=report_filename)
    msg.attach(attachment)

    if csv_bytes is not None:
        csv_part = MIMEBase("text", "csv")
        csv_part.set_payload(csv_bytes)
        encoders.encode_base64(csv_part)
        csv_part.add_header("Content-Disposition", "attachment",
                            filename=csv_filename or "threat_findings.csv")
        msg.attach(csv_part)
    return msg


def _report_intro(greeting_name: str) -> str:
    """Shared opening for a report email — the same pattern for the IT Owner and the Admin,
    only the greeting name differs."""
    return (
        f"<p>Dear {_html.escape(greeting_name)},</p>"
        "<p>The security analysis of the uploaded log file(s) has been completed. "
        "A summary of the findings is provided below.</p>"
    )


def send_pdf_report_email(
    to_email,
    username: str,
    pdf_bytes: bytes,
    report_filename: str,
    summary: dict,
    analyzed_files: list[str],
    admin_email: "str | None" = None,
    admin_name: "str | None" = None,
    csv_bytes: "bytes | None" = None,
    csv_filename: "str | None" = None,
    application: str = "",
    leanix_id: str = "",
) -> bool:
    """Email the security report to the uploader and (for IT-Owner uploads) the Administrator.

    Every email greets its recipient by name and attaches the PDF report plus the findings
    CSV (the findings are NOT embedded in the email body — they travel as attachments).

    - The uploader always receives a report addressed to them by name.
    - When an IT Owner uploaded the log, the Administrator additionally receives a
      SEPARATE copy addressed to the Administrator by name (``admin_name``) whose subject
      identifies the IT Owner ("IT Owner : <name> has generated a security report - <date>").
    - When the Administrator is the uploader, only the single uploader email is sent.

    Pass ``admin_email``/``admin_name`` for the Administrator copy; leave them ``None``
    when the Administrator is the uploader. For backward compatibility ``to_email`` may
    also be a list whose first entry is the uploader and second the admin recipient.
    """
    cfg = _get_smtp_config()
    if not cfg:
        logger.warning("SMTP not configured – cannot send PDF report email.")
        return False

    if isinstance(to_email, (list, tuple, set)):
        addrs = [str(a).strip() for a in to_email if a]
        uploader_email = addrs[0] if addrs else ""
        if admin_email is None and len(addrs) > 1:
            admin_email = addrs[1]
    else:
        uploader_email = str(to_email).strip()

    now = now_ist()
    # IT Owner reports carry an Application/Product + LeanIX/PIF ID, so their subject is
    # "[APPLICATION] | [LEANIX/PIF ID]-Log Analysis Report-[Mon DD,YYYY]" (e.g.
    # "AZURE | 2345-Log Analysis Report-Jun 20,2026"). Admin test reports have no context,
    # so the subject is simply "Log Analysis Report-[DD Mon,YYYY]" (e.g. "Log Analysis
    # Report-16 Jun,2026").
    app_part = (application or "").strip().upper()
    id_part = (leanix_id or "").strip()
    if app_part or id_part:
        subject = f"{app_part} | {id_part}-Log Analysis Report-{now.strftime('%b %d,%Y')}"
    else:
        subject = f"Log Analysis Report-{now.strftime('%d %b,%Y')}"

    # 1) Report addressed to the uploader (IT Owner or Administrator), greeted by name.
    uploader_body = _report_html(
        intro=_report_intro(username),
        generated_by=f"{username} ({uploader_email})",
        now=now, summary=summary, analyzed_files=analyzed_files,
        application=application, leanix_id=leanix_id,
    )
    ok_uploader = _send(
        _report_message(cfg, uploader_email, subject, uploader_body, pdf_bytes,
                        report_filename, csv_bytes, csv_filename),
        cfg,
    )

    # 2) Copy addressed to the Administrator (only when an IT Owner uploaded), greeted by
    #    name, with a subject that identifies the IT Owner who generated the report.
    ok_admin = True
    if admin_email and admin_email.strip().lower() != uploader_email.lower():
        admin_body = _report_html(
            intro=_report_intro(admin_name or "Administrator"),
            generated_by=f"{username} ({uploader_email})",
            now=now, summary=summary, analyzed_files=analyzed_files,
            application=application, leanix_id=leanix_id,
        )
        # Admin copy subject is prefixed with the IT Owner's username so the Administrator
        # can tell at a glance who generated it, e.g. "USERX : AZURE | 2345-Log Analysis Report-…".
        admin_subject = f"{username} : {subject}"
        ok_admin = _send(
            _report_message(cfg, admin_email.strip(), admin_subject, admin_body,
                            pdf_bytes, report_filename, csv_bytes, csv_filename),
            cfg,
        )
        if not ok_admin:
            logger.warning("Failed to send admin notification copy to %s", admin_email)

    return ok_uploader and ok_admin
