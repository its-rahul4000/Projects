import pytest
import datetime

from services.user_service import (
    authenticate, change_password, is_password_expired,
    register_it_owner, get_user_by_username,
)
from database.models import User
from auth.password import hash_password
from config.settings import ROLE_IT_OWNER


def test_authenticate_success(admin_user, db):
    ok, user, msg = authenticate("admin@bosch1211", "Security@bosch#9693261348", db)
    assert ok is True
    assert user is not None
    assert msg == ""


def test_authenticate_wrong_password(admin_user, db):
    ok, user, msg = authenticate("admin@bosch1211", "WrongPassword!!!!!", db)
    assert ok is False
    assert user is None


def test_authenticate_unknown_user(db):
    ok, user, msg = authenticate("nobody", "AnyPassword1234!!XX", db)
    assert ok is False
    assert user is None


def test_authenticate_inactive_user(db):
    user = User(
        username="inactiveuser",
        password_hash=hash_password("SomePass@word12345!XY"),
        email="inactive@example.com",
        role=ROLE_IT_OWNER,
        created_at=datetime.datetime.utcnow(),
        is_active=False,
        password_type="permanent",
        is_first_login=False,
    )
    db.add(user)
    db.commit()
    ok, u, msg = authenticate("inactiveuser", "SomePass@word12345!XY", db)
    assert ok is False
    assert "disabled" in msg.lower()


def test_change_password_success(it_owner_user, db):
    ok, msg = change_password(it_owner_user.id, "NewSecure@Pass!2024XYZ", db)
    assert ok is True
    db.refresh(it_owner_user)
    assert it_owner_user.password_type == "permanent"
    assert it_owner_user.is_first_login is False


def test_change_password_policy_violation(it_owner_user, db):
    ok, msg = change_password(it_owner_user.id, "short", db)
    assert ok is False
    assert "20" in msg or "character" in msg.lower()


def test_change_password_reuse_blocked(it_owner_user, db):
    # Change to a new password – puts original fixture hash into history
    ok, msg = change_password(it_owner_user.id, "FirstNew@Pass!2024XYZ", db)
    assert ok is True
    # Try to reuse the original fixture password (meets policy, should be in history)
    ok2, msg2 = change_password(it_owner_user.id, "TestPass@wordXYZ#2024", db)
    assert ok2 is False
    assert "reuse" in msg2.lower() or "cannot" in msg2.lower() or "differ" in msg2.lower()


def test_is_password_expired_future(it_owner_user):
    assert is_password_expired(it_owner_user) is False


def test_is_password_expired_past(it_owner_user, db):
    it_owner_user.password_expiry = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    db.commit()
    assert is_password_expired(it_owner_user) is True


def test_is_password_expired_admin_never(admin_user):
    assert is_password_expired(admin_user) is False


def test_register_it_owner_duplicate_username(it_owner_user, db):
    ok, msg, _temp = register_it_owner("testowner", "new@example.com", db)
    assert ok is False
    assert "taken" in msg.lower() or "username" in msg.lower()


def test_register_invalid_email(db):
    ok, msg, _temp = register_it_owner("newuser123", "not-an-email", db)
    assert ok is False
    assert "email" in msg.lower()
