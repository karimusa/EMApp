"""Tests for orchestration.app_connections schema (environment_name registry)."""

from app.db.connection_manager import (
    ACTIVE_APP_CONNECTIONS_SQL,
    APP_CONNECTIONS_REGISTRY_SQL,
)


def test_active_connections_query_uses_environment_name():
    assert "environment_name" in ACTIVE_APP_CONNECTIONS_SQL
    assert "connection_name" not in ACTIVE_APP_CONNECTIONS_SQL
    assert "WHERE is_active = 1" in ACTIVE_APP_CONNECTIONS_SQL
    assert "sql_username" in ACTIVE_APP_CONNECTIONS_SQL
    assert "sql_password_encrypted" in ACTIVE_APP_CONNECTIONS_SQL
    assert "sql_password_hash" in ACTIVE_APP_CONNECTIONS_SQL


def test_registry_query_orders_by_environment_name():
    assert "ORDER BY environment_name" in APP_CONNECTIONS_REGISTRY_SQL
    assert "connection_name" not in APP_CONNECTIONS_REGISTRY_SQL
