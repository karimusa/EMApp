"""Integration tests for ConnectionManager runtime credential resolution."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from app.db.connection_manager import (
    ConnectionDiagnostics,
    ConnectionManager,
    _format_connection_diagnostics,
    _log_bootstrap_vs_primary,
)

USER_SHA256 = "6A1E8FF1C31598F89EB18B72EE8F81BFF27C85692BB1DF4E33C0F9E3731E0C3C"

BOOTSTRAP_CONFIG = {
    "BOOTSTRAP_DRIVER": "ODBC Driver 18 for SQL Server",
    "BOOTSTRAP_SERVER": "SDAZ001MLD21",
    "BOOTSTRAP_DATABASE": "MonthEndOrchestrationDB",
    "BOOTSTRAP_USER": "MonthEndApp",
    "BOOTSTRAP_PASSWORD": "MonthEndApp",
    "BOOTSTRAP_TRUST_CERT": "yes",
    "CONNECTION_SECRET_KEY": "",
}

PRIMARY_ROW = {
    "connection_id": 1,
    "environment_name": "PRIMARY",
    "is_active": True,
    "server_name": "SDAZ001MLD21",
    "database_name": "MonthEndOrchestrationDB",
    "auth_type": "sql",
    "sql_username": "MonthEndApp",
    "sql_password_encrypted": None,
    "sql_password_hash": USER_SHA256,
    "description": "",
    "created_at": None,
    "updated_at": None,
}


def test_primary_hash_uses_bootstrap_password_in_connection_string():
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    with patch.object(manager, "_fetch_app_connections", return_value=[PRIMARY_ROW]):
        manager.load_connections()

    primary = manager.get_primary()
    assert primary is not None
    assert "PWD=MonthEndApp" in manager.build_connection_string(primary)


def test_primary_hash_connects_with_bootstrap_password():
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.description = [("x",)]

    with patch("app.db.connection_manager._import_pyodbc") as import_pyodbc, patch.object(
        manager, "_fetch_app_connections", return_value=[PRIMARY_ROW]
    ):
        pyodbc = import_pyodbc.return_value
        pyodbc.connect.return_value = mock_db
        manager.reload()

    assert manager.get_primary_error() is None
    connection_string = pyodbc.connect.call_args.args[0]
    assert "PWD=MonthEndApp" in connection_string
    assert USER_SHA256 not in connection_string


def test_primary_hash_resolves_bootstrap_password_source():
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    with patch.object(manager, "_fetch_app_connections", return_value=[PRIMARY_ROW]):
        manager.load_connections()

    primary = manager.get_primary()
    assert primary is not None

    _user, _password, password_source = manager._runtime_sql_credentials(
        primary,
        environment_name="PRIMARY",
    )
    assert password_source == "BOOTSTRAP_PASSWORD"


def test_primary_hash_connect_logs_matching_password_source(caplog):
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.description = [("x",)]

    with patch("app.db.connection_manager._import_pyodbc") as import_pyodbc, patch.object(
        manager, "_fetch_app_connections", return_value=[PRIMARY_ROW]
    ), caplog.at_level(logging.INFO):
        pyodbc = import_pyodbc.return_value
        pyodbc.connect.return_value = mock_db
        manager.reload()
        with manager.connect("PRIMARY"):
            pass

    messages = "\n".join(record.message for record in caplog.records)
    assert "MATCH PasswordSource:" in messages
    assert "BOOTSTRAP_PASSWORD" in messages
    assert "DIFF  PasswordSource:" not in messages


def test_primary_hash_blocks_login_when_bootstrap_target_differs():
    row = dict(PRIMARY_ROW)
    row["server_name"] = "OTHER-SERVER"
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    with patch.object(manager, "_fetch_app_connections", return_value=[row]):
        manager.reload()

    assert manager.get_primary_error() is not None
    assert "one-way hash" in manager.get_primary_error()


def test_is_pyodbc_error_detects_sql_server_login_message():
    from app.db.connection_manager import is_pyodbc_error

    class FakeDriverError(Exception):
        __module__ = "builtins"

    exc = FakeDriverError(
        "('28000', \"[Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Login failed for user 'MonthEndApp'. (18456)\")"
    )
    assert is_pyodbc_error(exc)


def test_ensure_primary_validated_matches_reload_validate_path():
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    with patch.object(manager, "reload") as reload_mock, patch.object(
        manager, "get_primary_error", return_value=None
    ):
        assert manager.ensure_primary_validated(reload_registry=True) is None
    reload_mock.assert_called_once_with()


def test_format_connection_diagnostics_hides_password():
    text = _format_connection_diagnostics(
        ConnectionDiagnostics(
            driver="ODBC Driver 18 for SQL Server",
            server="SDAZ001MLD21",
            database="MonthEndOrchestrationDB",
            uid="MonthEndApp",
            trust_server_certificate="yes",
            password_source="BOOTSTRAP_PASSWORD",
        )
    )
    assert "PWD=<hidden>" in text
    assert "MonthEndApp" in text
    assert "PasswordSource=BOOTSTRAP_PASSWORD" in text
    assert "PWD=MonthEndApp" not in text


def test_log_bootstrap_vs_primary_reports_field_diffs(caplog):
    bootstrap = ConnectionDiagnostics(
        driver="ODBC Driver 18 for SQL Server",
        server="SDAZ001MLD21",
        database="MonthEndOrchestrationDB",
        uid="MonthEndApp",
        trust_server_certificate="yes",
        password_source="BOOTSTRAP_PASSWORD",
    )
    primary = ConnectionDiagnostics(
        driver="ODBC Driver 18 for SQL Server",
        server="OTHER-SERVER",
        database="MonthEndOrchestrationDB",
        uid="MonthEndApp",
        trust_server_certificate="yes",
        password_source="sql_password_hash",
    )
    with caplog.at_level(logging.INFO):
        _log_bootstrap_vs_primary(bootstrap, primary)

    messages = "\n".join(record.message for record in caplog.records)
    assert "ODBC connection comparison" in messages
    assert "DIFF" in messages and "Server:" in messages
    assert "MATCH" in messages and "Database:" in messages
    assert "PWD=<hidden>" in messages
    assert "PWD=MonthEndApp" not in messages
