"""Connection service — resolves the active database connection."""

from __future__ import annotations

from typing import Any

from app.dashboard import data


class ConnectionService:
    def list_connections(self) -> list[dict[str, Any]]:
        return data.get_app_connections()

    def get_active(self) -> dict[str, Any]:
        return data.get_active_connection()
