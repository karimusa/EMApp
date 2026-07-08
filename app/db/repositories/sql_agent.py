"""SQL Agent jobs — orchestration.usp_GetMonitoredAgentJobs per connection."""

from __future__ import annotations

import logging
from typing import Any

from app.db.connection_manager import get_connection_manager
from app.db.formatters import coerce_bool, format_agent_job_time
from app.db.registry import job_key
from app.db.repositories.base import query_connection, use_mock_data

logger = logging.getLogger(__name__)

PROC_NAME = "orchestration.usp_GetMonitoredAgentJobs"


class SqlAgentRepository:
    def get_monitored_agent_jobs(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_monitored_agent_jobs()

        jobs: list[dict[str, Any]] = []
        manager = get_connection_manager()
        for conn_name in ("PRIMARY", "REMOTE_SQL"):
            conn = manager.get(conn_name)
            if not conn:
                continue
            try:
                rows = query_connection(conn_name, f"EXEC {PROC_NAME}")
                for row in rows:
                    jobs.append(self._normalize(row, conn_name, conn.server_name))
            except Exception:
                logger.exception("Failed to load SQL Agent jobs for %s", conn_name)
        return jobs

    def _normalize(
        self, row: dict[str, Any], connection_name: str, server_name: str
    ) -> dict[str, Any]:
        job_name = row.get("job_name") or ""
        alt_name = row.get("alt_name")
        return {
            "job_name": job_name,
            "alt_name": alt_name,
            "job_key": job_key(job_name),
            "is_enabled": coerce_bool(row.get("is_enabled")),
            "last_run_status": row.get("last_run_status") or "Unknown",
            "last_run_time": format_agent_job_time(row.get("last_run_time")),
            "next_run_time": format_agent_job_time(row.get("next_run_time")),
            "is_running": coerce_bool(row.get("is_running")),
            "server_name": server_name,
            "connection_name": connection_name,
        }
