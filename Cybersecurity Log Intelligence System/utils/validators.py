import re
from pathlib import Path
from email_validator import validate_email, EmailNotValidError

from config.settings import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB


def sanitize_username(value: str) -> str:
    """Strip whitespace and restrict to safe characters."""
    value = value.strip()
    value = re.sub(r"[^\w@.\-]", "", value)
    return value[:100]


def sanitize_text(value: str, max_len: int = 1000) -> str:
    """Remove null bytes and non-printable chars; truncate."""
    value = value.replace("\x00", "").strip()
    value = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
    return value[:max_len]


def validate_email_address(email: str) -> bool:
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validate_file_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def validate_file_size(file_bytes: bytes) -> bool:
    return len(file_bytes) <= MAX_UPLOAD_SIZE_MB * 1024 * 1024


def validate_rule_condition(condition: str) -> tuple[bool, str]:
    """Validate that a static rule condition is a compilable regex (or a known DYNAMIC: key)."""
    if condition.startswith("DYNAMIC:"):
        return True, ""
    try:
        re.compile(condition)
        return True, ""
    except re.error as exc:
        return False, f"Invalid regex pattern: {exc}"
