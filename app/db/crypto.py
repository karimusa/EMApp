"""Credential encryption utilities for orchestration.app_connections."""

from __future__ import annotations

import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_fernet(secret_key: str):
    from cryptography.fernet import Fernet

    key = secret_key.encode() if isinstance(secret_key, str) else secret_key
    if len(key) != 44:
        padded = base64.urlsafe_b64encode(key.ljust(32, b"\0")[:32])
        key = padded
    return Fernet(key)


def encrypt_password(plain_text: str, secret_key: str) -> str:
    """Encrypt a connection password for storage in orchestration.app_connections."""
    if not plain_text:
        return ""
    fernet = _get_fernet(secret_key)
    return fernet.encrypt(plain_text.encode()).decode()


def decrypt_password(cipher_text: str, secret_key: str) -> str:
    """Decrypt a connection password from orchestration.app_connections."""
    if not cipher_text:
        return ""
    if not secret_key:
        logger.warning("CONNECTION_SECRET_KEY not set; cannot decrypt connection password")
        return ""
    try:
        fernet = _get_fernet(secret_key)
        return fernet.decrypt(cipher_text.encode()).decode()
    except Exception:
        logger.exception("Failed to decrypt connection password")
        return ""
