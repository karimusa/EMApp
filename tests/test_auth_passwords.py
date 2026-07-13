"""Tests for dbo.users password verification and legacy hash upgrade."""

from __future__ import annotations

from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.passwords import (
    is_legacy_sha256_password_hash,
    legacy_sha256_password_hash,
    verify_legacy_sha256_password_hash,
    verify_user_password_hash,
)
from app.auth.service import AuthService
from app.db.repositories.users import UserRepository

LEGACY_PASSWORD = "MonthEndApp"
LEGACY_HASH = legacy_sha256_password_hash(LEGACY_PASSWORD)
KARIM_LEGACY_HASH = (
    "830F40C0ECE8D7414B9EB5265732435A7A203360EA5EB332411FAF6F4CD74EFC"
)


def test_is_legacy_sha256_password_hash_detects_uppercase_hex():
    assert is_legacy_sha256_password_hash(KARIM_LEGACY_HASH)
    assert is_legacy_sha256_password_hash(LEGACY_HASH)


def test_is_legacy_sha256_password_hash_rejects_werkzeug():
    assert not is_legacy_sha256_password_hash(generate_password_hash("admin123"))


def test_verify_user_password_hash_accepts_werkzeug_hash():
    stored = generate_password_hash("admin123")
    assert verify_user_password_hash(stored, "admin123")
    assert not verify_user_password_hash(stored, "wrong")


def test_verify_user_password_hash_accepts_legacy_sha256_hash():
    assert verify_user_password_hash(LEGACY_HASH, LEGACY_PASSWORD)
    assert verify_legacy_sha256_password_hash(LEGACY_HASH, LEGACY_PASSWORD)
    assert not verify_user_password_hash(LEGACY_HASH, "wrong")


def test_user_repository_verify_password_werkzeug():
    repo = UserRepository()
    user = {"password_hash": generate_password_hash("viewer123")}
    assert repo.verify_password(user, "viewer123") is True
    assert repo.verify_password(user, "nope") is False


def test_user_repository_verify_password_legacy_sha256():
    repo = UserRepository()
    user = {"password_hash": LEGACY_HASH}
    assert repo.verify_password(user, LEGACY_PASSWORD) is True
    assert repo.verify_password(user, "wrong") is False


@patch("app.db.repositories.users.exec_primary")
def test_user_repository_upgrade_password_hash_writes_werkzeug(mock_exec):
    repo = UserRepository()
    repo.upgrade_password_hash(7, "new-secret")

    mock_exec.assert_called_once()
    sql, params = mock_exec.call_args.args
    assert "UPDATE dbo.users" in sql
    assert params[1] == 7
    assert check_password_hash(params[0], "new-secret")


@patch.object(UserRepository, "upgrade_password_hash")
def test_auth_service_upgrades_legacy_password_after_login(mock_upgrade):
    service = AuthService()
    user = {
        "user_id": 3,
        "password_hash": LEGACY_HASH,
    }

    with patch("app.auth.service.use_mock_data", return_value=False):
        service.upgrade_legacy_password_if_needed(user, LEGACY_PASSWORD)

    mock_upgrade.assert_called_once_with(3, LEGACY_PASSWORD)


@patch.object(UserRepository, "upgrade_password_hash")
def test_auth_service_skips_upgrade_for_werkzeug_hash(mock_upgrade):
    service = AuthService()
    user = {
        "user_id": 3,
        "password_hash": generate_password_hash("admin123"),
    }

    with patch("app.auth.service.use_mock_data", return_value=False):
        service.upgrade_legacy_password_if_needed(user, "admin123")

    mock_upgrade.assert_not_called()


@patch.object(UserRepository, "upgrade_password_hash")
def test_auth_service_skips_upgrade_in_mock_mode(mock_upgrade):
    service = AuthService()
    user = {"user_id": 1, "password_hash": LEGACY_HASH}

    with patch("app.auth.service.use_mock_data", return_value=True):
        service.upgrade_legacy_password_if_needed(user, LEGACY_PASSWORD)

    mock_upgrade.assert_not_called()
