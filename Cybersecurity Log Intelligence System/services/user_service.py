import datetime
import logging
from typing import Optional

from database.models import User, PasswordHistory
from auth.password import hash_password, verify_password, validate_policy, generate_temp_password, is_in_history
from auth.session_manager import invalidate_all_user_sessions
from services.email_service import send_temp_password_email
from services.audit_service import log_action, ACTION_REGISTER, ACTION_USER_DEACTIVATE, ACTION_USER_ACTIVATE, ACTION_USER_DELETE
from utils.validators import sanitize_username, validate_email_address
from config.settings import ROLE_IT_OWNER, PASSWORD_EXPIRY_DAYS, PASSWORD_HISTORY_DEPTH

logger = logging.getLogger(__name__)


def get_user_by_username(username: str, db) -> Optional[User]:
    return db.query(User).filter_by(username=username).first()


def get_user_by_id(user_id: int, db) -> Optional[User]:
    return db.query(User).filter_by(id=user_id).first()


def get_all_users(db) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def authenticate(username: str, password: str, db) -> tuple[bool, Optional[User], str]:
    """
    Returns (success, user, error_message).
    success=True means credentials are valid and user is active.
    """
    clean_username = sanitize_username(username)
    user = get_user_by_username(clean_username, db)
    if not user:
        return False, None, "Invalid username or password."
    if not user.is_active:
        return False, None, "Account is disabled. Contact your Administrator."
    if not verify_password(password, user.password_hash):
        return False, None, "Invalid username or password."
    return True, user, ""


def register_it_owner(username: str, email: str, db) -> tuple[bool, str, str | None]:
    """
    Returns (success, message, temp_password).
    temp_password is set only when the account was created but the email failed to send.
    The caller must display it securely so the admin can relay it to the new user.
    """
    clean_username = sanitize_username(username)
    clean_email = email.strip().lower()

    if not clean_username:
        return False, "Username is required.", None
    if len(clean_username) < 3:
        return False, "Username must be at least 3 characters.", None
    if not validate_email_address(clean_email):
        return False, "Invalid email address.", None

    if db.query(User).filter_by(username=clean_username).first():
        return False, "Username already taken. Please choose a different one.", None
    if db.query(User).filter_by(email=clean_email).first():
        return False, "Email address already registered.", None

    temp_password = generate_temp_password()
    now = datetime.datetime.utcnow()

    user = User(
        username=clean_username,
        password_hash=hash_password(temp_password),
        email=clean_email,
        role=ROLE_IT_OWNER,
        created_at=now,
        password_changed_at=now,
        password_expiry=None,
        is_active=True,
        password_type="temporary",
        is_first_login=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(user.id, ACTION_REGISTER, db, details=f"IT Owner registered: {clean_username}")

    email_sent = send_temp_password_email(clean_email, clean_username, temp_password)
    if not email_sent:
        logger.warning("Temp password email could not be sent to %s", clean_email)
        return (
            True,
            "Account created successfully! Email delivery failed — the temporary password is shown below. "
            "Please share it securely with the new user.",
            temp_password,
        )

    return True, "Account created! A temporary password has been sent to the user's email address.", None


def change_password(
    user_id: int,
    new_password: str,
    db,
    action_label: str = "PASSWORD_CHANGE",
) -> tuple[bool, str]:
    valid, violations = validate_policy(new_password)
    if not valid:
        return False, " ".join(violations)

    user = get_user_by_id(user_id, db)
    if not user:
        return False, "User not found."

    history = (
        db.query(PasswordHistory)
        .filter_by(user_id=user_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(PASSWORD_HISTORY_DEPTH)
        .all()
    )
    if is_in_history(new_password, [h.password_hash for h in history]):
        return False, f"Cannot reuse any of your last {PASSWORD_HISTORY_DEPTH} passwords."

    if verify_password(new_password, user.password_hash):
        return False, "New password must differ from the current password."

    history_entry = PasswordHistory(
        user_id=user_id, password_hash=user.password_hash, created_at=datetime.datetime.utcnow()
    )
    db.add(history_entry)

    now = datetime.datetime.utcnow()
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.password_type = "permanent"
    user.is_first_login = False

    if user.role == ROLE_IT_OWNER:
        user.password_expiry = now + datetime.timedelta(days=PASSWORD_EXPIRY_DAYS)
    else:
        user.password_expiry = None

    db.commit()
    invalidate_all_user_sessions(user_id, db)
    log_action(user_id, action_label, db, details="Password changed successfully.")
    return True, "Password changed successfully."


def is_password_expired(user: User) -> bool:
    if user.password_expiry is None:
        return False
    return datetime.datetime.utcnow() > user.password_expiry


def set_user_active(user_id: int, active: bool, db, actor_id: int) -> bool:
    user = get_user_by_id(user_id, db)
    if not user:
        return False
    user.is_active = active
    db.commit()
    action = ACTION_USER_ACTIVATE if active else ACTION_USER_DEACTIVATE
    log_action(actor_id, action, db, details=f"User {user.username} {'activated' if active else 'deactivated'}.")
    if not active:
        invalidate_all_user_sessions(user_id, db)
    return True


def delete_user(user_id: int, db, actor_id: int) -> tuple[bool, str]:
    user = get_user_by_id(user_id, db)
    if not user:
        return False, "User not found."
    if user.id == actor_id:
        return False, "Cannot delete your own account."
    username = user.username
    invalidate_all_user_sessions(user_id, db)
    db.delete(user)
    db.commit()
    log_action(actor_id, ACTION_USER_DELETE, db, details=f"Deleted user: {username}")
    return True, f"User '{username}' deleted."
