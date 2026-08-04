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
# These are audit-action labels (event names), not credentials.
ACTION_PASSWORD_CHANGE = "PASSWORD_CHANGE"  # nosec B105
ACTION_PASSWORD_EXPIRED_CHANGE = "PASSWORD_EXPIRED_CHANGE"  # nosec B105
ACTION_ANALYZE = "LOG_ANALYZE"
ACTION_EMAIL_REPORT = "EMAIL_REPORT"
ACTION_DOWNLOAD_REPORT = "DOWNLOAD_REPORT"
ACTION_RULE_CREATE = "RULE_CREATE"
ACTION_RULE_UPDATE = "RULE_UPDATE"
ACTION_RULE_DELETE = "RULE_DELETE"
ACTION_RULE_TOGGLE = "RULE_TOGGLE"
ACTION_RULE_PROPAGATE = "RULE_PROPAGATE"
ACTION_USER_CREATE = "USER_CREATE"
ACTION_USER_DEACTIVATE = "USER_DEACTIVATE"
ACTION_USER_ACTIVATE = "USER_ACTIVATE"
ACTION_USER_DELETE = "USER_DELETE"
ACTION_SESSION_EXPIRE = "SESSION_EXPIRE"
ACTION_FORGOT_PASSWORD = "FORGOT_PASSWORD"  # nosec B105
ACTION_ADMIN_SETUP = "ADMIN_SETUP"


def log_action(
    user_id: int,
    action: str,
    db,
    ip_address: Optional[str] = None,
    details: Optional[str] = None,
    file_name: Optional[str] = None,
    application: Optional[str] = None,
    leanix_id: Optional[str] = None,
) -> None:
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            timestamp=now_ist(),
            ip_address=ip_address,
            details=details,
            file_name=file_name,
            # Normalise empty strings to NULL so "no context" is consistent in queries.
            application=(application or None) or None,
            leanix_id=(leanix_id or None) or None,
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
    application_filter: Optional[str] = None,
    leanix_filter: Optional[str] = None,
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
    if application_filter:
        q = q.filter(AuditLog.application == application_filter)
    if leanix_filter:
        q = q.filter(AuditLog.leanix_id == leanix_filter)
    return q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()


def get_audit_filter_options(db) -> tuple[list[str], list[str]]:
    """Distinct non-empty Application/Product and LeanIX/PIF values across all audit
    entries, sorted — used to populate the Audit page filter drop-downs."""
    apps = [
        r[0] for r in db.query(AuditLog.application).distinct().all()
        if r[0]
    ]
    leanix = [
        r[0] for r in db.query(AuditLog.leanix_id).distinct().all()
        if r[0]
    ]
    return sorted(set(apps)), sorted(set(leanix))


def get_app_mappings_by_user(db) -> dict[int, list[tuple[str, str]]]:
    """Map each user_id to the distinct (Application/Product, LeanIX/PIF ID) pairs that
    appear in their audit history. A single IT Owner may be responsible for several
    applications, so each user can have multiple mappings."""
    rows = (
        db.query(AuditLog.user_id, AuditLog.application, AuditLog.leanix_id)
        .filter(AuditLog.application.isnot(None))
        .filter(AuditLog.application != "")
        .distinct()
        .all()
    )
    out: dict[int, list[tuple[str, str]]] = {}
    for uid, app, leanix in rows:
        pair = (app, leanix or "")
        bucket = out.setdefault(uid, [])
        if pair not in bucket:
            bucket.append(pair)
    for uid in out:
        out[uid].sort()
    return out


def purge_old_logs(db, retention_days: int = 180) -> int:
    import datetime
    cutoff = now_ist() - datetime.timedelta(days=retention_days)
    deleted = db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
    db.commit()
    return deleted
