import logging
import yaml

from database.db import get_db, create_all_tables
from database.models import User, DetectionRule
from config.settings import (
    ADMIN_USERNAME, ADMIN_EMAIL, _ADMIN_INITIAL_PASSWORD,
    DETECTION_RULES_YAML, ROLE_ADMIN, AUDIT_LOG_RETENTION_DAYS, now_ist,
)

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all tables, seed default admin and detection rules. Idempotent."""
    create_all_tables()
    db = get_db()
    try:
        _purge_expired_audit_logs(db)
        _seed_admin(db)
        _seed_detection_rules(db)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Database initialisation failed")
        raise
    finally:
        db.close()


def _seed_admin(db) -> None:
    from auth.password import hash_password

    existing = db.query(User).filter_by(username=ADMIN_USERNAME).first()
    if existing:
        return

    now = now_ist()
    admin = User(
        username=ADMIN_USERNAME,
        password_hash=hash_password(_ADMIN_INITIAL_PASSWORD),
        email=ADMIN_EMAIL,
        role=ROLE_ADMIN,
        created_at=now,
        password_changed_at=now,
        password_expiry=None,
        is_active=True,
        password_type="permanent",
        is_first_login=True,  # triggers recovery-email setup on first login
    )
    db.add(admin)
    logger.info("Default admin account created.")


def _seed_detection_rules(db) -> None:
    try:
        with open(DETECTION_RULES_YAML, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        logger.warning("detection_rules.yaml not found – skipping rule seeding.")
        return

    all_rules = list(data.get("static_rules", [])) + list(data.get("dynamic_rules", []))
    for rule_data in all_rules:
        existing = db.query(DetectionRule).filter_by(rule_name=rule_data["rule_name"]).first()
        if existing:
            continue
        rule = DetectionRule(
            rule_name=rule_data["rule_name"],
            rule_type=rule_data["rule_type"],
            condition=rule_data["condition"],
            severity=rule_data["severity"].upper(),
            description=rule_data.get("description"),
            is_static=rule_data.get("is_static", True),
            default_threshold=rule_data.get("default_threshold"),
            time_window_seconds=rule_data.get("time_window_seconds"),
            is_enabled=rule_data.get("is_enabled", True),
        )
        db.add(rule)
    logger.info("Detection rules seeded from YAML.")


def _purge_expired_audit_logs(db) -> int:
    import datetime
    from database.models import AuditLog

    cutoff = now_ist() - datetime.timedelta(days=AUDIT_LOG_RETENTION_DAYS)
    deleted = db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
    if deleted:
        logger.info("Purged %d expired audit log entries.", deleted)
    return deleted
