"""Mock orchestration data shaped exactly like the SQL schema.

The UI is built against these Python structures now; in a later step the same
shapes are produced by reading the real tables — with no changes to the services
or templates. Column names mirror ``docs/planning/sql/schema.sql``.

Tables modelled here:

* ``dbo.users``                      -> :func:`get_users`
* ``orchestration.app_connections``  -> :func:`get_app_connections` / :func:`get_active_connection`
* ``orchestration.jobs``             -> :func:`get_jobs`
* ``orchestration.job_steps``        -> :func:`get_job_steps`
* ``orchestration.job_runs``         -> :func:`get_job_runs` / :func:`get_current_run`
* ``orchestration.step_runs``        -> :func:`get_step_runs`
* ``orchestration.db_execution_log`` -> :func:`get_execution_log`
* ``orchestration.run_metrics``      -> :func:`get_run_metrics`

Server and database names are NOT hardcoded in application logic — they live only
in the ``app_connections`` rows below and are resolved from there.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from werkzeug.security import generate_password_hash

from app.db.registry import PHASES, STEP_REGISTRY, job_key

JOB_ID = 1
RUN_ID = 42

EXECUTION_STATUSES = ("Success", "Running", "Pending", "Failed", "Skipped")
VALIDATION_STATUSES = ("Passed", "Failed", "Pending", "NotRequired")

# Fixed reference timestamp so the sample run renders deterministically.
_RUN_DATE = datetime(2025, 5, 31, 2, 15, 0)


# ---------------------------------------------------------------------------
# dbo.users
# ---------------------------------------------------------------------------
def get_users() -> list[dict[str, Any]]:
    """Rows shaped like ``dbo.users`` (password hashes, never plain text)."""
    return [
        {
            "user_id": 1,
            "username": "admin",
            "password_hash": generate_password_hash("admin123"),
            "role": "Admin",
            "is_active": True,
            "created_at": "2025-01-04 09:12:00",
            "last_login": "2025-05-01 08:00:00",
            "updated_at": "2025-05-01 08:00:00",
        },
        {
            "user_id": 2,
            "username": "viewer",
            "password_hash": generate_password_hash("viewer123"),
            "role": "ReadOnly",
            "is_active": True,
            "created_at": "2025-01-04 09:15:00",
            "last_login": None,
            "updated_at": None,
        },
        {
            "user_id": 3,
            "username": "jmorgan",
            "password_hash": generate_password_hash("changeme"),
            "role": "Admin",
            "is_active": True,
            "created_at": "2025-02-18 14:30:00",
            "last_login": None,
            "updated_at": None,
        },
        {
            "user_id": 4,
            "username": "areyes",
            "password_hash": generate_password_hash("changeme"),
            "role": "ReadOnly",
            "is_active": False,
            "created_at": "2025-03-22 11:05:00",
            "last_login": "2025-04-10 16:40:00",
            "updated_at": "2025-04-10 16:40:00",
        },
    ]


# ---------------------------------------------------------------------------
# orchestration.app_connections  (the only place server/db names live)
# ---------------------------------------------------------------------------
def get_app_connections() -> list[dict[str, Any]]:
    """Offline mock rows — generic hostnames; live values come from orchestration.app_connections."""
    return [
        {
            "connection_id": 1,
            "environment_name": "PRIMARY",
            "server_name": "mock-primary.local",
            "database_name": "mock_orchestration",
            "auth_type": "sql",
            "sql_username": "mock_user",
            "sql_password_hash": None,
            "description": "Mock primary environment",
            "is_active": True,
            "created_at": "2025-01-04 09:00:00",
            "updated_at": None,
        },
        {
            "connection_id": 2,
            "environment_name": "REMOTE_SQL",
            "server_name": "mock-remote.local",
            "database_name": "mock_msdb",
            "auth_type": "sql",
            "sql_username": "mock_agent",
            "sql_password_hash": None,
            "description": "Mock remote SQL environment",
            "is_active": True,
            "created_at": "2025-01-04 09:00:00",
            "updated_at": None,
        },
    ]


def get_active_connection() -> dict[str, Any]:
    """The active PRIMARY connection (used as the console's data source)."""
    connections = get_app_connections()
    for conn in connections:
        if conn["environment_name"] == "PRIMARY" and conn["is_active"]:
            return conn
    return connections[0]


def _server_for(environment_name: str) -> str:
    """Resolve a server name from ``app_connections`` (never hardcoded)."""
    for conn in get_app_connections():
        if conn["environment_name"] == environment_name:
            return conn["server_name"]
    return get_active_connection()["server_name"]


# ---------------------------------------------------------------------------
# orchestration.jobs
# ---------------------------------------------------------------------------
def get_jobs() -> list[dict[str, Any]]:
    """Rows shaped like ``orchestration.jobs``."""
    return [
        {
            "job_id": JOB_ID,
            "job_name": "RRA Month-End Orchestration",
            "description": "End-to-end month-end close orchestration.",
            "is_active": True,
            "created_at": "2025-01-04 09:00:00",
        }
    ]


# STEP_REGISTRY lives in app.db.registry (frozen proc-mapping contract).
# Mock runtime overlay — replaced by orchestration.step_runs + db_execution_log
# later. Keyed by execute proc (unique):
# (execution_status, validation_status, duration_seconds, last_message)
_RUNTIME: dict[str, tuple[str, str, int | None, str]] = {
    "orchestration.sp_send_month_end_start_email":
        ("Success", "Passed", 3, "Kickoff notification sent to close distribution list."),
    "usp_backup_bi":
        ("Success", "Passed", 214, "Full backup completed to \\\\bak\\BI\\2025-05.bak."),
    "usp_backup_RRAPS":
        ("Success", "Passed", 331, "Full backup completed (12.4 GB)."),
    "usp_backup_warehouse":
        ("Success", "Passed", 512, "Full backup completed (48.1 GB)."),
    "usp_me_01_populate_keyclient":
        ("Success", "Passed", 12, "1,284 KeyClient rows staged."),
    "usp_me_02_backup_bigfish_tables":
        ("Success", "Passed", 8, "6 BigFish tables snapshotted."),
    "usp_me_03_run_bigfish_job":
        ("Success", "Passed", 225, "BigFish load agent job succeeded."),
    "usp_me_04_populate_bigfish_tables":
        ("Success", "Passed", 34, "BigFish fact tables populated."),
    "usp_me_05_validate_bigfish_dashboard":
        ("Success", "Passed", 15, "Dashboard row counts match source."),
    "usp_me_06_populate_quadrant_tables":
        ("Success", "Passed", 22, "Quadrant tables populated."),
    "usp_me_07_run_azure_pshr_job":
        ("Success", "Passed", 138, "Azure Agent job completed on the remote server."),
    "usp_me_08_run_comptaskforce_job":
        ("Success", "Passed", 126, "CompTaskForce job completed."),
    "usp_me_09_fix_employee_role_data":
        ("Success", "Failed", 16, "Executed, but 3 employees still missing a role mapping."),
    "usp_me_10_validate_measurement_dashboard":
        ("Success", "Passed", 11, "Measurement dashboard totals reconciled."),
    "usp_me_11_insert_asofdate_rraps":
        ("Success", "Passed", 2, "As-of date set to 2025-05-31."),
    "usp_me_12_load_peoplesoft_revenue":
        ("Success", "Passed", 174, "PeopleSoft revenue loaded (58,220 rows)."),
    "usp_me_13_load_wip_tables":
        ("Success", "Passed", 96, "WIP tables loaded."),
    "usp_me_14_check_and_load_consultant_workload":
        ("Success", "Passed", 14, "Workload thresholds within tolerance."),
    "usp_me_15_run_officefull_model":
        ("Success", "Passed", 402, "OfficeFull tabular model processed."),
    "usp_me_16_run_bi_finance_job":
        ("Success", "Passed", 251, "BI finance job succeeded."),
    "usp_me_17_check_employee_role_data":
        ("Success", "Passed", 9, "Role data check passed."),
    "usp_me_18_consultant_quadrant_data_load":
        ("Running", "Pending", None, "Loading consultant quadrant data…"),
    "usp_me_19_area_manager_dashboard_load":
        ("Pending", "Pending", None, "Waiting for upstream step to complete."),
    "usp_me_20_insert_historical_tables":
        ("Pending", "Pending", None, "Queued."),
    "usp_me_d5_01_refresh_peoplesoft_revenue":
        ("Pending", "Pending", None, "Scheduled for day-5 refresh."),
    "usp_me_d5_02_run_officefull_model":
        ("Pending", "Pending", None, "Queued."),
    "orchestration.sp_send_month_end_complete_email":
        ("Pending", "Pending", None, "Sends when all phases succeed."),
}


def get_job_steps() -> list[dict[str, Any]]:
    """Rows shaped like ``orchestration.job_steps``, derived from STEP_REGISTRY.

    Server names are resolved from ``app_connections`` (never hardcoded).
    """
    rows: list[dict[str, Any]] = []
    order_by_phase: dict[str, int] = {}
    for step_id, step in enumerate(STEP_REGISTRY, start=1):
        order = order_by_phase.get(step.phase_code, 0) + 1
        order_by_phase[step.phase_code] = order
        rows.append(
            {
                "step_id": step_id,
                "job_id": JOB_ID,
                "step_name": step.step_name,
                "phase_code": step.phase_code,
                "server_name": _server_for(step.environment_name),
                "step_order": order,
                "execute_proc_name": step.execute_proc,
                "validate_proc_name": step.validate_proc,
                "is_enabled": True,
                "agent_job_name": step.agent_job,
                "agent_job_key": job_key(step.agent_job) if step.agent_job else None,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# orchestration.step_runs
# ---------------------------------------------------------------------------
def get_step_runs() -> dict[int, dict[str, Any]]:
    """Per-step runtime state keyed by ``step_id`` (shaped like ``step_runs``)."""
    runs: dict[int, dict[str, Any]] = {}
    elapsed = 0
    for step_id, step in enumerate(STEP_REGISTRY, start=1):
        exec_status, val_status, duration, message = _RUNTIME[step.execute_proc]
        started_at = None
        completed_at = None
        if exec_status in ("Success", "Failed"):
            started_at = _seconds_after(elapsed)
            elapsed += (duration or 0) + 5
            completed_at = _seconds_after(elapsed)
        elif exec_status == "Running":
            started_at = _seconds_after(elapsed)
        runs[step_id] = {
            "step_run_id": 1000 + step_id,
            "run_id": RUN_ID,
            "step_id": step_id,
            "execution_status": exec_status,
            "validation_status": val_status,
            "last_message": message,
            "duration_seconds": duration,
            "started_at": started_at,
            "completed_at": completed_at,
            "run_by": "admin",
        }
    return runs


# ---------------------------------------------------------------------------
# Validation result contract — one clean UI row per step.
#
# Returned by each usp_validate_me_XX_* proc. Validation never starts a job; it
# reads the latest db_execution_log + step_runs rows and checks the step's
# artifact, then returns PASS/FAIL with the fields the UI displays.
# ---------------------------------------------------------------------------
def get_validation_results() -> dict[int, dict[str, Any]]:
    """Per-step validation rows keyed by ``step_id``."""
    steps = {r["step_id"]: r for r in get_job_steps()}
    runs = get_step_runs()
    results: dict[int, dict[str, Any]] = {}
    for sid, run in runs.items():
        step = steps[sid]
        vs = run["validation_status"]
        if vs == "Passed":
            status = "PASS"
            expected = "Expected result present"
            matched = "Matched"
            message = "Validation passed: step result verified against expected output."
        elif vs == "Failed":
            status = "FAIL"
            expected = "0 employees missing role mapping"
            matched = "3 employees missing role mapping"
            message = "Validation failed: log reports success but the result does not match."
        else:
            status = "PENDING"
            expected = "—"
            matched = "—"
            message = "Awaiting execution."
        results[sid] = {
            "StepName": step["step_name"],
            "LatestLogStatus": run["execution_status"],
            "ExpectedItem": expected,
            "MatchedItem": matched,
            "ValidationStatus": status,
            "ResultMessage": message,
            "ValidationTime": run["completed_at"] or "—",
        }
    return results


# ---------------------------------------------------------------------------
# orchestration.db_execution_log
# ---------------------------------------------------------------------------
def get_execution_log() -> list[dict[str, Any]]:
    """Detailed log rows shaped like ``orchestration.db_execution_log`` (newest first)."""
    steps = {row["step_id"]: row for row in get_job_steps()}
    runs = get_step_runs()
    log: list[dict[str, Any]] = []
    log_id = 5000
    for step_id, run in runs.items():
        step = steps[step_id]
        if run["execution_status"] in ("Success", "Failed"):
            log.append(_log_row(log_id, step, "Step started execution", "Info",
                                 None, run["started_at"]))
            log_id += 1
            status = "Success" if run["execution_status"] == "Success" else "Failed"
            log.append(_log_row(log_id, step, run["last_message"], status,
                                 run["duration_seconds"], run["completed_at"]))
            log_id += 1
        elif run["execution_status"] == "Running":
            log.append(_log_row(log_id, step, run["last_message"], "Running",
                                 None, run["started_at"]))
            log_id += 1

    log.sort(key=lambda row: (row["logged_at"] or ""), reverse=True)
    return log


def _log_row(log_id, step, message, status, duration, logged_at) -> dict[str, Any]:
    return {
        "log_id": log_id,
        "run_id": RUN_ID,
        "phase": step["phase_code"],
        "step_name": step["step_name"],
        "message": message,
        "status": status,
        "duration_seconds": duration,
        "server_name": step["server_name"],
        "logged_at": logged_at,
    }


# ---------------------------------------------------------------------------
# orchestration.run_metrics
# ---------------------------------------------------------------------------
def get_run_metrics() -> dict[str, Any]:
    """Summary metrics for the current run, shaped like ``orchestration.run_metrics``."""
    runs = get_step_runs().values()
    total = len(runs)
    success = sum(1 for r in runs if r["execution_status"] == "Success")
    failed = sum(1 for r in runs if r["execution_status"] == "Failed")
    running = sum(1 for r in runs if r["execution_status"] == "Running")
    pending = sum(1 for r in runs if r["execution_status"] in ("Pending", "Skipped"))
    val_failed = sum(1 for r in runs if r["validation_status"] == "Failed")
    progress = round((success / total) * 100) if total else 0
    return {
        "metric_id": 1,
        "run_id": RUN_ID,
        "total_steps": total,
        "success_count": success,
        "failed_count": failed,
        "running_count": running,
        "pending_count": pending,
        "validation_failed_count": val_failed,
        "progress_pct": progress,
        "updated_at": _seconds_after(0),
    }


# ---------------------------------------------------------------------------
# orchestration.job_runs
# ---------------------------------------------------------------------------
def get_job_runs() -> list[dict[str, Any]]:
    """Run history rows shaped like ``orchestration.job_runs`` (newest first)."""
    return [
        {
            "run_id": RUN_ID,
            "job_id": JOB_ID,
            "period_label": "May 2025",
            "status": "In Progress",
            "started_at": _RUN_DATE.strftime("%b %d, %Y %I:%M %p"),
            "completed_at": None,
            "duration_seconds": None,
            "started_by": "admin",
        },
        {
            "run_id": 41,
            "job_id": JOB_ID,
            "period_label": "April 2025",
            "status": "Completed",
            "started_at": "Apr 30, 2025 02:10 AM",
            "completed_at": "Apr 30, 2025 03:32 AM",
            "duration_seconds": 4920,
            "started_by": "jmorgan",
        },
        {
            "run_id": 40,
            "job_id": JOB_ID,
            "period_label": "March 2025",
            "status": "Completed",
            "started_at": "Mar 31, 2025 02:05 AM",
            "completed_at": "Mar 31, 2025 03:28 AM",
            "duration_seconds": 4980,
            "started_by": "admin",
        },
        {
            "run_id": 39,
            "job_id": JOB_ID,
            "period_label": "February 2025",
            "status": "Failed",
            "started_at": "Feb 28, 2025 02:08 AM",
            "completed_at": "Feb 28, 2025 02:41 AM",
            "duration_seconds": 1980,
            "started_by": "admin",
        },
    ]


# ---------------------------------------------------------------------------
# orchestration.usp_GetMonitoredAgentJobs
#
# Only the monitored jobs below are tracked — no unrelated SQL Agent jobs. Job
# names and the two servers are the only "hardcoded" identifiers, as required.
# (job_name, environment_name, enabled, last_status, last_run, next_run,
#  running, alt_name)
# ---------------------------------------------------------------------------
_MONITORED_JOBS: list[tuple[str, str, bool, str, str, str | None, bool, str | None]] = [
    ("zz-Load Big Fish Dashboard Data 2016", "PRIMARY", True, "Succeeded",
     "05/31 02:19 AM", "06/01 02:15 AM", False, None),
    ("zz_Load CompTaskForce Data 2016", "PRIMARY", True, "Succeeded",
     "05/31 02:30 AM", "06/01 02:25 AM", False, None),
    ("RRAPS_Populate Consultant_workload table - Monthly Load", "PRIMARY", True, "Succeeded",
     "05/31 02:33 AM", "06/01 02:30 AM", False, None),
    ("BI_FINANCE_DATA", "PRIMARY", True, "Succeeded",
     "05/31 02:41 AM", "06/01 02:40 AM", False, None),
    ("Azure_PSHRDataLoads", "REMOTE_SQL", True, "Succeeded",
     "05/31 02:22 AM", "06/01 02:20 AM", False, "AzurePSHRDataLoads_TEST"),
]


def get_monitored_agent_jobs() -> list[dict[str, Any]]:
    """Rows shaped like the ``orchestration.usp_GetMonitoredAgentJobs`` result set.

    Server names are resolved from ``app_connections`` (never hardcoded).
    """
    rows: list[dict[str, Any]] = []
    for name, environment_name, enabled, status, last_run, next_run, running, alt in _MONITORED_JOBS:
        rows.append(
            {
                "job_name": name,
                "alt_name": alt,
                "job_key": job_key(name),
                "is_enabled": enabled,
                "last_run_status": status,
                "last_run_time": last_run,
                "next_run_time": next_run,
                "is_running": running,
                "server_name": _server_for(environment_name),
                "environment_name": environment_name,
            }
        )
    return rows


def get_current_run() -> dict[str, Any]:
    """The active ``job_runs`` row, enriched with the job name."""
    current = get_job_runs()[0]
    return {
        "run_id": current["run_id"],
        "job_id": current["job_id"],
        "job_name": get_jobs()[0]["job_name"],
        "period_label": current["period_label"],
        "status": current["status"],
        "started_at": current["started_at"],
        "last_run_at": current["started_at"],
    }


def _seconds_after(seconds: int) -> str:
    return (_RUN_DATE + timedelta(seconds=seconds)).strftime("%m/%d %I:%M:%S %p")
