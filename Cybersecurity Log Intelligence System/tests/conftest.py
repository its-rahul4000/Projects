import pytest
import datetime
from sqlalchemy.orm import Session as OrmSession

from database.db import get_engine, create_all_tables
from database.models import Base, User, DetectionRule
from auth.password import hash_password
from config.settings import ROLE_ADMIN, ROLE_IT_OWNER


@pytest.fixture(scope="function")
def db_engine():
    engine = get_engine(testing=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db(db_engine):
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=db_engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def admin_user(db):
    user = User(
        username="admin",
        password_hash=hash_password("Cybersecuritylogadmin@12798"),
        email="admin@example.com",
        role=ROLE_ADMIN,
        created_at=datetime.datetime.utcnow(),
        password_changed_at=datetime.datetime.utcnow(),
        is_active=True,
        password_type="permanent",
        is_first_login=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def it_owner_user(db):
    user = User(
        username="testowner",
        password_hash=hash_password("TestPass@wordXYZ#2024"),
        email="owner@example.com",
        role=ROLE_IT_OWNER,
        created_at=datetime.datetime.utcnow(),
        password_changed_at=datetime.datetime.utcnow(),
        password_expiry=datetime.datetime.utcnow() + datetime.timedelta(days=180),
        is_active=True,
        password_type="permanent",
        is_first_login=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_static_rule(db, admin_user):
    rule = DetectionRule(
        rule_name="Test SQL Injection",
        rule_type="static",
        condition=r"(?i)(union\s+select|drop\s+table)",
        severity="HIGH",
        description="Test rule",
        is_static=True,
        default_threshold=None,
        time_window_seconds=None,
        is_enabled=True,
        created_by=admin_user.id,
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
