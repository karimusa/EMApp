"""Tests for bootstrap self-test against legacy app_connections schema."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from config.bootstrap import run_bootstrap_self_test


def test_bootstrap_self_test_uses_legacy_schema_when_encrypted_column_missing():
    config = {
        "BOOTSTRAP_DRIVER": "ODBC Driver 18 for SQL Server",
        "BOOTSTRAP_SERVER": "SDAZ001MLD21",
        "BOOTSTRAP_DATABASE": "MonthEndOrchestrationDB",
        "BOOTSTRAP_USER": "MonthEndApp",
        "BOOTSTRAP_PASSWORD": "MonthEndApp",
        "BOOTSTRAP_TRUST_CERT": "yes",
    }
    row = (
        1,
        "PRIMARY",
        True,
        "SDAZ001MLD21",
        "MonthEndOrchestrationDB",
        "sql",
        "MonthEndApp",
        "MonthEndApp",
        "",
        None,
        None,
    )
    columns = [
        "connection_id",
        "environment_name",
        "is_active",
        "server_name",
        "database_name",
        "auth_type",
        "sql_username",
        "sql_password_hash",
        "description",
        "created_at",
        "updated_at",
    ]

    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.description = [(name,) for name in columns]
    mock_cursor.fetchone.side_effect = [(1,), (None,), row]
    mock_cursor.fetchall.return_value = [row]

    with patch("app.db.connection_manager._import_pyodbc") as import_pyodbc:
        pyodbc = import_pyodbc.return_value
        pyodbc.connect.return_value = mock_db
        rows = run_bootstrap_self_test(config)

    executed_sql = [call.args[0] for call in mock_cursor.execute.call_args_list]
    registry_sql = executed_sql[-1]
    assert "sql_password_hash" in registry_sql
    assert "sql_password_encrypted" not in registry_sql
    assert rows[0]["environment_name"] == "PRIMARY"
    assert rows[0]["sql_password_hash"] == "MonthEndApp"
