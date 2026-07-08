"""Integration tests for ConnectionManager runtime credential resolution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.db.connection_manager import ConnectionManager

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


def test_primary_hash_blocks_login_when_bootstrap_target_differs():
    row = dict(PRIMARY_ROW)
    row["server_name"] = "OTHER-SERVER"
    manager = ConnectionManager(BOOTSTRAP_CONFIG)
    with patch.object(manager, "_fetch_app_connections", return_value=[row]):
        manager.reload()

    assert manager.get_primary_error() is not None
    assert "one-way hash" in manager.get_primary_error()
