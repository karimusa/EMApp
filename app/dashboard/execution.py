"""Dashboard run/step execution service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.dashboard.errors import ExecutionError, LiveExecutionRequiredError
from app.db.repositories.base import use_mock_data
from app.db.repositories.orchestration import OrchestrationRepository

_ACTIVE_RUN_STATUSES = frozenset({"Running", "In Progress", "Pending"})
_BLOCKING_START_STATUSES = frozenset({"Running", "In Progress"})


class ExecutionService:
    def __init__(self) -> None:
        self._repo = OrchestrationRepository()

    def _require_live_execution(self) -> None:
        if use_mock_data():
            raise LiveExecutionRequiredError(
                "Live SQL connection unavailable. Run, validate, stop, and sequence "
                "actions require MonthEndOrchestrationDB."
            )

    def _get_jobs(self) -> list[dict[str, Any]]:
        jobs = self._repo.get_jobs()
        if not jobs:
            raise ExecutionError("No active orchestration job is configured.")
        return jobs

    def _resolve_run_id(self, run_id: int | None) -> int:
        if run_id is not None:
            return int(run_id)
        current = self._repo.get_current_run_id()
        if current is None:
            raise ExecutionError("No active run. Start a new run first.")
        return int(current)

    def _active_run(self) -> dict[str, Any] | None:
        runs = self._repo.get_job_runs()
        for run in runs:
            if run["status"] in _ACTIVE_RUN_STATUSES:
                return run
        return None

    def get_execution_state(self) -> dict[str, Any]:
        active = self._active_run()
        return {
            "live_db_available": not use_mock_data(),
            "active_run_id": active["run_id"] if active else None,
            "active_run_status": active["status"] if active else None,
            "can_stop": active is not None,
            "can_sequence": active is not None,
        }

    def start_run(self, *, actor: str, run_name: str | None = None) -> dict[str, Any]:
        self._require_live_execution()
        if self._active_run():
            raise ExecutionError("A run is already in progress. Stop it before starting a new one.")
        jobs = self._get_jobs()
        label = (run_name or "").strip() or datetime.utcnow().strftime("%B %Y")
        run_id = self._repo.create_job_run(
            job_id=int(jobs[0]["job_id"]),
            triggered_by=actor,
            run_name=label,
        )
        return {
            "run_id": run_id,
            "status": "Running",
            "period_label": label,
        }

    def stop_run(self, *, run_id: int | None, actor: str) -> dict[str, Any]:
        self._require_live_execution()
        resolved_run_id = self._resolve_run_id(run_id)
        active = self._active_run()
        if not active or int(active["run_id"]) != int(resolved_run_id):
            raise ExecutionError("Only an in-progress run can be stopped.")
        self._repo.stop_job_run(resolved_run_id)
        return {"run_id": resolved_run_id, "status": "Stopped", "stopped_by": actor}

    def run_step(self, step_id: int, *, run_id: int | None, actor: str) -> dict[str, Any]:
        self._require_live_execution()
        resolved_run_id = self._resolve_run_id(run_id)
        step = self._repo.get_step_by_id(step_id)
        if not step:
            raise ExecutionError("Step not found.")
        if not step.get("is_enabled", True):
            raise ExecutionError("Step is disabled.")
        try:
            result = self._repo.execute_step_procedure(
                step,
                run_id=resolved_run_id,
                actor=actor,
            )
        except ConnectionError:
            raise
        except Exception as exc:
            raise ExecutionError(str(exc)) from exc
        return {
            "run_id": resolved_run_id,
            "step_id": step_id,
            **result,
        }

    def validate_step(self, step_id: int, *, run_id: int | None, actor: str) -> dict[str, Any]:
        self._require_live_execution()
        resolved_run_id = self._resolve_run_id(run_id)
        step = self._repo.get_step_by_id(step_id)
        if not step:
            raise ExecutionError("Step not found.")
        result = self._repo.validate_step_procedure(
            step,
            run_id=resolved_run_id,
            actor=actor,
        )
        return {
            "run_id": resolved_run_id,
            "step_id": step_id,
            **result,
        }

    def run_sequence(self, *, run_id: int | None, actor: str) -> dict[str, Any]:
        self._require_live_execution()
        resolved_run_id = self._resolve_run_id(run_id)
        steps = sorted(
            self._repo.get_job_steps(),
            key=lambda step: (step.get("phase_code") or "", step.get("step_order") or 0, step["step_id"]),
        )
        step_runs = self._repo.get_step_runs(resolved_run_id)
        executed: list[dict[str, Any]] = []

        for step in steps:
            current = step_runs.get(int(step["step_id"]), {})
            if current.get("execution_status") == "Success":
                continue
            try:
                result = self._repo.execute_step_procedure(
                    step,
                    run_id=resolved_run_id,
                    actor=actor,
                )
            except Exception as exc:
                return {
                    "run_id": resolved_run_id,
                    "executed_count": len(executed),
                    "stopped_on_step_id": step["step_id"],
                    "stopped_on_step_name": step["step_name"],
                    "error": str(exc),
                    "executed": executed,
                }
            executed.append(
                {
                    "step_id": step["step_id"],
                    "step_name": step["step_name"],
                    **result,
                }
            )
            step_runs[int(step["step_id"])] = {
                "execution_status": result.get("execution_status", "Success")
            }

        return {
            "run_id": resolved_run_id,
            "executed_count": len(executed),
            "executed": executed,
            "completed": True,
        }
