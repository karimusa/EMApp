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

import re
from datetime import datetime, timedelta
from typing import Any

from werkzeug.security import generate_password_hash

JOB_ID = 1
RUN_ID = 42

# Ordered phases + display labels for the UI tabs (matches the job_steps CHECK).
PHASES: list[dict[str, str]] = [
    {"key": "PRE", "label": "PRE"},
    {"key": "MAIN", "label": "MAIN"},
    {"key": "BI", "label": "BI"},
    {"key": "DAY5", "label": "DAY 5"},
    {"key": "POST", "label": "POST"},
]

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
            "updated_at": "2025-05-01 08:00:00",
        },
        {
            "user_id": 2,
            "username": "viewer",
            "password_hash": generate_password_hash("viewer123"),
            "role": "ReadOnly",
            "is_active": True,
            "created_at": "2025-01-04 09:15:00",
            "updated_at": None,
        },
        {
            "user_id": 3,
            "username": "jmorgan",
            "password_hash": generate_password_hash("changeme"),
            "role": "Admin",
            "is_active": True,
            "created_at": "2025-02-18 14:30:00",
            "updated_at": None,
        },
        {
            "user_id": 4,
            "username": "areyes",
            "password_hash": generate_password_hash("changeme"),
            "role": "ReadOnly",
            "is_active": False,
            "created_at": "2025-03-22 11:05:00",
            "updated_at": "2025-04-10 16:40:00",
        },
    ]


# ---------------------------------------------------------------------------
# orchestration.app_connections  (the only place server/db names live)
# ---------------------------------------------------------------------------
def get_app_connections() -> list[dict[str, Any]]:
    """Rows shaped like ``orchestration.app_connections``."""
    return [
        {
            "connection_id": 1,
            "connection_name": "PRIMARY",
            "server_name": "SPUS001BDBEXT",
            "database_name": "MonthEndOrchestrationDB",
            "username": "svc_orchestration",
            "password_encrypted": "gAAAAAB...redacted",
            "password_plain": None,
            "driver": "ODBC Driver 18 for SQL Server",
            "trust_server_certificate": "yes",
            "is_active": True,
            "created_at": "2025-01-04 09:00:00",
            "updated_at": None,
        },
        {
            "connection_id": 2,
            "connection_name": "REMOTE_SQL",
            "server_name": "SPAZ001EDM10",
            "database_name": "msdb",
            "username": "svc_agent",
            "password_encrypted": "gAAAAAB...redacted",
            "password_plain": None,
            "driver": "ODBC Driver 18 for SQL Server",
            "trust_server_certificate": "yes",
            "is_active": True,
            "created_at": "2025-01-04 09:00:00",
            "updated_at": None,
        },
    ]


def get_active_connection() -> dict[str, Any]:
    """The active PRIMARY connection (used as the console's data source)."""
    connections = get_app_connections()
    for conn in connections:
        if conn["connection_name"] == "PRIMARY" and conn["is_active"]:
            return conn
    return connections[0]


def _server_for(connection_name: str) -> str:
    """Resolve a server name from ``app_connections`` (never hardcoded)."""
    for conn in get_app_connections():
        if conn["connection_name"] == connection_name:
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


# ---------------------------------------------------------------------------
# Internal step catalogue.
#
# Each tuple: (step_name, execution_status, validation_status, duration_seconds,
#              last_message, connection_name)
# connection_name references orchestration.app_connections.connection_name.
# ---------------------------------------------------------------------------
_STEPS: dict[str, list[tuple[str, str, str, int | None, str, str]]] = {
    "PRE": [
        ("Send Start Email", "Success", "Passed", 3,
         "Kickoff notification sent to close distribution list.", "PRIMARY"),
        ("Backup BI DB", "Success", "Passed", 214,
         "Full backup completed to \\\\bak\\BI\\2025-05.bak.", "PRIMARY"),
        ("Backup RRAPS DB", "Success", "Passed", 331,
         "Full backup completed (12.4 GB).", "PRIMARY"),
        ("Backup Warehouse DB", "Success", "Passed", 512,
         "Full backup completed (48.1 GB).", "PRIMARY"),
    ],
    "MAIN": [
        ("Populate KeyClient", "Success", "Passed", 12,
         "1,284 KeyClient rows staged.", "PRIMARY"),
        ("Backup BigFish Tables", "Success", "Passed", 8,
         "6 BigFish tables snapshotted.", "PRIMARY"),
        ("Run BigFish Load Job", "Success", "Passed", 225,
         "BigFish load agent job succeeded.", "PRIMARY"),
        ("Populate BigFish Tables", "Success", "Passed", 34,
         "BigFish fact tables populated.", "PRIMARY"),
        ("Validate BigFish Dashboard", "Success", "Passed", 15,
         "Dashboard row counts match source.", "PRIMARY"),
        ("Populate Quadrant Tables", "Success", "Passed", 22,
         "Quadrant tables populated.", "PRIMARY"),
        ("Run Azure Job", "Success", "Passed", 138,
         "Azure Agent job completed on the remote server.", "REMOTE_SQL"),
        ("Run CompTaskForce Job", "Success", "Passed", 126,
         "CompTaskForce job completed.", "PRIMARY"),
        ("Fix Employee Role Data", "Success", "Failed", 16,
         "Executed, but 3 employees still missing a role mapping.", "PRIMARY"),
        ("Validate Measurement Dashboard", "Success", "Passed", 11,
         "Measurement dashboard totals reconciled.", "PRIMARY"),
    ],
    "BI": [
        ("Insert AsOfDate", "Success", "Passed", 2,
         "As-of date set to 2025-05-31.", "PRIMARY"),
        ("Load PeopleSoft Revenue", "Success", "Passed", 174,
         "PeopleSoft revenue loaded (58,220 rows).", "PRIMARY"),
        ("Load WIP Tables", "Success", "Passed", 96,
         "WIP tables loaded.", "PRIMARY"),
        ("Check Consultant Workload", "Success", "Passed", 14,
         "Workload thresholds within tolerance.", "PRIMARY"),
        ("Run OfficeFull Model", "Success", "Passed", 402,
         "OfficeFull tabular model processed.", "PRIMARY"),
        ("Run BI Finance Job", "Success", "Passed", 251,
         "BI finance job succeeded.", "PRIMARY"),
        ("Check Employee Role Data", "Success", "Passed", 9,
         "Role data check passed.", "PRIMARY"),
        ("Consultant Quadrant Data Load", "Running", "Pending", None,
         "Loading consultant quadrant data…", "PRIMARY"),
        ("Area Manager Dashboard Load", "Pending", "Pending", None,
         "Waiting for upstream step to complete.", "PRIMARY"),
        ("Insert Historical Tables", "Pending", "Pending", None,
         "Queued.", "PRIMARY"),
    ],
    "DAY5": [
        ("Refresh PeopleSoft Revenue", "Pending", "Pending", None,
         "Scheduled for day-5 refresh.", "PRIMARY"),
        ("Run OfficeFull Model", "Pending", "Pending", None,
         "Queued.", "PRIMARY"),
    ],
    "POST": [
        ("Send Complete Email", "Pending", "Pending", None,
         "Sends when all phases succeed.", "PRIMARY"),
    ],
}


