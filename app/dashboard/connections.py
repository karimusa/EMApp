"""Connection service — resolves the active database connection.

Server and database names are never hardcoded in application logic; they are
loaded from ``orchestration.app_connections`` (mock rows today, live SQL later).
"""

from __future__ import annotations

from typing import Any

from app.dashboard import mock_data


class ConnectionService:
    def list_connections(self) -> list[dict[str, Any]]:
        return mock_data.get_app_connections()

    def get_active(self) -> dict[str, Any]:
        """Return the active PRIMARY connection used as the console data source."""
        return mock_data.get_active_connection()
