import logging
import yaml
from sqlalchemy import text

from database.db import get_db, create_all_tables
from database.models import User, DetectionRule, AppMetadata
from config.settings import (
    ADMIN_USERNAME, ADMIN_EMAIL, _ADMIN_INITIAL_PASSWORD,
    DETECTION_RULES_YAML, ROLE_ADMIN, AUDIT_LOG_RETENTION_DAYS, now_ist,
)

_DB_INITIALIZED_KEY = "db_initialized_at"

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create all tables, seed default admin and detection rules. Idempotent."""
    create_all_tables()
    db = get_db()
    try:
        _ensure_rule_columns(db)
        _ensure_audit_columns(db)
        _migrate_dynamic_to_behavioral(db)
        _record_db_initialized(db)
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


# Columns added after the original schema shipped. create_all() only creates missing
# *tables*, never missing *columns*, so an existing cybersec.db needs these added in
# place. ALTER TABLE ADD COLUMN is safe and cheap on SQLite (nullable, no default).
_RULE_COLUMN_DDL = {
    "detection_logic": "TEXT",
    "recommended_action": "TEXT",
    "framework_refs": "VARCHAR(255)",
    "example_log": "TEXT",
    "group_by": "VARCHAR(20)",
    "why_suspicious": "TEXT",
    "security_impact": "TEXT",
    # Existing rows were already live for everyone, so default them to propagated (1).
    "is_propagated": "BOOLEAN NOT NULL DEFAULT 1",
}


def _ensure_rule_columns(db) -> None:
    """Add any missing detection_rules columns to an existing database. Idempotent."""
    rows = db.execute(text("PRAGMA table_info(detection_rules)")).fetchall()
    existing = {row[1] for row in rows}  # row[1] = column name
    for column, ddl_type in _RULE_COLUMN_DDL.items():
        if column not in existing:
            # column/ddl_type come only from the _RULE_COLUMN_DDL constant above — never
            # from user input — so this DDL string is not an injection vector.
            db.execute(text(f"ALTER TABLE detection_rules ADD COLUMN {column} {ddl_type}"))
            logger.info("Added missing column detection_rules.%s", column)


# Columns added to audit_logs after the original schema shipped. Same rationale as
# _RULE_COLUMN_DDL: create_all() never adds missing columns to an existing table.
_AUDIT_COLUMN_DDL = {
    "application": "VARCHAR(150)",
    "leanix_id": "VARCHAR(100)",
}


def _ensure_audit_columns(db) -> None:
    """Add any missing audit_logs columns to an existing database. Idempotent."""
    rows = db.execute(text("PRAGMA table_info(audit_logs)")).fetchall()
    existing = {row[1] for row in rows}  # row[1] = column name
    for column, ddl_type in _AUDIT_COLUMN_DDL.items():
        if column not in existing:
            # column/ddl_type come only from the _AUDIT_COLUMN_DDL constant above — never
            # from user input — so this DDL string is not an injection vector.
            db.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {column} {ddl_type}"))
            logger.info("Added missing column audit_logs.%s", column)


def _migrate_dynamic_to_behavioral(db) -> None:
    """Rename the legacy 'dynamic' rule type to 'behavioral' in place (idempotent).

    The behavioural metric-key prefix on static-stored rules also moves DYNAMIC: ->
    BEHAVIORAL:. Safe to run repeatedly: the WHERE clauses match nothing once migrated.
    """
    db.execute(text("UPDATE detection_rules SET rule_type='behavioral' WHERE rule_type='dynamic'"))
    db.execute(text(
        "UPDATE detection_rules SET condition='BEHAVIORAL:' || substr(condition, 9) "
        "WHERE condition LIKE 'DYNAMIC:%'"
    ))


def _record_db_initialized(db) -> None:
    """Stamp when the database was first created / reseeded (used by the Rules page to
    show when default rules were generated). Set once; never overwritten thereafter."""
    existing = db.query(AppMetadata).filter_by(key=_DB_INITIALIZED_KEY).first()
    if existing is None:
        db.add(AppMetadata(key=_DB_INITIALIZED_KEY, value=now_ist().isoformat(timespec="seconds")))
        logger.info("Recorded database initialization timestamp.")


def get_db_initialized_at(db) -> "str | None":
    """Return the stored DB initialization/reseed timestamp (ISO string) or None."""
    row = db.query(AppMetadata).filter_by(key=_DB_INITIALIZED_KEY).first()
    return row.value if row else None


def _seed_admin(db) -> None:
    from auth.password import hash_password

    existing = db.query(User).filter_by(username=ADMIN_USERNAME).first()
    if existing:
        return

    now = now_ist()
    # password_type="permanent" below is an enum label, not a password value.
    admin = User(  # nosec B106
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

    all_rules = (
        list(data.get("static_rules", []))
        # Accept both keys so an older YAML still seeds; behavioral_rules is canonical now.
        + list(data.get("behavioral_rules", []))
        + list(data.get("dynamic_rules", []))
        + list(data.get("custom_rules", []))
    )
    for rule_data in all_rules:
        existing = db.query(DetectionRule).filter_by(rule_name=rule_data["rule_name"]).first()
        if existing:
            # Refresh ONLY the descriptive / framework metadata so the built-in library
            # stays current. Never touch admin-tuned operational fields (severity,
            # threshold, window, enabled, condition) — those are the operator's to own.
            existing.detection_logic = rule_data.get("detection_logic")
            existing.recommended_action = rule_data.get("recommended_action")
            existing.framework_refs = rule_data.get("framework_refs")
            existing.example_log = rule_data.get("example_log")
            existing.group_by = rule_data.get("group_by")
            existing.why_suspicious = rule_data.get("why_suspicious")
            existing.security_impact = rule_data.get("security_impact")
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
            detection_logic=rule_data.get("detection_logic"),
            recommended_action=rule_data.get("recommended_action"),
            framework_refs=rule_data.get("framework_refs"),
            example_log=rule_data.get("example_log"),
            group_by=rule_data.get("group_by"),
            why_suspicious=rule_data.get("why_suspicious"),
            security_impact=rule_data.get("security_impact"),
            is_propagated=True,  # built-in library is live for every IT Owner out of the box
        )
        db.add(rule)
    logger.info("Detection rules seeded from YAML.")


def get_ruleset_version(db) -> tuple[int, "object | None"]:
    """Return (rule_count, last_updated) used to stamp a rule-set version in the UI.

    All IT Owners read the same shared rule table, so a single derived version
    communicates exactly which configuration is currently active for everyone.
    """
    from sqlalchemy import func

    count = db.query(func.count(DetectionRule.id)).scalar() or 0
    last_updated = db.query(func.max(DetectionRule.updated_at)).scalar()
    return count, last_updated


def _purge_expired_audit_logs(db) -> int:
    import datetime
    from database.models import AuditLog

    cutoff = now_ist() - datetime.timedelta(days=AUDIT_LOG_RETENTION_DAYS)
    deleted = db.query(AuditLog).filter(AuditLog.timestamp < cutoff).delete()
    if deleted:
        logger.info("Purged %d expired audit log entries.", deleted)
    return deleted
