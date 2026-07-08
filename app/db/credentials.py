"""Resolve SQL login passwords for orchestration.app_connections.

``dbo.users.password_hash`` stores one-way application login hashes (Werkzeug).
Runtime SQL connections must use the real SQL Server login password, stored as:

* ``sql_password_encrypted`` — Fernet ciphertext (recommended) or plain text (dev only)
* ``sql_password_hash`` — legacy column name; never store SHA/bcrypt hashes here
"""

from __future__ import annotations

import re
from typing import Any

from app.db.crypto import decrypt_password

_ONE_WAY_HASH_PATTERNS = (
    re.compile(r"^[0-9a-fA-F]{64}$"),  # SHA-256 hex
    re.compile(r"^[0-9a-fA-F]{40}$"),  # SHA-1 hex
    re.compile(r"^pbkdf2:", re.IGNORECASE),
    re.compile(r"^scrypt:", re.IGNORECASE),
    re.compile(r"^\$2[aby]\$"),
)

_FERNET_PATTERN = re.compile(r"^gAAAAA[A-Za-z0-9_-]+$")


class ConnectionCredentialError(ValueError):
    """Runtime connection credentials are missing or misconfigured."""


def is_one_way_hash(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    return any(pattern.match(text) for pattern in _ONE_WAY_HASH_PATTERNS)


def is_fernet_ciphertext(value: str | None) -> bool:
    text = (value or "").strip()
    return bool(text and _FERNET_PATTERN.match(text))


def stored_credential_from_row(row: dict[str, Any]) -> str | None:
    """Prefer sql_password_encrypted; fall back to legacy sql_password_hash."""
    encrypted = (row.get("sql_password_encrypted") or "").strip()
    legacy = (row.get("sql_password_hash") or "").strip()
    value = encrypted or legacy
    return value or None


def _normalize_sql_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def matches_bootstrap_target(
    server_name: str,
    database_name: str,
    sql_username: str,
    config: dict,
) -> bool:
    return (
        _normalize_sql_identifier(server_name)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_SERVER"))
        and _normalize_sql_identifier(database_name)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_DATABASE"))
        and _normalize_sql_identifier(sql_username)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_USER"))
    )


def resolve_sql_login_password(
    stored_credential: str | None,
    *,
    secret_key: str,
    environment_name: str,
    server_name: str = "",
    database_name: str = "",
    sql_username: str = "",
    config: dict | None = None,
) -> str:
    """Return a SQL Server login password or raise ConnectionCredentialError."""
    raw = (stored_credential or "").strip()
    env = environment_name or "connection"

    if not raw:
        if config and matches_bootstrap_target(
            server_name, database_name, sql_username, config
        ):
            bootstrap_password = (config.get("BOOTSTRAP_PASSWORD") or "").strip()
            if bootstrap_password:
                return bootstrap_password
        raise ConnectionCredentialError(
            f"{env}: no SQL login password configured. "
            "Set orchestration.app_connections.sql_password_encrypted to the SQL "
            "login password (plain text for development) or a Fernet ciphertext from "
            "scripts/encrypt_password.py."
        )

    if is_one_way_hash(raw):
        raise ConnectionCredentialError(
            f"{env}: orchestration.app_connections stores a one-way hash "
            f"({raw[:8]}…), which cannot be used for SQL Server authentication. "
            "Replace it with the real SQL login password or Fernet ciphertext in "
            "sql_password_encrypted. One-way hashes belong only in dbo.users.password_hash."
        )

    if is_fernet_ciphertext(raw):
        if not (secret_key or "").strip():
            raise ConnectionCredentialError(
                f"{env}: sql_password_encrypted is Fernet-encrypted but "
                "CONNECTION_SECRET_KEY is not set in .env."
            )
        password = decrypt_password(raw, secret_key)
        if not password:
            raise ConnectionCredentialError(
                f"{env}: could not decrypt sql_password_encrypted. "
                "Verify CONNECTION_SECRET_KEY matches the key used by "
                "scripts/encrypt_password.py."
            )
        return password

    return raw
