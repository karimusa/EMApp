"""Orchestration repository — jobs, steps, runs, logs, metrics."""

from __future__ import annotations

import logging
from typing import Any

from app.db.live_schema import (
    build_step_run_from_execution_log_row,
    normalize_execution_log_row,
    normalize_job_row,
    normalize_job_run_row,
    normalize_job_step_row,
    normalize_run_metrics_row,
    normalize_step_run_row,
)
from app.db.registry import PHASES
from app.db.repositories.base import exec_connection, exec_primary, query_connection, query_primary, query_scalar_primary, use_mock_data

logger = logging.getLogger(__name__)

_STEP_RUNS_SQL = """
    SELECT
        step_run_id,
        run_id,
        step_id,
        start_time,
        end_time,
        status,
        log_message,
        duration_sec,
        approval_status,
        approved_by,
        approved_at,
        error_message,
        log_ref_id,
        step_order,
        step_name,
        phase_code,
        retry_attempt
    FROM orchestration.step_runs
"""

_EXECUTION_LOG_SQL = """
    SELECT TOP ({limit})
        log_id,
        process_name,
        database_name,
        step,
        status,
        message,
        log_time
    FROM orchestration.db_execution_log
    ORDER BY log_time DESC, log_id DESC
"""


def build_validation_results(
    steps: list[dict[str, Any]], step_runs: dict[int, dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """Map step_runs validation_status into the UI validation contract."""
    results: dict[int, dict[str, Any]] = {}
    steps_by_id = {s["step_id"]: s for s in steps}

    for step_id, run in step_runs.items():
        step = steps_by_id.get(step_id, {})
        vs = run.get("validation_status", "Pending")
        exec_status = run.get("execution_status", "Pending")

        if vs == "Passed":
            status = "PASS"
            expected = "Expected result present"
            matched = "Matched"
            message = "Validation passed: step result verified against expected output."
        elif vs == "Failed":
            status = "FAIL"
            expected = run.get("expected_item") or "Expected result"
            matched = run.get("matched_item") or "Mismatch"
            message = run.get("validation_message") or (
                "Validation failed: log reports success but the result does not match."
            )
        else:
            status = "PENDING"
            expected = "—"
            matched = "—"
            message = "Awaiting execution."

        val_time = run.get("validation_time") or run.get("completed_at") or "—"
        results[step_id] = {
            "StepName": step.get("step_name", ""),
            "LatestLogStatus": exec_status,
            "ExpectedItem": expected,
            "MatchedItem": matched,
            "ValidationStatus": status,
            "ResultMessage": message,
            "ValidationTime": val_time,
        }
    return results


class OrchestrationRepository:
    def __init__(self) -> None:
        self.last_step_run_source = "unknown"

    def get_phases(self) -> list[dict[str, str]]:
        return PHASES

    def get_jobs(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_jobs()

        rows = query_primary(
            """
            SELECT job_id, job_name, is_active, created_at
            FROM orchestration.jobs
            WHERE is_active = 1
            ORDER BY job_id
            """
        )
        return [normalize_job_row(row) for row in rows]

    def get_job_steps(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_job_steps()

        rows = query_primary(
            """
            SELECT
                step_id,
                job_id,
                step_order,
                step_name,
                parameters,
                is_active,
                step_type,
                command,
                server_name,
                requires_approval,
                on_failure_action,
                retry_count,
                retry_delay_sec,
                execution_mode,
                phase_code
            FROM orchestration.job_steps
            WHERE is_active = 1
            ORDER BY phase_code, step_order, step_id
            """
        )
        return [normalize_job_step_row(row) for row in rows]

    def get_current_run_id(self) -> int | None:
        rows = query_primary(
            """
            SELECT TOP 1 run_id
            FROM orchestration.job_runs
            ORDER BY start_time DESC, run_id DESC
            """
        )
        if rows:
            return int(rows[0]["run_id"])

        rows = query_primary(
            """
            SELECT TOP 1 run_id
            FROM orchestration.step_runs
            ORDER BY step_run_id DESC
            """
        )
        return int(rows[0]["run_id"]) if rows else None

    def _rows_to_step_runs(self, rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        runs: dict[int, dict[str, Any]] = {}
        for row in rows:
            normalized = normalize_step_run_row(row)
            normalized["data_source"] = "orchestration.step_runs"
            runs[int(row["step_id"])] = normalized
        return runs

    def _fetch_step_runs_for_run(self, run_id: int) -> dict[int, dict[str, Any]]:
        rows = query_primary(
            f"""
            {_STEP_RUNS_SQL}
            WHERE run_id = ?
            """,
            (run_id,),
        )
        return self._rows_to_step_runs(rows)

    def _fetch_latest_step_runs_by_step(self) -> dict[int, dict[str, Any]]:
        rows = query_primary(
            f"""
            SELECT
                sr.step_run_id,
                sr.run_id,
                sr.step_id,
                sr.start_time,
                sr.end_time,
                sr.status,
                sr.log_message,
                sr.duration_sec,
                sr.approval_status,
                sr.approved_by,
                sr.approved_at,
                sr.error_message,
                sr.log_ref_id,
                sr.step_order,
                sr.step_name,
                sr.phase_code,
                sr.retry_attempt
            FROM orchestration.step_runs sr
            INNER JOIN (
                SELECT step_id, MAX(step_run_id) AS max_step_run_id
                FROM orchestration.step_runs
                GROUP BY step_id
            ) latest ON sr.step_run_id = latest.max_step_run_id
            """
        )
        return self._rows_to_step_runs(rows)

    @staticmethod
    def _step_match_keys(step: dict[str, Any]) -> set[str]:
        keys = {str(step.get("step_name") or "").strip().lower()}
        proc = str(step.get("execute_proc_name") or "").strip().lower()
        if proc:
            keys.add(proc)
            keys.add(proc.rsplit(".", 1)[-1])
        return {key for key in keys if key}

    @classmethod
    def _execution_log_matches_step(
        cls,
        step: dict[str, Any],
        *,
        log_step: str,
        log_process: str,
    ) -> bool:
        step_keys = cls._step_match_keys(step)
        if not step_keys:
            return False
        candidates = {log_step.lower(), log_process.lower()}
        if log_process:
            candidates.add(log_process.rsplit(".", 1)[-1].lower())
        return bool(step_keys & {value for value in candidates if value})

    def _fetch_execution_log_rows(self, limit: int = 500) -> list[dict[str, Any]]:
        rows = query_primary(_EXECUTION_LOG_SQL.format(limit=int(limit)))
        return [normalize_execution_log_row(row) for row in rows]

    def _fetch_step_runs_from_execution_log(
        self,
        steps: list[dict[str, Any]],
        *,
        limit: int = 500,
    ) -> dict[int, dict[str, Any]]:
        rows = query_primary(_EXECUTION_LOG_SQL.format(limit=int(limit)))
        runs: dict[int, dict[str, Any]] = {}

        for row in rows:
            log_step = str(row.get("step") or "").strip()
            log_process = str(row.get("process_name") or "").strip()
            for step in steps:
                step_id = int(step["step_id"])
                if step_id in runs:
                    continue
                if self._execution_log_matches_step(
                    step,
                    log_step=log_step,
                    log_process=log_process,
                ):
                    runs[step_id] = build_step_run_from_execution_log_row(
                        row,
                        step_id=step_id,
                    )
        return runs

    def get_step_runs(self, run_id: int | None = None) -> dict[int, dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            self.last_step_run_source = "mock_data"
            return mock_data.get_step_runs()

        steps = self.get_job_steps()
        source = "none"
        runs: dict[int, dict[str, Any]] = {}

        if run_id is None:
            run_id = self.get_current_run_id()
        if run_id is not None:
            runs = self._fetch_step_runs_for_run(run_id)
            if runs:
                source = f"orchestration.step_runs (run_id={run_id})"

        if not runs:
            runs = self._fetch_latest_step_runs_by_step()
            if runs:
                source = "orchestration.step_runs (latest per step)"

        if not runs and steps:
            runs = self._fetch_step_runs_from_execution_log(steps)
            if runs:
                source = "orchestration.db_execution_log"

        self.last_step_run_source = source
        logger.info(
            "Dashboard step status source=%s step_cards=%d step_runs=%d data_mode=%s",
            source,
            len(steps),
            len(runs),
            "mock" if use_mock_data() else "live",
        )
        return runs

    def get_validation_results(self) -> dict[int, dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_validation_results()

        return build_validation_results(self.get_job_steps(), self.get_step_runs())

    def get_job_runs(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_job_runs()

        rows = query_primary(
            """
            SELECT
                run_id,
                job_id,
                start_time,
                end_time,
                status,
                triggered_by,
                error_message,
                phase_code,
                run_name
            FROM orchestration.job_runs
            ORDER BY start_time DESC, run_id DESC
            """
        )
        return [normalize_job_run_row(row) for row in rows]

    def get_current_run(self) -> dict[str, Any]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_current_run()

        runs = self.get_job_runs()
        if not runs:
            return {
                "run_id": None,
                "job_id": None,
                "job_name": "",
                "period_label": "—",
                "status": "Pending",
                "started_at": "—",
                "last_run_at": "—",
            }

        current = runs[0]
        jobs = self.get_jobs()
        job_name = jobs[0]["job_name"] if jobs else ""
        return {
            "run_id": current["run_id"],
            "job_id": current["job_id"],
            "job_name": job_name,
            "period_label": current["period_label"],
            "status": current["status"],
            "started_at": current["started_at"],
            "last_run_at": current["started_at"],
        }

    def get_execution_log(self, limit: int = 500) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_execution_log()

        return self._fetch_execution_log_rows(limit=limit)

    def get_run_metrics(self) -> dict[str, Any]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_run_metrics()

        run_id = self.get_current_run_id()
        if run_id is not None:
            rows = query_primary(
                """
                SELECT TOP 1
                    run_id,
                    total_steps,
                    success_count,
                    failed_count,
                    duration_sec
                FROM orchestration.run_metrics
                WHERE run_id = ?
                """,
                (run_id,),
            )
            if rows:
                return normalize_run_metrics_row(rows[0])

        step_runs = list(self.get_step_runs().values())
        steps = self.get_job_steps()
        total = len(steps) if steps else len(step_runs)
        success = sum(1 for r in step_runs if r["execution_status"] == "Success")
        failed = sum(1 for r in step_runs if r["execution_status"] == "Failed")
        running = sum(1 for r in step_runs if r["execution_status"] == "Running")
        pending = max(total - success - failed - running, 0)
        val_failed = sum(1 for r in step_runs if r["validation_status"] == "Failed")
        progress = round((success / total) * 100) if total else 0
        return {
            "metric_id": run_id,
            "run_id": run_id,
            "total_steps": total,
            "success_count": success,
            "failed_count": failed,
            "running_count": running,
            "pending_count": pending,
            "validation_failed_count": val_failed,
            "progress_pct": progress,
            "updated_at": "—",
        }

    def get_step_by_id(self, step_id: int) -> dict[str, Any] | None:
        if use_mock_data():
            from app.dashboard import mock_data

            for step in mock_data.get_job_steps():
                if int(step["step_id"]) == int(step_id):
                    return step
            return None

        rows = query_primary(
            """
            SELECT
                step_id,
                job_id,
                step_order,
                step_name,
                parameters,
                is_active,
                step_type,
                command,
                server_name,
                requires_approval,
                on_failure_action,
                retry_count,
                retry_delay_sec,
                execution_mode,
                phase_code
            FROM orchestration.job_steps
            WHERE step_id = ?
            """,
            (step_id,),
        )
        return normalize_job_step_row(rows[0]) if rows else None

    def create_job_run(self, *, job_id: int, triggered_by: str, run_name: str) -> int:
        run_id = query_scalar_primary(
            """
            INSERT INTO orchestration.job_runs (
                job_id, start_time, status, triggered_by, run_name, phase_code
            )
            OUTPUT INSERTED.run_id
            VALUES (?, SYSUTCDATETIME(), 'Running', ?, ?, 'PRE')
            """,
            (job_id, triggered_by, run_name),
        )
        if run_id is None:
            raise RuntimeError("Failed to create job run.")
        return int(run_id)

    def stop_job_run(self, run_id: int) -> None:
        exec_primary(
            """
            UPDATE orchestration.job_runs
            SET status = 'Stopped',
                end_time = SYSUTCDATETIME()
            WHERE run_id = ?
              AND status IN ('Running', 'In Progress', 'Pending')
            """,
            (run_id,),
        )
        exec_primary(
            """
            UPDATE orchestration.step_runs
            SET status = 'Skipped',
                end_time = SYSUTCDATETIME(),
                log_message = COALESCE(log_message, 'Run stopped by operator.')
            WHERE run_id = ?
              AND status IN ('Running', 'Pending')
            """,
            (run_id,),
        )

    def _insert_execution_log(
        self,
        *,
        run_id: int,
        step: dict[str, Any],
        status: str,
        message: str,
    ) -> None:
        exec_primary(
            """
            INSERT INTO orchestration.db_execution_log (
                process_name, database_name, step, status, message, log_time
            )
            VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME())
            """,
            (
                step.get("execute_proc_name") or step.get("step_name"),
                step.get("server_name") or step.get("environment_name") or "PRIMARY",
                step.get("step_name"),
                status,
                message,
            ),
        )

    def _upsert_step_run_running(
        self,
        *,
        run_id: int,
        step: dict[str, Any],
        actor: str,
    ) -> None:
        exec_primary(
            """
            IF EXISTS (
                SELECT 1 FROM orchestration.step_runs
                WHERE run_id = ? AND step_id = ?
            )
                UPDATE orchestration.step_runs
                SET status = 'Running',
                    start_time = SYSUTCDATETIME(),
                    end_time = NULL,
                    log_message = 'Execution started.',
                    step_order = ?,
                    step_name = ?,
                    phase_code = ?,
                    approved_by = ?
                WHERE run_id = ? AND step_id = ?
            ELSE
                INSERT INTO orchestration.step_runs (
                    run_id, step_id, start_time, status, log_message,
                    step_order, step_name, phase_code, approved_by
                )
                VALUES (?, ?, SYSUTCDATETIME(), 'Running', 'Execution started.',
                        ?, ?, ?, ?)
            """,
            (
                run_id,
                step["step_id"],
                step.get("step_order") or 0,
                step["step_name"],
                step.get("phase_code") or "",
                actor,
                run_id,
                step["step_id"],
                run_id,
                step["step_id"],
                step.get("step_order") or 0,
                step["step_name"],
                step.get("phase_code") or "",
                actor,
            ),
        )

    def _finalize_step_run(
        self,
        *,
        run_id: int,
        step_id: int,
        status: str,
        message: str,
        approval_status: str | None = None,
    ) -> None:
        if approval_status:
            exec_primary(
                """
                UPDATE orchestration.step_runs
                SET status = ?,
                    end_time = SYSUTCDATETIME(),
                    log_message = ?,
                    approval_status = ?
                WHERE run_id = ? AND step_id = ?
                """,
                (status, message, approval_status, run_id, step_id),
            )
        else:
            exec_primary(
                """
                UPDATE orchestration.step_runs
                SET status = ?,
                    end_time = SYSUTCDATETIME(),
                    log_message = ?
                WHERE run_id = ? AND step_id = ?
                """,
                (status, message, run_id, step_id),
            )

    @staticmethod
    def _proc_sql(proc_name: str) -> str:
        import re

        name = (proc_name or "").strip()
        if not name:
            raise ValueError("Stored procedure name is required.")
        if not re.match(r"^[A-Za-z0-9_.]+$", name):
            raise ValueError(f"Invalid procedure name: {name}")
        return f"EXEC {name}"

    def execute_step_procedure(
        self,
        step: dict[str, Any],
        *,
        run_id: int,
        actor: str,
    ) -> dict[str, Any]:
        proc_name = step.get("execute_proc_name") or ""
        environment_name = step.get("environment_name") or "PRIMARY"
        if not proc_name:
            raise ValueError(f"Step {step['step_id']} has no execute procedure configured.")

        self._upsert_step_run_running(run_id=run_id, step=step, actor=actor)
        sql = self._proc_sql(proc_name)
        try:
            query_connection(environment_name, sql)
            message = f"{step['step_name']} completed successfully."
            status = "Success"
            self._finalize_step_run(
                run_id=run_id,
                step_id=int(step["step_id"]),
                status=status,
                message=message,
            )
            self._insert_execution_log(
                run_id=run_id,
                step=step,
                status=status,
                message=message,
            )
            return {"execution_status": status, "message": message}
        except Exception as exc:
            message = str(exc)
            status = "Failed"
            self._finalize_step_run(
                run_id=run_id,
                step_id=int(step["step_id"]),
                status=status,
                message=message,
            )
            self._insert_execution_log(
                run_id=run_id,
                step=step,
                status=status,
                message=message,
            )
            raise

    def validate_step_procedure(
        self,
        step: dict[str, Any],
        *,
        run_id: int,
        actor: str,
    ) -> dict[str, Any]:
        proc_name = step.get("validate_proc_name") or ""
        environment_name = step.get("environment_name") or "PRIMARY"
        if not proc_name:
            raise ValueError(f"Step {step['step_id']} has no validate procedure configured.")

        sql = self._proc_sql(proc_name)
        rows = query_connection(environment_name, sql)
        approval_status = "Passed"
        message = f"{step['step_name']} validation passed."
        if rows:
            row = rows[0]
            raw_status = (
                row.get("ValidationStatus")
                or row.get("pass_fail")
                or row.get("validation_status")
                or row.get("status")
            )
            if raw_status:
                text = str(raw_status).strip().upper()
                if text in {"FAIL", "FAILED", "REJECTED"}:
                    approval_status = "Failed"
                    message = (
                        row.get("ResultMessage")
                        or row.get("result_message")
                        or row.get("message")
                        or "Validation failed."
                    )
                else:
                    message = (
                        row.get("ResultMessage")
                        or row.get("result_message")
                        or row.get("message")
                        or message
                    )

        self._finalize_step_run(
            run_id=run_id,
            step_id=int(step["step_id"]),
            status="Success",
            message=message,
            approval_status=approval_status,
        )
        return {
            "validation_status": "Passed" if approval_status == "Passed" else "Failed",
            "message": message,
        }
