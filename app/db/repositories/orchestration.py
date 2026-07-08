"""Orchestration repository — jobs, steps, runs, logs, metrics."""

from __future__ import annotations

from typing import Any

from app.db.formatters import format_log_datetime, format_run_datetime, format_timestamp
from app.db.registry import PHASES, agent_job_for_proc, job_key
from app.db.repositories.base import query_primary, use_mock_data


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
    def get_phases(self) -> list[dict[str, str]]:
        return PHASES

    def get_jobs(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_jobs()

        rows = query_primary(
            """
            SELECT job_id, job_name, description, is_active, created_at
            FROM orchestration.jobs
            WHERE is_active = 1
            ORDER BY job_id
            """
        )
        return [
            {
                "job_id": row["job_id"],
                "job_name": row["job_name"],
                "description": row.get("description") or "",
                "is_active": bool(row["is_active"]),
                "created_at": format_timestamp(row.get("created_at")),
            }
            for row in rows
        ]

    def get_job_steps(self) -> list[dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_job_steps()

        rows = query_primary(
            """
            SELECT
                step_id,
                job_id,
                step_name,
                phase_code,
                server_name,
                step_order,
                execute_proc_name,
                validate_proc_name,
                is_enabled
            FROM orchestration.job_steps
            WHERE is_enabled = 1
            ORDER BY phase_code, step_order, step_id
            """
        )
        steps = []
        for row in rows:
            agent_job = agent_job_for_proc(row["execute_proc_name"])
            steps.append(
                {
                    "step_id": row["step_id"],
                    "job_id": row["job_id"],
                    "step_name": row["step_name"],
                    "phase_code": row["phase_code"],
                    "server_name": row["server_name"],
                    "step_order": row["step_order"],
                    "execute_proc_name": row["execute_proc_name"],
                    "validate_proc_name": row["validate_proc_name"],
                    "is_enabled": bool(row["is_enabled"]),
                    "agent_job_name": agent_job,
                    "agent_job_key": job_key(agent_job) if agent_job else None,
                }
            )
        return steps

    def get_current_run_id(self) -> int | None:
        rows = query_primary(
            """
            SELECT TOP 1 run_id
            FROM orchestration.job_runs
            ORDER BY started_at DESC, run_id DESC
            """
        )
        return int(rows[0]["run_id"]) if rows else None

    def get_step_runs(self, run_id: int | None = None) -> dict[int, dict[str, Any]]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_step_runs()

        if run_id is None:
            run_id = self.get_current_run_id()
        if run_id is None:
            return {}

        rows = query_primary(
            """
            SELECT
                step_run_id,
                run_id,
                step_id,
                execution_status,
                validation_status,
                last_message,
                duration_seconds,
                started_at,
                completed_at,
                run_by
            FROM orchestration.step_runs
            WHERE run_id = ?
            """,
            (run_id,),
        )
        runs: dict[int, dict[str, Any]] = {}
        for row in rows:
            runs[int(row["step_id"])] = {
                "step_run_id": row["step_run_id"],
                "run_id": row["run_id"],
                "step_id": row["step_id"],
                "execution_status": row["execution_status"],
                "validation_status": row["validation_status"],
                "last_message": row.get("last_message") or "",
                "duration_seconds": row.get("duration_seconds"),
                "started_at": format_log_datetime(row.get("started_at")),
                "completed_at": format_log_datetime(row.get("completed_at")),
                "run_by": row.get("run_by"),
            }
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
                period_label,
                status,
                started_at,
                completed_at,
                duration_seconds,
                started_by
            FROM orchestration.job_runs
            ORDER BY started_at DESC, run_id DESC
            """
        )
        return [
            {
                "run_id": row["run_id"],
                "job_id": row["job_id"],
                "period_label": row["period_label"],
                "status": row["status"],
                "started_at": format_run_datetime(row.get("started_at")),
                "completed_at": format_run_datetime(row.get("completed_at")),
                "duration_seconds": row.get("duration_seconds"),
                "started_by": row.get("started_by") or "",
            }
            for row in rows
        ]

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

        rows = query_primary(
            f"""
            SELECT TOP ({int(limit)})
                log_id,
                run_id,
                phase,
                step_name,
                message,
                status,
                duration_seconds,
                server_name,
                logged_at
            FROM orchestration.db_execution_log
            ORDER BY logged_at DESC, log_id DESC
            """
        )
        return [
            {
                "log_id": row["log_id"],
                "run_id": row["run_id"],
                "phase": row["phase"],
                "step_name": row["step_name"],
                "message": row["message"],
                "status": row["status"],
                "duration_seconds": row.get("duration_seconds"),
                "server_name": row["server_name"],
                "logged_at": format_log_datetime(row.get("logged_at")),
            }
            for row in rows
        ]

    def get_run_metrics(self) -> dict[str, Any]:
        if use_mock_data():
            from app.dashboard import mock_data

            return mock_data.get_run_metrics()

        run_id = self.get_current_run_id()
        if run_id is not None:
            rows = query_primary(
                """
                SELECT TOP 1
                    metric_id,
                    run_id,
                    total_steps,
                    success_count,
                    failed_count,
                    running_count,
                    pending_count,
                    validation_failed_count,
                    progress_pct,
                    updated_at
                FROM orchestration.run_metrics
                WHERE run_id = ?
                ORDER BY updated_at DESC
                """,
                (run_id,),
            )
            if rows:
                row = rows[0]
                return {
                    "metric_id": row["metric_id"],
                    "run_id": row["run_id"],
                    "total_steps": row["total_steps"],
                    "success_count": row["success_count"],
                    "failed_count": row["failed_count"],
                    "running_count": row["running_count"],
                    "pending_count": row["pending_count"],
                    "validation_failed_count": row["validation_failed_count"],
                    "progress_pct": row["progress_pct"],
                    "updated_at": format_log_datetime(row.get("updated_at")),
                }

        step_runs = self.get_step_runs(run_id).values()
        total = len(step_runs)
        success = sum(1 for r in step_runs if r["execution_status"] == "Success")
        failed = sum(1 for r in step_runs if r["execution_status"] == "Failed")
        running = sum(1 for r in step_runs if r["execution_status"] == "Running")
        pending = sum(1 for r in step_runs if r["execution_status"] in ("Pending", "Skipped"))
        val_failed = sum(1 for r in step_runs if r["validation_status"] == "Failed")
        progress = round((success / total) * 100) if total else 0
        return {
            "metric_id": 1,
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
