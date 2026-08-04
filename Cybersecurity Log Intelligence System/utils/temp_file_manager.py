import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# module-level registry: {session_token_hash: [filepath, ...]}
_registry: dict[str, list[str]] = {}


def register_temp_file(session_key: str, path: str) -> None:
    _registry.setdefault(session_key, []).append(path)


def cleanup_session_files(session_key: str) -> None:
    paths = _registry.pop(session_key, [])
    for path in paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
                logger.debug("Deleted temp file: %s", path)
        except OSError as exc:
            logger.warning("Could not delete temp file %s: %s", path, exc)


def cleanup_all_temp_files() -> None:
    for key in list(_registry.keys()):
        cleanup_session_files(key)


def save_upload_to_temp(file_bytes: bytes, suffix: str) -> str:
    """Write bytes to a temp file and return the file path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(file_bytes)
    except Exception:
        os.close(fd)
        raise
    return path
