"""Dashboard service — assembles the view model consumed by the template.

Reads the mock rows in :mod:`app.dashboard.mock_data` today; the same methods
will read the live ``orchestration.*`` tables later and return identical shapes.
No execution logic lives here.

Data sources per the schema:
* summary cards -> ``orchestration.run_metrics``
* step cards    -> ``orchestration.job_steps`` + ``orchestration.step_runs``
* log panel     -> ``orchestration.db_execution_log``
* run history   -> ``orchestration.job_runs``
"""

from __future__ import annotations

from typing import Any

from app.dashboard import mock_data
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
        job_steps = mock_data.get_job_steps()
        step_runs = mock_data.get_step_runs()
        validations = mock_data.get_validation_results()

        cards = [
            self._build_card(
                step,
                step_runs.get(step["step_id"], {}),
                validations.get(step["step_id"], {}),
            )
            for step in job_steps
        ]

        phases = []
        for phase in mock_data.PHASES:
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
            "metrics": mock_data.get_run_metrics(),
            "phases": phases,
            "execution_log": self._build_log(),
            "run_history": mock_data.get_job_runs(),
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
        jobs = mock_data.get_monitored_agent_jobs()

        # Attach the trigger step + execute proc (from the frozen registry).
        triggers = {
            s.agent_job: {"step_name": s.step_name, "execute_proc": s.execute_proc}
            for s in mock_data.STEP_REGISTRY
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
        return dict(mock_data.get_current_run())

    def _build_log(self) -> list[dict[str, Any]]:
        rows = []
        for row in mock_data.get_execution_log():
            enriched = dict(row)
            enriched["duration"] = _format_duration(row.get("duration_seconds"))
            rows.append(enriched)
        return rows

    def get_logs_page(self) -> dict[str, Any]:
        return {
            "execution_log": self._build_log(),
            "audit_log": mock_data.get_audit_log(),
            "run_history": mock_data.get_job_runs(),
            "active_connection": self.connections.get_active(),
        }

    def get_runs_page(self) -> dict[str, Any]:
        return {
            "run_history": mock_data.get_job_runs(),
            "current_run": self._build_run_header(),
            "active_connection": self.connections.get_active(),
        }

    def get_steps_page(self) -> dict[str, Any]:
        data = self.get_dashboard()
        all_steps = []
        for phase in data["phases"]:
            all_steps.extend(phase["steps"])
        return {
            "steps": sorted(all_steps, key=lambda s: s["step_order"]),
            "phases": data["phases"],
            "active_connection": self.connections.get_active(),
        }

    def get_monitoring_page(self) -> dict[str, Any]:
        return {
            "metrics": mock_data.get_monitoring_metrics(),
            "connections": self.connections.list_connections(),
            "agent_totals": self.get_agent_jobs()["totals"],
            "active_connection": self.connections.get_active(),
        }

    def get_validations_page(self) -> dict[str, Any]:
        validations = mock_data.get_validation_results()
        steps = mock_data.get_job_steps()
        rows = []
        for step in steps:
            val = validations.get(step["step_id"], {})
            if val:
                rows.append({**step, "validation": val})
        return {
            "validations": rows,
            "active_connection": self.connections.get_active(),
        }

    def get_alerts_page(self) -> dict[str, Any]:
        return {
            "alerts": mock_data.get_alerts(),
            "active_connection": self.connections.get_active(),
        }

    def get_reports_page(self) -> dict[str, Any]:
        return {
            "reports": mock_data.get_reports(),
            "active_connection": self.connections.get_active(),
        }

    def get_servers_page(self) -> dict[str, Any]:
        return {
            "connections": self.connections.list_connections(),
            "active_connection": self.connections.get_active(),
        }

    def get_audit_page(self) -> dict[str, Any]:
        return {
            "audit_log": mock_data.get_audit_log(),
            "active_connection": self.connections.get_active(),
        }

    def get_settings_page(self) -> dict[str, Any]:
        return {
            "settings": {
                "session_timeout_minutes": 60,
                "log_retention_days": 90,
                "auto_validate": True,
                "notify_on_failure": True,
                "default_period": "Current month",
            },
            "active_connection": self.connections.get_active(),
        }

