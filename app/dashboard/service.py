"""Dashboard service — assembles the view model consumed by the template.

This is the seam between the UI and the data source. Today it reads the mock
rows in :mod:`app.dashboard.mock_data`; in a later step the same methods will
read ``orchestration.job_steps`` / ``step_runs`` / ``db_execution_log`` from the
database and return the identical shapes. No execution logic lives here.
"""

from __future__ import annotations

from typing import Any

from app.dashboard import mock_data


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

    def get_dashboard(self) -> dict[str, Any]:
        job_steps = mock_data.get_job_steps()
        step_runs = mock_data.get_step_runs()

        cards = [self._build_card(step, step_runs.get(step["step_id"], {})) for step in job_steps]

        phases = []
        for phase in mock_data.PHASES:
            phase_cards = [c for c in cards if c["phase"] == phase["key"]]
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
            "run": self._build_run_header(cards),
            "phases": phases,
            "execution_log": self._build_log(),
        }

    def _build_card(self, step: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
        return {
            "step_id": step["step_id"],
            "step_order": step["step_order"],
            "step_name": step["step_name"],
            "phase": step["phase"],
            "server_name": step["server_name"],
            "execute_proc_name": step["execute_proc_name"],
            "validate_proc_name": step["validate_proc_name"],
            "is_enabled": step["is_enabled"],
            "execution_status": run.get("execution_status", "Pending"),
            "validation_status": run.get("validation_status", "Pending"),
            "last_message": run.get("last_message", ""),
            "last_run_time": run.get("completed_at") or run.get("started_at") or "—",
            "duration": _format_duration(run.get("duration_seconds")),
        }

    def _build_run_header(self, cards: list[dict[str, Any]]) -> dict[str, Any]:
        run = dict(mock_data.get_current_run())
        total = len(cards)
        success = sum(1 for c in cards if c["execution_status"] == "Success")
        failed = sum(1 for c in cards if c["execution_status"] == "Failed")
        running = sum(1 for c in cards if c["execution_status"] == "Running")
        pending = sum(1 for c in cards if c["execution_status"] in ("Pending", "Skipped"))
        val_failed = sum(1 for c in cards if c["validation_status"] == "Failed")

        run["totals"] = {
            "total": total,
            "success": success,
            "failed": failed,
            "running": running,
            "pending": pending,
            "validation_failed": val_failed,
        }
        run["progress_pct"] = round((success / total) * 100) if total else 0
        run["success_pct"] = round((success / total) * 100) if total else 0
        return run

    def _build_log(self) -> list[dict[str, Any]]:
        rows = []
        for row in mock_data.get_execution_log():
            enriched = dict(row)
            enriched["duration"] = _format_duration(row.get("duration_seconds"))
            rows.append(enriched)
        return rows
