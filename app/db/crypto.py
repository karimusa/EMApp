"""Credential encryption for orchestration.app_connections."""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger(__name__)


def _get_fernet(secret_key: str):
    from cryptography.fernet import Fernet

    key = secret_key.encode() if isinstance(secret_key, str) else secret_key
    if len(key) != 44:
        key = base64.urlsafe_b64encode(key.ljust(32, b"\0")[:32])
    return Fernet(key)


def encrypt_password(plain_text: str, secret_key: str) -> str:
    if not plain_text:
        return ""
    return _get_fernet(secret_key).encrypt(plain_text.encode()).decode()


def decrypt_password(cipher_text: str, secret_key: str) -> str:
    if not cipher_text:
        return ""
    if not secret_key:
        logger.warning("CONNECTION_SECRET_KEY not set; cannot decrypt connection password")
        return ""
    try:
        return _get_fernet(secret_key).decrypt(cipher_text.encode()).decode()
    except Exception:
        logger.exception("Failed to decrypt connection password")
        return ""
