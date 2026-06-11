import datetime
import logging
import streamlit as st

from database.models import Session, User
from utils.crypto_utils import generate_session_token, hash_token
from config.settings import SESSION_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def create_session(user_id: int, db) -> str:
    """Create a DB session record. Returns the raw token (stored only in st.session_state)."""
    raw_token = generate_session_token()
    token_hash = hash_token(raw_token)
    now = datetime.datetime.utcnow()
    session = Session(
        user_id=user_id,
        session_token_hash=token_hash,
        created_at=now,
        last_activity=now,
        expiry_time=now + datetime.timedelta(seconds=SESSION_TIMEOUT_SECONDS),
    )
    db.add(session)
    db.commit()
    return raw_token


def validate_session(raw_token: str, db) -> tuple[bool, "User | None"]:
    """Check if the token is valid and not expired. Refreshes last_activity if valid."""
    token_hash = hash_token(raw_token)
    session = db.query(Session).filter_by(session_token_hash=token_hash).first()
    if not session:
        return False, None

    now = datetime.datetime.utcnow()
    if now > session.expiry_time:
        _delete_session(session, db)
        return False, None

    session.last_activity = now
    session.expiry_time = now + datetime.timedelta(seconds=SESSION_TIMEOUT_SECONDS)
    db.commit()

    user = db.query(User).filter_by(id=session.user_id).first()
    if not user or not user.is_active:
        _delete_session(session, db)
        return False, None

    return True, user


def invalidate_session(raw_token: str, db) -> None:
    token_hash = hash_token(raw_token)
    session = db.query(Session).filter_by(session_token_hash=token_hash).first()
    if session:
        _delete_session(session, db)


def invalidate_all_user_sessions(user_id: int, db) -> None:
    db.query(Session).filter_by(user_id=user_id).delete()
    db.commit()


def cleanup_expired_sessions(db) -> int:
    now = datetime.datetime.utcnow()
    deleted = db.query(Session).filter(Session.expiry_time < now).delete()
    db.commit()
    return deleted


def validate_and_refresh(db) -> "User | None":
    """
    Called at the top of every Streamlit rerun.
    Reads the token from st.session_state, validates it, returns User or None.
    On timeout, clears all session state and schedules a rerun.
    """
    raw_token = st.session_state.get("session_token")
    if not raw_token:
        return None

    valid, user = validate_session(raw_token, db)
    if not valid:
        _clear_streamlit_session()
        return None

    return user


def _delete_session(session: Session, db) -> None:
    db.delete(session)
    db.commit()


def _clear_streamlit_session() -> None:
    keys_to_clear = [
        "session_token", "current_user_id", "page",
        "analysis_results", "log_df", "analyzed_files",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
