"""SQL Agent jobs repository — uses stored procedure on each server connection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.db.connection_manager import get_connection_manager


class SqlAgentRepository:
    """Fetch SQL Agent jobs via orchestration.usp_GetMonitoredAgentJobs."""

    PROC_NAME = "orchestration.usp_GetMonitoredAgentJobs"

    def get_all_jobs(self) -> list[dict[str, Any]]:
        if self._testing():
            return self._mock_jobs()

        jobs: list[dict[str, Any]] = []
        for conn_name in ("PRIMARY", "REMOTE_SQL"):
            conn = get_connection_manager().get(conn_name)
            if not conn:
                continue
            try:
                server_jobs = self._fetch_jobs(conn_name)
                for job in server_jobs:
                    job["connection_name"] = conn_name
                    job["server_name"] = conn.server_name
                jobs.extend(server_jobs)
            except Exception as exc:
                jobs.append(
                    {
                        "connection_name": conn_name,
                        "server_name": conn.server_name,
                        "job_name": f"(Error loading jobs: {exc})",
                        "is_enabled": False,
                        "last_run_status": "Error",
                        "last_run_time": None,
                        "next_run_time": None,
                        "is_running": False,
                    }
                )
        return jobs

    def _fetch_jobs(self, connection_name: str) -> list[dict[str, Any]]:
        with get_connection_manager().connect(connection_name) as db:
            cursor = db.cursor()
            cursor.execute(f"EXEC {self.PROC_NAME}")
            if not cursor.description:
                return []
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _testing(self) -> bool:
        try:
            return get_connection_manager()._config.get("TESTING", False)
        except RuntimeError:
            return False

    def _mock_jobs(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        return [
            {
                "connection_name": "PRIMARY",
                "server_name": "SPUS001BDBEXT",
                "job_name": "ME_GL_Posting",
                "is_enabled": True,
                "last_run_status": "Succeeded",
                "last_run_time": now,
                "next_run_time": None,
                "is_running": False,
            },
            {
                "connection_name": "PRIMARY",
                "server_name": "SPUS001BDBEXT",
                "job_name": "ME_Subledger_Reconcile",
                "is_enabled": True,
                "last_run_status": "Succeeded",
                "last_run_time": now,
                "next_run_time": None,
                "is_running": False,
            },
            {
                "connection_name": "REMOTE_SQL",
                "server_name": "SPAZ001EDM10",
                "job_name": "ME_BI_Cube_Process",
                "is_enabled": True,
                "last_run_status": "Running",
                "last_run_time": now,
                "next_run_time": None,
                "is_running": True,
            },
            {
                "connection_name": "REMOTE_SQL",
                "server_name": "SPAZ001EDM10",
                "job_name": "ME_Report_Refresh",
                "is_enabled": False,
                "last_run_status": "Disabled",
                "last_run_time": None,
                "next_run_time": None,
                "is_running": False,
            },
        ]
