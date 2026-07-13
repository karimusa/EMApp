"""Application login password verification for dbo.users.password_hash."""

from __future__ import annotations

import hashlib
import re

from werkzeug.security import check_password_hash, generate_password_hash

_LEGACY_SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")


def is_legacy_sha256_password_hash(value: str | None) -> bool:
    """Return True when the stored value is a 64-character SHA-256 hex digest."""
    return bool(_LEGACY_SHA256_HEX.match((value or "").strip()))


def legacy_sha256_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest().upper()


def verify_legacy_sha256_password_hash(stored: str, password: str) -> bool:
    return legacy_sha256_password_hash(password) == stored.strip().upper()


def verify_user_password_hash(stored: str | None, password: str) -> bool:
    """Verify a dbo.users password against Werkzeug or legacy SHA-256 storage."""
    stored_value = (stored or "").strip()
    if not stored_value:
        return False
    if is_legacy_sha256_password_hash(stored_value):
        return verify_legacy_sha256_password_hash(stored_value, password)
    return check_password_hash(stored_value, password)


def werkzeug_password_hash(password: str) -> str:
    return generate_password_hash(password)
