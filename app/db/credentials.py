"""Resolve SQL login passwords for orchestration.app_connections.

``dbo.users.password_hash`` stores one-way application login hashes (Werkzeug).
Runtime SQL connections must use the real SQL Server login password, stored as:

* ``sql_password_encrypted`` — Fernet ciphertext (recommended) or plain text (dev only)
* ``sql_password_hash`` — legacy column name; never store SHA/bcrypt hashes here
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.db.crypto import decrypt_password

logger = logging.getLogger(__name__)

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
    text = _normalize_credential_text(value)
    if not text:
        return False
    if any(pattern.match(text) for pattern in _ONE_WAY_HASH_PATTERNS):
        return True
    compact = re.sub(r"[^0-9a-fA-F]", "", text)
    return len(compact) in {40, 64, 128} and compact == text


def _normalize_credential_text(value: str | None) -> str:
    text = (value or "").strip().lstrip("\ufeff")
    if text.lower().startswith("0x"):
        text = text[2:].strip()
    return re.sub(r"\s+", "", text)


def is_fernet_ciphertext(value: str | None) -> bool:
    text = (value or "").strip()
    return bool(text and _FERNET_PATTERN.match(text))


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    return str(value).strip()


def stored_credential_from_row(row: dict[str, Any]) -> str | None:
    """Prefer sql_password_encrypted; fall back to legacy sql_password_hash."""
    encrypted = _coerce_text(row.get("sql_password_encrypted"))
    legacy = _coerce_text(row.get("sql_password_hash"))

    if encrypted and not is_one_way_hash(encrypted):
        return encrypted
    if legacy:
        return legacy
    if encrypted:
        return encrypted
    return None


def is_unusable_stored_credential(
    stored_credential: str | None,
    *,
    secret_key: str,
) -> bool:
    if not _coerce_text(stored_credential):
        return True
    if is_one_way_hash(stored_credential):
        return True
    stored_value = _coerce_text(stored_credential)
    if is_fernet_ciphertext(stored_value):
        if not (secret_key or "").strip():
            return True
        return not decrypt_password(stored_value, secret_key)
    return False


def _normalize_sql_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def _normalize_server_name(value: str | None) -> str:
    """Compare SQL Server host names without instance or port suffixes."""
    server = _normalize_sql_identifier(value)
    if "\\" in server:
        server = server.split("\\", 1)[0]
    if "," in server:
        server = server.split(",", 1)[0]
    return server


def matches_bootstrap_target(
    server_name: str,
    database_name: str,
    sql_username: str,
    config: dict,
) -> bool:
    bootstrap_user = (config.get("BOOTSTRAP_USER") or "").strip()
    runtime_user = (sql_username or "").strip()
    if runtime_user and bootstrap_user:
        users_match = _normalize_sql_identifier(runtime_user) == _normalize_sql_identifier(
            bootstrap_user
        )
    else:
        users_match = not runtime_user or not bootstrap_user

    return (
        _normalize_server_name(server_name)
        == _normalize_server_name(config.get("BOOTSTRAP_SERVER"))
        and _normalize_sql_identifier(database_name)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_DATABASE"))
        and users_match
    )


def bootstrap_password_fallback(
    *,
    server_name: str,
    database_name: str,
    sql_username: str,
    config: dict | None,
) -> str | None:
    if not config or not matches_bootstrap_target(
        server_name, database_name, sql_username, config
    ):
        return None
    bootstrap_password = (config.get("BOOTSTRAP_PASSWORD") or "").strip()
    return bootstrap_password or None


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
    env = environment_name or "connection"
    fallback = bootstrap_password_fallback(
        server_name=server_name,
        database_name=database_name,
        sql_username=sql_username,
        config=config,
    )

    if fallback and is_unusable_stored_credential(
        stored_credential, secret_key=secret_key
    ):
        logger.info("%s: using BOOTSTRAP_PASSWORD for runtime SQL connection", env)
        return fallback

    raw = _normalize_credential_text(stored_credential)
    if not raw:
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

    stored_value = _coerce_text(stored_credential)
    if is_fernet_ciphertext(stored_value):
        if not (secret_key or "").strip():
            raise ConnectionCredentialError(
                f"{env}: sql_password_encrypted is Fernet-encrypted but "
                "CONNECTION_SECRET_KEY is not set in .env."
            )
        password = decrypt_password(stored_value, secret_key)
        if not password:
            raise ConnectionCredentialError(
                f"{env}: could not decrypt sql_password_encrypted. "
                "Verify CONNECTION_SECRET_KEY matches the key used by "
                "scripts/encrypt_password.py."
            )
        return password

    return stored_value
