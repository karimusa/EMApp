"""Tests for orchestration.app_connections schema detection."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.db.app_connections_schema import (
    active_app_connections_sql,
    detect_sql_password_encrypted_column,
    registry_app_connections_sql,
    runtime_credential_column_label,
)


def test_detect_sql_password_encrypted_column_true():
    cursor = MagicMock()
    cursor.fetchone.return_value = (8000,)
    assert detect_sql_password_encrypted_column(cursor) is True
    cursor.execute.assert_called_once()


def test_detect_sql_password_encrypted_column_false():
    cursor = MagicMock()
    cursor.fetchone.return_value = (None,)
    assert detect_sql_password_encrypted_column(cursor) is False


def test_active_sql_excludes_encrypted_by_default():
    sql = active_app_connections_sql(include_encrypted_password=False)
    assert "sql_password_hash" in sql
    assert "sql_password_encrypted" not in sql


def test_active_sql_includes_encrypted_when_requested():
    sql = active_app_connections_sql(include_encrypted_password=True)
    assert "sql_password_encrypted" in sql
    assert "sql_password_hash" in sql


def test_registry_sql_excludes_encrypted_by_default():
    sql = registry_app_connections_sql(include_encrypted_password=False)
    assert "ORDER BY environment_name" in sql
    assert "sql_password_encrypted" not in sql


def test_runtime_credential_column_label():
    assert (
        runtime_credential_column_label(include_encrypted_password=False)
        == "sql_password_hash"
    )
    assert (
        runtime_credential_column_label(include_encrypted_password=True)
        == "sql_password_encrypted"
    )
