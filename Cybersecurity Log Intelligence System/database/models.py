import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, ForeignKey, event
)
from config.settings import now_ist


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="it_owner")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=now_ist
    )
    password_changed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    password_expiry: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    last_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    password_type: Mapped[str] = mapped_column(String(20), nullable=False, default="temporary")
    is_first_login: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    password_history: Mapped[list["PasswordHistory"]] = relationship(
        "PasswordHistory", back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=now_ist)
    last_activity: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=now_ist)
    expiry_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=now_ist, index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Application/Product + LeanIX/PIF identifier the action was performed under. Captured
    # on the Home page for analysis/report actions; NULL for actions without that context
    # (login, password change, etc.). Nullable → safe ALTER on existing databases.
    application: Mapped[Optional[str]] = mapped_column(String(150), nullable=True, index=True)
    leanix_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=now_ist
    )

    user: Mapped["User"] = relationship("User", back_populates="password_history")


class PendingRegistration(Base):
    """An IT Owner registration that has been started but not yet activated.

    No real user account exists until the registrant signs in with the temporary
    password and sets their own permanent password — at which point a User row is
    created and the pending record is removed. This prevents half-finished
    registrations from creating live accounts.
    """
    __tablename__ = "pending_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    temp_password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=now_ist)


class DetectionRule(Base):
    __tablename__ = "detection_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_static: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_window_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Presentation / framework metadata (data-driven rule cards). Nullable so existing
    # databases upgrade cleanly via _ensure_rule_columns (ALTER TABLE ADD COLUMN).
    detection_logic: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # how/when it fires
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # concise (<=2 lines)
    framework_refs: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # MITRE / NIST / ISO / CERT-In
    example_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)           # representative log line
    # Generic no-code engine aggregation: "source_ip" | "username" | "global" | None.
    group_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Operator-authored detail shown on the rule card (so admin custom rules match the
    # built-in library's presentation). Nullable → safe ALTER on existing databases.
    why_suspicious: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    security_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Staging / propagation: a rule that an admin has created or edited is "staged" —
    # used only in the admin's own Home analysis — until it is propagated to all IT
    # Owners. Built-in seeded rules ship already propagated.
    is_propagated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=now_ist
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=now_ist, onupdate=now_ist
    )


class AppMetadata(Base):
    """Tiny key/value store for application-level metadata.

    Currently records ``db_initialized_at`` — the timestamp the database was first
    created / reseeded — so the Rules page can show when default rules were generated.
    """
    __tablename__ = "app_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
