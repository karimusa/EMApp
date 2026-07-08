"""Connection repository — orchestration.app_connections (database registry)."""

from __future__ import annotations

from typing import Any

from app.db.connection_manager import APP_CONNECTIONS_REGISTRY_SQL, get_connection_manager
from app.db.formatters import coerce_bool, format_timestamp
from app.db.repositories.base import query_primary, use_mock_data


class ConnectionsRepository:
    def list_connections(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_app_connections()

        rows = query_primary(APP_CONNECTIONS_REGISTRY_SQL)
        return [self._normalize(row) for row in rows]

    def get_active(self) -> dict[str, Any]:
        connections = self.list_connections()
        for conn in connections:
            if conn["connection_name"] == "PRIMARY" and conn["is_active"]:
                return conn
        return connections[0] if connections else {}

    def ping_latency_ms(self, connection_name: str) -> int | None:
        if use_mock_data():
            return 12
        try:
            with get_connection_manager().connect(connection_name) as db:
                cursor = db.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return 12
        except Exception:
            return None

    def _normalize(self, row: dict[str, Any]) -> dict[str, Any]:
        encrypted = row.get("password_encrypted")
        return {
            "connection_id": row["connection_id"],
            "connection_name": row["connection_name"],
            "server_name": row["server_name"],
            "database_name": row["database_name"],
            "username": row["username"],
            "password_encrypted": (
                "gAAAAAB...redacted" if encrypted else None
            ),
            "password_plain": None,
            "driver": row.get("driver") or "ODBC Driver 18 for SQL Server",
            "trust_server_certificate": row.get("trust_server_certificate") or "yes",
            "is_active": coerce_bool(row.get("is_active")),
            "created_at": format_timestamp(row.get("created_at")),
            "updated_at": format_timestamp(row.get("updated_at")),
        }
