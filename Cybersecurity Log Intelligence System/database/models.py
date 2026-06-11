import datetime
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Text, ForeignKey, event
)


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
        DateTime, nullable=False, default=datetime.datetime.utcnow
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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    last_activity: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    expiry_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    append_used: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="password_history")


class DetectionRule(Base):
    __tablename__ = "detection_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "static" | "dynamic"
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # CRITICAL|HIGH|MEDIUM|LOW|INFO
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_static: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_window_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )
