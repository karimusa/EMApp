"""Dashboard run/step execution service."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.dashboard.errors import ExecutionError, LiveExecutionRequiredError
from app.dashboard.runtime import execution_enabled, get_execution_runtime
from app.db.repositories.orchestration import OrchestrationRepository

logger = logging.getLogger(__name__)

_ACTIVE_RUN_STATUSES = frozenset({"Running", "In Progress", "Pending"})
_BLOCKING_START_STATUSES = frozenset({"Running", "In Progress"})


class ExecutionService:
    def __init__(self) -> None:
        self._repo = OrchestrationRepository()

    def _require_live_execution(self) -> None:
        reason = get_execution_runtime().get("execution_block_reason")
        if reason:
            logger.warning("Execution blocked: %s", reason)
            raise LiveExecutionRequiredError(reason)

    def _get_jobs(self) -> list[dict[str, Any]]:
        jobs = self._repo.get_jobs()
        if not jobs:
            raise ExecutionError("No active orchestration job is configured.")
        return jobs

    def _ensure_active_run_id(self, run_id: int | None, *, actor: str) -> int:
        if run_id is not None:
            return int(run_id)

        active = self._active_run()
        if active:
            return int(active["run_id"])

        latest_run_id = self._repo.get_current_run_id()
        if latest_run_id is not None:
            runs = {int(run["run_id"]): run for run in self._repo.get_job_runs()}
            latest = runs.get(int(latest_run_id))
            if latest and latest["status"] in _ACTIVE_RUN_STATUSES:
                return int(latest_run_id)

        jobs = self._get_jobs()
        label = datetime.utcnow().strftime("%B %Y")
        created_run_id = self._repo.create_job_run(
            job_id=int(jobs[0]["job_id"]),
            triggered_by=actor,
            run_name=label,
        )
        logger.info("auto_start_run run_id=%s actor=%s", created_run_id, actor)
        return int(created_run_id)

    def _resolve_run_id(self, run_id: int | None) -> int:
        if run_id is not None:
            return int(run_id)
        active = self._active_run()
        if active:
            return int(active["run_id"])
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

    def _blocking_run_for_start(self) -> dict[str, Any] | None:
        runs = self._repo.get_job_runs()
        for run in runs:
            if run["status"] in _BLOCKING_START_STATUSES:
                return run
        return None

    def get_execution_state(self) -> dict[str, Any]:
        runtime = get_execution_runtime()
        active = self._active_run()
        state = {
            **runtime,
            "active_run_id": active["run_id"] if active else None,
            "active_run_status": active["status"] if active else None,
            "can_stop": execution_enabled() and active is not None,
            "can_sequence": execution_enabled(),
            "can_start": execution_enabled() and self._blocking_run_for_start() is None,
        }
        logger.info(
            "Execution state build=%s git=%s enabled=%s active_run=%s",
            state.get("build_id"),
            state.get("git_head"),
            state.get("execution_enabled"),
            state.get("active_run_id"),
        )
        return state

    def start_run(self, *, actor: str, run_name: str | None = None) -> dict[str, Any]:
        logger.info("start_run requested by=%s run_name=%s", actor, run_name)
        self._require_live_execution()
        if self._blocking_run_for_start():
            raise ExecutionError("A run is already in progress. Stop it before starting a new one.")
        jobs = self._get_jobs()
        label = (run_name or "").strip() or datetime.utcnow().strftime("%B %Y")
        run_id = self._repo.create_job_run(
            job_id=int(jobs[0]["job_id"]),
            triggered_by=actor,
            run_name=label,
        )
        logger.info("start_run created run_id=%s label=%s actor=%s", run_id, label, actor)
        return {
            "run_id": run_id,
            "status": "Running",
            "period_label": label,
        }

    def stop_run(self, *, run_id: int | None, actor: str) -> dict[str, Any]:
        logger.info("stop_run requested by=%s run_id=%s", actor, run_id)
        self._require_live_execution()
        resolved_run_id = self._resolve_run_id(run_id)
        active = self._active_run()
        if not active or int(active["run_id"]) != int(resolved_run_id):
            raise ExecutionError("Only an in-progress run can be stopped.")
        self._repo.stop_job_run(resolved_run_id)
        logger.info("stop_run completed run_id=%s actor=%s", resolved_run_id, actor)
        return {"run_id": resolved_run_id, "status": "Stopped", "stopped_by": actor}

    def run_step(self, step_id: int, *, run_id: int | None, actor: str) -> dict[str, Any]:
        logger.info("run_step requested by=%s step_id=%s run_id=%s", actor, step_id, run_id)
        self._require_live_execution()
        resolved_run_id = self._ensure_active_run_id(run_id, actor=actor)
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
            logger.exception("run_step failed step_id=%s run_id=%s", step_id, resolved_run_id)
            raise ExecutionError(str(exc)) from exc
        logger.info(
            "run_step completed step_id=%s run_id=%s status=%s",
            step_id,
            resolved_run_id,
            result.get("execution_status"),
        )
        return {
            "run_id": resolved_run_id,
            "step_id": step_id,
            **result,
        }

    def validate_step(self, step_id: int, *, run_id: int | None, actor: str) -> dict[str, Any]:
        logger.info("validate_step requested by=%s step_id=%s run_id=%s", actor, step_id, run_id)
        self._require_live_execution()
        resolved_run_id = self._ensure_active_run_id(run_id, actor=actor)
        step = self._repo.get_step_by_id(step_id)
        if not step:
            raise ExecutionError("Step not found.")
        result = self._repo.validate_step_procedure(
            step,
            run_id=resolved_run_id,
            actor=actor,
        )
        logger.info(
            "validate_step completed step_id=%s run_id=%s status=%s",
            step_id,
            resolved_run_id,
            result.get("validation_status"),
        )
        return {
            "run_id": resolved_run_id,
            "step_id": step_id,
            **result,
        }

    def run_sequence(self, *, run_id: int | None, actor: str) -> dict[str, Any]:
        logger.info("run_sequence requested by=%s run_id=%s", actor, run_id)
        self._require_live_execution()
        resolved_run_id = self._ensure_active_run_id(run_id, actor=actor)
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
