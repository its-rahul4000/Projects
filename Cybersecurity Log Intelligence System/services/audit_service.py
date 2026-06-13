import datetime
import logging
from typing import Optional

from database.models import AuditLog
from config.settings import now_ist

logger = logging.getLogger(__name__)

# Audit action constants
ACTION_LOGIN = "LOGIN"
ACTION_LOGIN_FAILED = "LOGIN_FAILED"
ACTION_LOGOUT = "LOGOUT"
ACTION_REGISTER = "REGISTER"
ACTION_PASSWORD_CHANGE = "PASSWORD_CHANGE"
ACTION_PASSWORD_EXPIRED_CHANGE = "PASSWORD_EXPIRED_CHANGE"
ACTION_ANALYZE = "LOG_ANALYZE"
ACTION_EMAIL_REPORT = "EMAIL_REPORT"
ACTION_DOWNLOAD_REPORT = "DOWNLOAD_REPORT"
ACTION_RULE_CREATE = "RULE_CREATE"
ACTION_RULE_UPDATE = "RULE_UPDATE"
ACTION_RULE_DELETE = "RULE_DELETE"
ACTION_RULE_TOGGLE = "RULE_TOGGLE"
ACTION_USER_CREATE = "USER_CREATE"
ACTION_USER_DEACTIVATE = "USER_DEACTIVATE"
ACTION_USER_ACTIVATE = "USER_ACTIVATE"
ACTION_USER_DELETE = "USER_DELETE"
ACTION_SESSION_EXPIRE = "SESSION_EXPIRE"
ACTION_FORGOT_PASSWORD = "FORGOT_PASSWORD"
ACTION_ADMIN_SETUP = "ADMIN_SETUP"


def log_action(
    user_id: int,
    action: str,
    db,
    ip_address: Optional[str] = None,
    details: Optional[str] = None,
    file_name: Optional[str] = None,
    append_used: Optional[bool] = None,
) -> None:
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            timestamp=now_ist(),
            ip_address=ip_address,
            details=details,
            file_name=file_name,
            append_used=append_used,
        )
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to write audit log entry for action=%s user=%s", action, user_id)


def get_audit_logs(
    db,
    user_id: Optional[int] = None,
    action_filter: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    limit: int = 500,
    offset: int = 0,
) -> list[AuditLog]:
    q = db.query(AuditLog)
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action_filter:
        q = q.filter(AuditLog.action == action_filter)
    if start_date:
        q = q.filter(AuditLog.timestamp >= start_date)
    if end_date:
        q = q.filter(AuditLog.timestamp <= end_date)
    return q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()


def purge_old_logs(db, retention_days: int = 180) -> int:
    import datetime
    cutoff = now_ist() - datetime.timedelta(days=retention_days)
    deleted = db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
    db.commit()
    return deleted
