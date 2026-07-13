"""Tests for orchestration.app_connections schema (environment_name registry)."""

from app.db.app_connections_schema import (
    active_app_connections_sql,
    registry_app_connections_sql,
)
from app.db.connection_manager import (
    ACTIVE_APP_CONNECTIONS_SQL,
    APP_CONNECTIONS_REGISTRY_SQL,
)


def test_active_connections_query_uses_environment_name():
    assert "environment_name" in ACTIVE_APP_CONNECTIONS_SQL
    assert "connection_name" not in ACTIVE_APP_CONNECTIONS_SQL
    assert "WHERE is_active = 1" in ACTIVE_APP_CONNECTIONS_SQL
    assert "sql_username" in ACTIVE_APP_CONNECTIONS_SQL
    assert "sql_password_hash" in ACTIVE_APP_CONNECTIONS_SQL
    assert "sql_password_encrypted" not in ACTIVE_APP_CONNECTIONS_SQL


def test_registry_query_orders_by_environment_name():
    assert "ORDER BY environment_name" in APP_CONNECTIONS_REGISTRY_SQL
    assert "connection_name" not in APP_CONNECTIONS_REGISTRY_SQL


def test_legacy_active_query_matches_schema_helper():
    assert (
        ACTIVE_APP_CONNECTIONS_SQL
        == active_app_connections_sql(include_encrypted_password=False)
    )


def test_encrypted_query_is_opt_in():
    encrypted_sql = active_app_connections_sql(include_encrypted_password=True)
    assert "sql_password_encrypted" in encrypted_sql
    assert "sql_password_hash" in encrypted_sql
    assert (
        registry_app_connections_sql(include_encrypted_password=True)
        == encrypted_sql.replace("\n    WHERE is_active = 1", "\n    ORDER BY environment_name")
    )