def _proc_slug(step_name: str) -> str:
    return "".join(part for part in step_name.replace("-", " ").split())


def get_job_steps() -> list[dict[str, Any]]:
    """Rows shaped like ``orchestration.job_steps`` (server resolved from connections)."""
    rows: list[dict[str, Any]] = []
    step_id = 1
    for phase in PHASES:
        phase_key = phase["key"]
        for order, entry in enumerate(_STEPS[phase_key], start=1):
            step_name, _e, _v, _d, _m, connection_name = entry
            slug = _proc_slug(step_name)
            agent_job = STEP_TO_AGENT_JOB.get(step_name)
            rows.append(
                {
                    "step_id": step_id,
                    "job_id": JOB_ID,
                    "step_name": step_name,
                    "phase": phase_key,
                    "server_name": _server_for(connection_name),
                    "step_order": order,
                    "execute_proc_name": f"orchestration.usp_Execute_{slug}",
                    "validate_proc_name": f"orchestration.usp_Validate_{slug}",
                    "is_enabled": True,
                    "agent_job_name": agent_job,
                    "agent_job_key": job_key(agent_job) if agent_job else None,
                }
            )
            step_id += 1
    return rows


# ---------------------------------------------------------------------------
# orchestration.step_runs
# ---------------------------------------------------------------------------
def get_step_runs() -> dict[int, dict[str, Any]]:
    """Per-step runtime state keyed by ``step_id`` (shaped like ``step_runs``)."""
    runs: dict[int, dict[str, Any]] = {}
    step_id = 1
    elapsed = 0
    for phase in PHASES:
        for entry in _STEPS[phase["key"]]:
            _name, exec_status, val_status, duration, message, _conn = entry
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
            step_id += 1
    return runs


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
        "phase": step["phase"],
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
# (job_name, connection_name, enabled, last_status, last_run, next_run,
#  running, alt_name)
# ---------------------------------------------------------------------------
_MONITORED_JOBS: list[tuple[str, str, bool, str, str, str | None, bool, str | None]] = [
    ("zz-Load Big Fish Dashboard Data 2016", "PRIMARY", True, "Succeeded",
     "05/31 02:19 AM", "06/01 02:15 AM", False, None),
    ("zz_Load CompTaskForce Data 2016", "PRIMARY", True, "Succeeded",
     "05/31 02:30 AM", "06/01 02:25 AM", False, None),
    ("RRAPS_Populate Consultant_workload table - Monthly Load", "PRIMARY", True, "Running",
     "05/31 02:48 AM", "06/01 02:45 AM", True, None),
    ("BI_FINANCE_DATA", "PRIMARY", True, "Succeeded",
     "05/31 02:41 AM", "06/01 02:40 AM", False, None),
    ("Azure_PSHRDataLoads", "REMOTE_SQL", True, "Succeeded",
     "05/31 02:22 AM", "06/01 02:20 AM", False, "AzurePSHRDataLoads_TEST"),
]

# Steps whose execute procedure launches a monitored SQL Agent job.
# Keyed by step_name; the step's execute_proc_name is the trigger point.
STEP_TO_AGENT_JOB: dict[str, str] = {
    "Run BigFish Load Job": "zz-Load Big Fish Dashboard Data 2016",
    "Run CompTaskForce Job": "zz_Load CompTaskForce Data 2016",
    "Run BI Finance Job": "BI_FINANCE_DATA",
    "Consultant Quadrant Data Load": "RRAPS_Populate Consultant_workload table - Monthly Load",
    "Run Azure Job": "Azure_PSHRDataLoads",
}


def job_key(job_name: str) -> str:
    """Stable anchor slug for a monitored job name."""
    return re.sub(r"[^a-z0-9]+", "-", job_name.lower()).strip("-")


def get_monitored_agent_jobs() -> list[dict[str, Any]]:
    """Rows shaped like the ``orchestration.usp_GetMonitoredAgentJobs`` result set.

    Server names are resolved from ``app_connections`` (never hardcoded).
    """
    rows: list[dict[str, Any]] = []
    for name, conn, enabled, status, last_run, next_run, running, alt in _MONITORED_JOBS:
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
                "server_name": _server_for(conn),
                "connection_name": conn,
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
