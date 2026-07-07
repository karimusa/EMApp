"""Orchestration repository — jobs, steps, runs, logs, metrics."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from app.db.connection_manager import get_connection_manager


class OrchestrationRepository:
    def get_job_steps(self, phase: Optional[str] = None) -> list[dict[str, Any]]:
        if self._testing():
            steps = self._mock_steps()
            if phase:
                return [s for s in steps if s["phase"] == phase]
            return steps

        sql = """
            SELECT
                js.step_id,
                js.job_id,
                j.job_name,
                js.step_name,
                js.phase,
                js.server_name,
                js.step_order,
                js.execute_proc_name,
                js.validate_proc_name,
                js.is_enabled,
                sr.execution_status,
                sr.validation_status,
                sr.last_message,
                sr.started_at,
                sr.completed_at
            FROM orchestration.job_steps js
            INNER JOIN orchestration.jobs j ON j.job_id = js.job_id
            LEFT JOIN (
                SELECT step_id, execution_status, validation_status, last_message,
                       started_at, completed_at,
                       ROW_NUMBER() OVER (PARTITION BY step_id ORDER BY step_run_id DESC) AS rn
                FROM orchestration.step_runs
            ) sr ON sr.step_id = js.step_id AND sr.rn = 1
            WHERE js.is_enabled = 1
        """
        params: tuple = ()
        if phase:
            sql += " AND js.phase = ?"
            params = (phase,)
        sql += " ORDER BY js.phase, js.step_order, js.step_name"
        return self._query(sql, params)

    def get_current_run(self) -> Optional[dict[str, Any]]:
        if self._testing():
            return {
                "job_run_id": 1001,
                "job_id": 1,
                "job_name": "Month-End Close",
                "run_status": "In Progress",
                "started_at": datetime.now(UTC),
                "completed_at": None,
                "current_phase": "MAIN",
                "progress_pct": 42,
            }

        sql = """
            SELECT TOP 1
                jr.job_run_id,
                jr.job_id,
                j.job_name,
                jr.run_status,
                jr.started_at,
                jr.completed_at,
                jr.current_phase,
                jr.progress_pct
            FROM orchestration.job_runs jr
            INNER JOIN orchestration.jobs j ON j.job_id = jr.job_id
            ORDER BY jr.job_run_id DESC
        """
        rows = self._query(sql)
        return rows[0] if rows else None

    def get_execution_log(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._testing():
            return self._mock_logs()

        sql = """
            SELECT TOP (?)
                log_id,
                step_name,
                phase,
                log_level,
                message,
                logged_at
            FROM orchestration.db_execution_log
            ORDER BY logged_at DESC
        """
        return self._query(sql, (limit,))

    def get_run_metrics(self) -> list[dict[str, Any]]:
        if self._testing():
            return [
                {"metric_name": "Steps Completed", "metric_value": "8", "metric_unit": ""},
                {"metric_name": "Steps Failed", "metric_value": "0", "metric_unit": ""},
                {"metric_name": "Validations Passed", "metric_value": "7", "metric_unit": ""},
                {"metric_name": "Elapsed Minutes", "metric_value": "34", "metric_unit": "min"},
            ]

        sql = """
            SELECT TOP 10 metric_name, metric_value, metric_unit, recorded_at
            FROM orchestration.run_metrics
            ORDER BY recorded_at DESC
        """
        return self._query(sql)

    def execute_step(self, step_id: int, username: str) -> dict[str, Any]:
        if self._testing():
            return {
                "success": True,
                "message": f"Step {step_id} executed successfully (mock).",
                "execution_status": "Completed",
            }

        step = self._get_step(step_id)
        proc = step["execute_proc_name"]
        with get_connection_manager().connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(f"EXEC {proc} @step_id = ?, @run_by = ?", (step_id, username))
            row = cursor.fetchone()
            db.commit()
            if row:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
            return {"success": True, "message": f"Step {step['step_name']} executed."}

    def validate_step(self, step_id: int, username: str) -> dict[str, Any]:
        if self._testing():
            return {
                "step_name": f"Step {step_id}",
                "latest_log_status": "Completed",
                "expected_item": "1000",
                "matched_item_type": "row_count",
                "pass_fail": "PASS",
                "result_message": "Validation passed (mock).",
                "validation_time": datetime.now(UTC),
            }

        step = self._get_step(step_id)
        proc = step["validate_proc_name"]
        with get_connection_manager().connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(f"EXEC {proc} @step_id = ?, @validated_by = ?", (step_id, username))
            row = cursor.fetchone()
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row)) if row else {}

    def _get_step(self, step_id: int) -> dict[str, Any]:
        sql = """
            SELECT step_id, step_name, execute_proc_name, validate_proc_name
            FROM orchestration.job_steps
            WHERE step_id = ?
        """
        rows = self._query(sql, (step_id,))
        if not rows:
            raise ValueError(f"Step {step_id} not found")
        return rows[0]

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with get_connection_manager().connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _testing(self) -> bool:
        try:
            return get_connection_manager()._config.get("TESTING", False)
        except RuntimeError:
            return False

    def _mock_steps(self) -> list[dict[str, Any]]:
        phases = {
            "PRE": ["Close Prep Checks", "Lock Period"],
            "MAIN": ["GL Posting", "Subledger Reconcile", "Intercompany"],
            "BI": ["Cube Process", "Report Refresh"],
            "DAY5": ["Day5 Adjustments", "Accrual True-up"],
            "POST": ["Final Validation", "Notify Stakeholders"],
        }
        steps = []
        sid = 1
        for phase, names in phases.items():
            server = "SPUS001BDBEXT" if phase != "BI" else "SPAZ001EDM10"
            for order, name in enumerate(names, 1):
                steps.append(
                    {
                        "step_id": sid,
                        "job_id": 1,
                        "job_name": "Month-End Close",
                        "step_name": name,
                        "phase": phase,
                        "server_name": server,
                        "step_order": order,
                        "execute_proc_name": f"orchestration.usp_Execute_{name.replace(' ', '')}",
                        "validate_proc_name": f"orchestration.usp_Validate_{name.replace(' ', '')}",
                        "is_enabled": True,
                        "execution_status": "Pending" if sid > 3 else "Completed",
                        "validation_status": "Pending" if sid > 2 else "Passed",
                        "last_message": "Ready" if sid > 3 else "Completed successfully",
                        "started_at": None,
                        "completed_at": None,
                    }
                )
                sid += 1
        return steps

    def _mock_logs(self) -> list[dict[str, Any]]:
        return [
            {
                "log_id": 3,
                "step_name": "GL Posting",
                "phase": "MAIN",
                "log_level": "INFO",
                "message": "GL posting completed — 12,450 entries processed.",
                "logged_at": datetime.now(UTC),
            },
            {
                "log_id": 2,
                "step_name": "Lock Period",
                "phase": "PRE",
                "log_level": "INFO",
                "message": "Period 2026-06 locked successfully.",
                "logged_at": datetime.now(UTC),
            },
            {
                "log_id": 1,
                "step_name": "Close Prep Checks",
                "phase": "PRE",
                "log_level": "INFO",
                "message": "All pre-close checks passed.",
                "logged_at": datetime.now(UTC),
            },
        ]
