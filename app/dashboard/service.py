"""Dashboard service — assembles the view model consumed by the template.

Reads from :mod:`app.dashboard.data` (SQL repositories or mock fallback).
No execution logic lives here.
"""

from __future__ import annotations

from typing import Any

from app.dashboard import data as orchestration_data
from app.dashboard.connections import ConnectionService


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    minutes, secs = divmod(int(seconds), 60)
    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class DashboardService:
    """Builds the operations-console view model for a single run."""

    def __init__(self) -> None:
        self.connections = ConnectionService()

    def get_dashboard(self) -> dict[str, Any]:
        job_steps = orchestration_data.get_job_steps()
        step_runs = orchestration_data.get_step_runs()
        validations = orchestration_data.get_validation_results()

        cards = [
            self._build_card(
                step,
                step_runs.get(step["step_id"], {}),
                validations.get(step["step_id"], {}),
            )
            for step in job_steps
        ]

        phases = []
        for phase in orchestration_data.PHASES:
            phase_cards = [c for c in cards if c["phase_code"] == phase["key"]]
            completed = sum(1 for c in phase_cards if c["execution_status"] == "Success")
            phases.append(
                {
                    "key": phase["key"],
                    "label": phase["label"],
                    "steps": phase_cards,
                    "total": len(phase_cards),
                    "completed": completed,
                }
            )

        return {
            "run": self._build_run_header(),
            "metrics": orchestration_data.get_run_metrics(),
            "phases": phases,
            "execution_log": self._build_log(),
            "run_history": orchestration_data.get_job_runs(),
            "active_connection": self.connections.get_active(),
        }

    def _build_card(
        self, step: dict[str, Any], run: dict[str, Any], validation: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "step_id": step["step_id"],
            "step_order": step["step_order"],
            "step_name": step["step_name"],
            "phase_code": step["phase_code"],
            "server_name": step["server_name"],
            "execute_proc_name": step["execute_proc_name"],
            "validate_proc_name": step["validate_proc_name"],
            "is_enabled": step["is_enabled"],
            "agent_job_name": step.get("agent_job_name"),
            "agent_job_key": step.get("agent_job_key"),
            "execution_status": run.get("execution_status", "Pending"),
            "validation_status": run.get("validation_status", "Pending"),
            "last_message": run.get("last_message", ""),
            "last_run_time": run.get("completed_at") or run.get("started_at") or "—",
            "duration": _format_duration(run.get("duration_seconds")),
            "validation": validation,
        }

    def get_agent_jobs(self) -> dict[str, Any]:
        """View model for the SQL Agent jobs page (mock ``usp_GetMonitoredAgentJobs``).

        Jobs are grouped by server, ordered by the connection registry.
        """
        jobs = orchestration_data.get_monitored_agent_jobs()

        triggers = {
            s.agent_job: {"step_name": s.step_name, "execute_proc": s.execute_proc}
            for s in orchestration_data.STEP_REGISTRY
            if s.agent_job
        }
        for job in jobs:
            trigger = triggers.get(job["job_name"], {})
            job["trigger_step"] = trigger.get("step_name")
            job["trigger_proc"] = trigger.get("execute_proc")

        groups = []
        for conn in self.connections.list_connections():
            server_jobs = [j for j in jobs if j["connection_name"] == conn["connection_name"]]
            if server_jobs:
                groups.append(
                    {
                        "connection_name": conn["connection_name"],
                        "server_name": conn["server_name"],
                        "database_name": conn["database_name"],
                        "jobs": server_jobs,
                    }
                )

        return {
            "groups": groups,
            "active_connection": self.connections.get_active(),
            "totals": {
                "total": len(jobs),
                "running": sum(1 for j in jobs if j["is_running"]),
                "failed": sum(1 for j in jobs if j["last_run_status"] == "Failed"),
                "disabled": sum(1 for j in jobs if not j["is_enabled"]),
            },
        }

    def _build_run_header(self) -> dict[str, Any]:
        return dict(orchestration_data.get_current_run())

    def _build_log(self) -> list[dict[str, Any]]:
        return self.get_logs()["rows"]

    def get_run_history(self) -> dict[str, Any]:
        """Full run history view model (``orchestration.job_runs``)."""
        runs = orchestration_data.get_job_runs()
        return {
            "runs": runs,
            "totals": {
                "total": len(runs),
                "in_progress": sum(1 for r in runs if r["status"] == "In Progress"),
                "completed": sum(1 for r in runs if r["status"] == "Completed"),
                "failed": sum(1 for r in runs if r["status"] == "Failed"),
            },
            "active_connection": self.connections.get_active(),
        }

    def get_logs(self) -> dict[str, Any]:
        """Full execution log view model (``orchestration.db_execution_log``)."""
        rows = []
        for row in orchestration_data.get_execution_log():
            enriched = dict(row)
            enriched["duration"] = _format_duration(row.get("duration_seconds"))
            rows.append(enriched)
        return {
            "rows": rows,
            "phases": orchestration_data.PHASES,
            "totals": {
                "total": len(rows),
                "success": sum(1 for r in rows if r["status"] == "Success"),
                "failed": sum(1 for r in rows if r["status"] == "Failed"),
                "running": sum(1 for r in rows if r["status"] == "Running"),
            },
            "active_connection": self.connections.get_active(),
        }

    def get_validation(self) -> dict[str, Any]:
        """Validation results across all steps."""
        job_steps = {s["step_id"]: s for s in orchestration_data.get_job_steps()}
        validations = orchestration_data.get_validation_results()
        rows = []
        for step_id, result in sorted(validations.items()):
            step = job_steps[step_id]
            rows.append(
                {
                    "step_id": step_id,
                    "step_order": step["step_order"],
                    "step_name": step["step_name"],
                    "phase_code": step["phase_code"],
                    "server_name": step["server_name"],
                    "execute_proc_name": step["execute_proc_name"],
                    "validate_proc_name": step["validate_proc_name"],
                    **result,
                }
            )
        return {
            "rows": rows,
            "totals": {
                "total": len(rows),
                "pass": sum(1 for r in rows if r["ValidationStatus"] == "PASS"),
                "fail": sum(1 for r in rows if r["ValidationStatus"] == "FAIL"),
                "pending": sum(1 for r in rows if r["ValidationStatus"] == "PENDING"),
            },
            "active_connection": self.connections.get_active(),
        }

    def get_monitoring(self) -> dict[str, Any]:
        """Operations monitoring overview."""
        metrics = orchestration_data.get_run_metrics()
        jobs = orchestration_data.get_monitored_agent_jobs()
        connections = self.connections.list_connections()
        return {
            "run": orchestration_data.get_current_run(),
            "metrics": metrics,
            "connections": [
                {
                    "connection_name": c["connection_name"],
                    "server_name": c["server_name"],
                    "database_name": c["database_name"],
                    "is_active": c["is_active"],
                    "status": "Connected" if c["is_active"] else "Inactive",
                    "latency_ms": orchestration_data.connection_latency_ms(c["connection_name"])
                    if c["is_active"]
                    else None,
                }
                for c in connections
            ],
            "agent_jobs": {
                "total": len(jobs),
                "running": sum(1 for j in jobs if j["is_running"]),
                "failed": sum(1 for j in jobs if j["last_run_status"] == "Failed"),
                "healthy": sum(1 for j in jobs if j["last_run_status"] == "Succeeded"),
            },
            "active_connection": self.connections.get_active(),
        }

    def get_settings(self) -> dict[str, Any]:
        """Application and connection settings (read-only until live DB)."""
        connections = []
        for conn in self.connections.list_connections():
            connections.append(
                {
                    "connection_id": conn["connection_id"],
                    "connection_name": conn["connection_name"],
                    "server_name": conn["server_name"],
                    "database_name": conn["database_name"],
                    "username": conn["username"],
                    "driver": conn["driver"],
                    "trust_server_certificate": conn["trust_server_certificate"],
                    "is_active": conn["is_active"],
                    "created_at": conn["created_at"],
                    "updated_at": conn.get("updated_at"),
                }
            )
        return {
            "connections": connections,
            "app_version": "1.0.0",
            "data_source": orchestration_data.data_source_label(),
            "active_connection": self.connections.get_active(),
        }
