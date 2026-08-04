import logging
from typing import Optional

import datetime

from database.models import User, PasswordHistory, PendingRegistration
from auth.password import hash_password, verify_password, validate_policy, generate_temp_password, is_in_history
from auth.session_manager import invalidate_all_user_sessions
from services.email_service import send_temp_password_email
from services.audit_service import (
    log_action, ACTION_REGISTER, ACTION_USER_DEACTIVATE, ACTION_USER_ACTIVATE,
    ACTION_USER_DELETE, ACTION_FORGOT_PASSWORD,
)
from utils.validators import sanitize_username, validate_email_address
from config.settings import ROLE_IT_OWNER, PASSWORD_EXPIRY_DAYS, PASSWORD_HISTORY_DEPTH, now_ist

# A started-but-not-activated registration is discarded after this many days.
PENDING_REGISTRATION_TTL_DAYS = 7

logger = logging.getLogger(__name__)


def get_user_by_username(username: str, db) -> Optional[User]:
    return db.query(User).filter_by(username=username).first()


def get_user_by_id(user_id: int, db) -> Optional[User]:
    return db.query(User).filter_by(id=user_id).first()


def get_all_users(db) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def authenticate(username: str, password: str, db) -> tuple[bool, Optional[User], str]:
    clean_username = sanitize_username(username)
    user = get_user_by_username(clean_username, db)
    if not user:
        return False, None, "Invalid username or password."
    if not user.is_active:
        return False, None, "Account is disabled. Contact your Administrator."
    if not verify_password(password, user.password_hash):
        return False, None, "Invalid username or password."
    return True, user, ""


def _purge_stale_pending(db) -> None:
    cutoff = now_ist() - datetime.timedelta(days=PENDING_REGISTRATION_TTL_DAYS)
    db.query(PendingRegistration).filter(PendingRegistration.created_at < cutoff).delete(
        synchronize_session=False
    )


def register_it_owner(username: str, email: str, db) -> tuple[bool, str, str | None]:
    """Start an IT Owner registration.

    No account is created here — a temporary password is generated and a *pending*
    registration is recorded. The account is created only once the registrant signs
    in with the temporary password and sets their own permanent password
    (see complete_pending_registration).

    Returns (success, message, temp_password). temp_password is only set when email
    delivery is unavailable, so it can be shown on screen as a fallback.
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

    _purge_stale_pending(db)
    # Replace any earlier unfinished registration for this username/email so a user
    # who lost their temporary password can simply register again.
    db.query(PendingRegistration).filter(
        (PendingRegistration.username == clean_username)
        | (PendingRegistration.email == clean_email)
    ).delete(synchronize_session=False)

    temp_password = generate_temp_password()
    db.add(PendingRegistration(
        username=clean_username,
        email=clean_email,
        temp_password_hash=hash_password(temp_password),
        created_at=now_ist(),
    ))
    db.commit()

    email_sent = send_temp_password_email(clean_email, clean_username, temp_password)
    if not email_sent:
        return (
            True,
            "Registration received. Use the temporary password below to sign in and set "
            "your permanent password — your account is activated once you do.",
            temp_password,
        )

    # Email delivered: never reveal the password on screen.
    return (
        True,
        "Registration received. A temporary password has been sent to your email address — "
        "sign in with it to set your password and activate your account.",
        None,
    )


def find_pending_registration(username: str, password: str, db) -> Optional[PendingRegistration]:
    """Return the pending registration matching the username + temporary password,
    or None. Used by the login flow to route a not-yet-activated registrant to set
    their permanent password."""
    pending = db.query(PendingRegistration).filter_by(
        username=sanitize_username(username)
    ).first()
    if not pending or not verify_password(password, pending.temp_password_hash):
        return None
    return pending


def complete_pending_registration(username: str, new_password: str, db) -> tuple[bool, str, Optional[User]]:
    """Create the real IT Owner account from a pending registration once the user
    sets a permanent password. Returns (success, message, user)."""
    valid, violations = validate_policy(new_password)
    if not valid:
        return False, " ".join(violations), None

    clean = sanitize_username(username)
    pending = db.query(PendingRegistration).filter_by(username=clean).first()
    if not pending:
        return False, "Your registration session has expired. Please register again.", None

    if db.query(User).filter_by(username=clean).first():
        db.delete(pending)
        db.commit()
        return False, "This account already exists. Please sign in normally.", None

    now = now_ist()
    # password_type="permanent" below is an enum label, not a password value.
    user = User(  # nosec B106
        username=pending.username,
        password_hash=hash_password(new_password),
        email=pending.email,
        role=ROLE_IT_OWNER,
        created_at=now,
        password_changed_at=now,
        password_expiry=now + datetime.timedelta(days=PASSWORD_EXPIRY_DAYS),
        is_active=True,
        password_type="permanent",
        is_first_login=False,
    )
    db.add(user)
    db.delete(pending)
    db.commit()
    db.refresh(user)

    log_action(user.id, ACTION_REGISTER, db, details=f"IT Owner account activated: {user.username}")
    return True, "Account created successfully.", user


def forgot_password(identifier: str, db) -> tuple[bool, str, str | None, str | None]:
    """
    Look up a user by username or email, generate a new temp password, email it.
    Returns (success, message, temp_password, username).
    temp_password is only set when email could not be sent (so it can be shown on
    screen as a fallback); it is None when the email was delivered. username is the
    resolved account username (for pre-filling the login form), or None on failure.
    """
    from services.email_service import send_forgot_password_email

    clean = identifier.strip()
    # Try username first, then email
    user = get_user_by_username(sanitize_username(clean), db)
    if not user:
        user = db.query(User).filter_by(email=clean.lower()).first()

    if not user:
        return False, "No account found with that username or email address.", None, None
    if not user.is_active:
        return False, "This account is disabled. Please contact your Administrator.", None, None

    temp_password = generate_temp_password()
    now = now_ist()
    user.password_hash = hash_password(temp_password)
    user.password_type = "temporary"  # nosec B105
    user.is_first_login = True
    user.password_changed_at = now
    db.commit()

    log_action(user.id, ACTION_FORGOT_PASSWORD, db,
               details=f"Password reset requested for {user.username}")

    sent = send_forgot_password_email(user.email, user.username, temp_password)
    if not sent:
        # Email is not configured (or delivery failed) — surface the temp password
        # on screen as a fallback so the user can still regain access.
        logger.warning("Forgot-password email not sent for %s (%s); showing on screen",
                       user.username, user.email)
        return (
            True,
            "Use the temporary password shown below to log in. "
            "You will be prompted to set a new permanent password.",
            temp_password,
            user.username,
        )

    return (
        True,
        "A temporary password has been sent to your registered email address. "
        "Please check your inbox (and junk folder). You will be prompted to set a new password on login.",
        None,
        user.username,
    )


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

    now = now_ist()
    history_entry = PasswordHistory(
        user_id=user_id, password_hash=user.password_hash, created_at=now
    )
    db.add(history_entry)

    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    user.password_type = "permanent"  # nosec B105
    user.is_first_login = False

    if user.role == ROLE_IT_OWNER:
        import datetime
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
    return now_ist() > user.password_expiry


def set_user_active(user_id: int, active: bool, db, actor_id: int) -> bool:
    user = get_user_by_id(user_id, db)
    if not user:
        return False
    user.is_active = active
    db.commit()
    action = ACTION_USER_ACTIVATE if active else ACTION_USER_DEACTIVATE
    log_action(actor_id, action, db,
               details=f"User {user.username} {'activated' if active else 'deactivated'}.")
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
