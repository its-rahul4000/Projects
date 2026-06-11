import re
import secrets
import string
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from config.settings import PASSWORD_MIN_LENGTH, TEMP_PASSWORD_LENGTH

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def validate_policy(password: str) -> tuple[bool, list[str]]:
    """Return (is_valid, list_of_violation_messages)."""
    violations = []
    if len(password) < PASSWORD_MIN_LENGTH:
        violations.append(f"At least {PASSWORD_MIN_LENGTH} characters required.")
    if not re.search(r"[A-Z]", password):
        violations.append("At least one uppercase letter required.")
    if not re.search(r"[a-z]", password):
        violations.append("At least one lowercase letter required.")
    if not re.search(r"\d", password):
        violations.append("At least one digit required.")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:'\",.<>?/`~\\]", password):
        violations.append("At least one special character required.")
    return len(violations) == 0, violations


def is_in_history(plain: str, history_hashes: list[str]) -> bool:
    """Return True if the plain password matches any previously used hash."""
    for old_hash in history_hashes:
        try:
            if _ph.verify(old_hash, plain):
                return True
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            continue
    return False


def generate_temp_password() -> str:
    """Generate a cryptographically random password that satisfies the policy."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.?/"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(TEMP_PASSWORD_LENGTH))
        valid, _ = validate_policy(pwd)
        if valid:
            return pwd
