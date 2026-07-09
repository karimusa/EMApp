"""Tests for runtime SQL credential resolution."""

from __future__ import annotations

import pytest

from app.db.credentials import (
    ConnectionCredentialError,
    is_one_way_hash,
    is_unusable_stored_credential,
    matches_bootstrap_target,
    resolve_sql_login_password,
    resolve_sql_login_password_with_source,
    stored_credential_from_row,
)

USER_SHA256 = "6A1E8FF1C31598F89EB18B72EE8F81BFF27C85692BB1DF4E33C0F9E3731E0C3C"

BOOTSTRAP_CONFIG = {
    "BOOTSTRAP_SERVER": "SDAZ001MLD21",
    "BOOTSTRAP_DATABASE": "MonthEndOrchestrationDB",
    "BOOTSTRAP_USER": "MonthEndApp",
    "BOOTSTRAP_PASSWORD": "MonthEndApp",
}


def test_is_one_way_hash_detects_sha256_hex():
    assert is_one_way_hash(USER_SHA256)
    assert is_one_way_hash(USER_SHA256.lower())


def test_is_one_way_hash_rejects_plain_password():
    assert not is_one_way_hash("MonthEndApp")


def test_stored_credential_prefers_encrypted_column():
    row = {
        "sql_password_encrypted": "plain-secret",
        "sql_password_hash": USER_SHA256,
    }
    assert stored_credential_from_row(row) == "plain-secret"


def test_resolve_plain_text_password():
    password = resolve_sql_login_password(
        "MonthEndApp",
        secret_key="",
        environment_name="PRIMARY",
    )
    assert password == "MonthEndApp"


def test_is_unusable_stored_credential_detects_hash():
    assert is_unusable_stored_credential(USER_SHA256, secret_key="")


def test_is_unusable_stored_credential_plain_text_is_usable():
    assert not is_unusable_stored_credential("MonthEndApp", secret_key="")


def test_resolve_rejects_one_way_hash_without_bootstrap_match():
    with pytest.raises(ConnectionCredentialError, match="one-way hash"):
        resolve_sql_login_password(
            USER_SHA256,
            secret_key="",
            environment_name="REMOTE_SQL",
            server_name="OTHER-SERVER",
            database_name="OtherDB",
            sql_username="OtherUser",
            config=BOOTSTRAP_CONFIG,
        )


def test_resolve_one_way_hash_uses_bootstrap_fallback_for_primary():
    password = resolve_sql_login_password_with_source(
        USER_SHA256,
        secret_key="",
        environment_name="PRIMARY",
        server_name="SDAZ001MLD21",
        database_name="MonthEndOrchestrationDB",
        sql_username="MonthEndApp",
        config=BOOTSTRAP_CONFIG,
        origin_column="sql_password_hash",
    )
    assert password.password == "MonthEndApp"
    assert password.source == "BOOTSTRAP_PASSWORD"


def test_resolve_empty_uses_bootstrap_fallback():
    password = resolve_sql_login_password(
        None,
        secret_key="",
        environment_name="PRIMARY",
        server_name="SDAZ001MLD21",
        database_name="MonthEndOrchestrationDB",
        sql_username="MonthEndApp",
        config=BOOTSTRAP_CONFIG,
    )
    assert password == "MonthEndApp"


def test_resolve_empty_no_fallback_when_target_differs():
    with pytest.raises(ConnectionCredentialError, match="no SQL login password"):
        resolve_sql_login_password(
            "",
            secret_key="",
            environment_name="REMOTE_SQL",
            server_name="OTHER-SERVER",
            database_name="MonthEndOrchestrationDB",
            sql_username="MonthEndApp",
            config=BOOTSTRAP_CONFIG,
        )


def test_resolve_fernet_requires_secret_key():
    with pytest.raises(ConnectionCredentialError, match="CONNECTION_SECRET_KEY"):
        resolve_sql_login_password(
            "gAAAAABmocktoken",
            secret_key="",
            environment_name="PRIMARY",
        )



def test_matches_bootstrap_target_case_insensitive():
    assert matches_bootstrap_target(
        "SDAZ001MLD21",
        "MonthEndOrchestrationDB",
        "MonthEndApp",
        BOOTSTRAP_CONFIG,
    )


def test_matches_bootstrap_target_ignores_sql_instance_suffix():
    assert matches_bootstrap_target(
        "SDAZ001MLD21\\SQLEXPRESS",
        "MonthEndOrchestrationDB",
        "MonthEndApp",
        BOOTSTRAP_CONFIG,
    )


def test_is_one_way_hash_detects_spaced_hex():
    spaced = " ".join(USER_SHA256[i : i + 4] for i in range(0, 64, 4))
    assert is_one_way_hash(spaced)


def test_stored_credential_skips_hash_in_encrypted_column():
    row = {
        "sql_password_encrypted": USER_SHA256,
        "sql_password_hash": USER_SHA256,
    }
    assert stored_credential_from_row(row) == USER_SHA256
