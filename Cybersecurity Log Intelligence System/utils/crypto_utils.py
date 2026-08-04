import hashlib
import os
import secrets
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config.settings import ENV_SECRET_KEY


def _get_secret_key() -> str:
    key = os.getenv(ENV_SECRET_KEY)
    if not key:
        key = secrets.token_hex(32)
    return key


def generate_session_token() -> str:
    """Return a 64-char cryptographically secure hex token."""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """Return SHA-256 hex digest of the token (stored in DB)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token(session_token: str) -> str:
    s = URLSafeTimedSerializer(_get_secret_key())
    return s.dumps(hash_token(session_token), salt="csrf")


def validate_csrf_token(csrf_token: str, session_token: str, max_age: int = 3600) -> bool:
    s = URLSafeTimedSerializer(_get_secret_key())
    try:
        stored_hash = s.loads(csrf_token, salt="csrf", max_age=max_age)
        return stored_hash == hash_token(session_token)
    except (BadSignature, SignatureExpired):
        return False
