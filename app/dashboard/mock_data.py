"""Mock orchestration data shaped exactly like the real SQL rows.

Step 2 builds the dashboard UI against these Python structures. In later steps the
same shapes are produced by reading the database — no template/service changes
required — via:

* ``orchestration.job_steps``      -> step definitions      (see ``get_job_steps``)
* ``orchestration.step_runs``      -> per-run step state     (see ``get_step_runs``)
* ``orchestration.db_execution_log`` -> detailed log rows    (see ``get_execution_log``)
* ``orchestration.job_runs``       -> the run header         (see ``get_current_run``)

Column names mirror ``docs/planning/sql/schema.sql`` so the DAO layer added in a
later step can drop in without reshaping the view model. This module contains NO
execution logic — it only describes the current state of a sample run.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Reference constants (match orchestration.app_connections seed rows)
# ---------------------------------------------------------------------------
JOB_ID = 1
RUN_ID = 42
PRIMARY_SERVER = "SPUS001BDBEXT"   # PRIMARY   -> MonthEndOrchestrationDB
REMOTE_SERVER = "SPAZ001EDM10"     # REMOTE_SQL -> msdb (Azure)

# Ordered phases + display labels for the UI tabs.
PHASES: list[dict[str, str]] = [
    {"key": "PRE", "label": "PRE"},
    {"key": "MAIN", "label": "MAIN"},
    {"key": "BI", "label": "BI"},
    {"key": "DAY5", "label": "DAY 5"},
    {"key": "POST", "label": "POST"},
]

# Allowed status values (mirrors the CHECK constraints planned for step_runs).
EXECUTION_STATUSES = ("Success", "Running", "Pending", "Failed", "Skipped")
VALIDATION_STATUSES = ("Passed", "Failed", "Pending", "NotRequired")

# ---------------------------------------------------------------------------
# Internal step catalogue.
#
# Each tuple: (step_name, execution_status, validation_status, duration_seconds,
#              last_message, server_name_override)
# server_name_override is None for the PRIMARY server.
# ---------------------------------------------------------------------------
_STEPS: dict[str, list[tuple[str, str, str, int | None, str, str | None]]] = {
    "PRE": [
        ("Send Start Email", "Success", "Passed", 3,
         "Kickoff notification sent to close distribution list.", None),
        ("Backup BI DB", "Success", "Passed", 214,
         "Full backup completed to \\\\bak\\BI\\2025-05.bak.", None),
        ("Backup RRAPS DB", "Success", "Passed", 331,
         "Full backup completed (12.4 GB).", None),
        ("Backup Warehouse DB", "Success", "Passed", 512,
         "Full backup completed (48.1 GB).", None),
    ],
    "MAIN": [
        ("Populate KeyClient", "Success", "Passed", 12,
         "1,284 KeyClient rows staged.", None),
        ("Backup BigFish Tables", "Success", "Passed", 8,
         "6 BigFish tables snapshotted.", None),
        ("Run BigFish Load Job", "Success", "Passed", 225,
         "BigFish load agent job succeeded.", None),
        ("Populate BigFish Tables", "Success", "Passed", 34,
         "BigFish fact tables populated.", None),
        ("Validate BigFish Dashboard", "Success", "Passed", 15,
         "Dashboard row counts match source.", None),
        ("Populate Quadrant Tables", "Success", "Passed", 22,
         "Quadrant tables populated.", None),
        ("Run Azure Job", "Success", "Passed", 138,
         "Azure Agent job completed on SPAZ001EDM10.", REMOTE_SERVER),
        ("Run CompTaskForce Job", "Success", "Passed", 126,
         "CompTaskForce job completed.", None),
        ("Fix Employee Role Data", "Success", "Failed", 16,
         "Executed, but 3 employees still missing a role mapping.", None),
        ("Validate Measurement Dashboard", "Success", "Passed", 11,
         "Measurement dashboard totals reconciled.", None),
    ],
    "BI": [
        ("Insert AsOfDate", "Success", "Passed", 2,
         "As-of date set to 2025-05-31.", None),
        ("Load PeopleSoft Revenue", "Success", "Passed", 174,
         "PeopleSoft revenue loaded (58,220 rows).", None),
        ("Load WIP Tables", "Success", "Passed", 96,
         "WIP tables loaded.", None),
        ("Check Consultant Workload", "Success", "Passed", 14,
         "Workload thresholds within tolerance.", None),
        ("Run OfficeFull Model", "Success", "Passed", 402,
         "OfficeFull tabular model processed.", None),
        ("Run BI Finance Job", "Success", "Passed", 251,
         "BI finance job succeeded.", None),
        ("Check Employee Role Data", "Success", "Passed", 9,
         "Role data check passed.", None),
        ("Consultant Quadrant Data Load", "Running", "Pending", None,
         "Loading consultant quadrant data…", None),
        ("Area Manager Dashboard Load", "Pending", "Pending", None,
         "Waiting for upstream step to complete.", None),
        ("Insert Historical Tables", "Pending", "Pending", None,
         "Queued.", None),
    ],
    "DAY5": [
        ("Refresh PeopleSoft Revenue", "Pending", "Pending", None,
         "Scheduled for day-5 refresh.", None),
        ("Run OfficeFull Model", "Pending", "Pending", None,
         "Queued.", None),
    ],
    "POST": [
        ("Send Complete Email", "Pending", "Pending", None,
         "Sends when all phases succeed.", None),
    ],
}

# Fixed reference timestamp so the sample run renders deterministically.
_RUN_DATE = datetime(2025, 5, 31, 2, 15, 0)


def _proc_slug(step_name: str) -> str:
    """Convert a step name into the PascalCase suffix used by the procs."""
    return "".join(part for part in step_name.replace("-", " ").split())


def get_job_steps() -> list[dict[str, Any]]:
    """Rows shaped like ``orchestration.job_steps``."""
    rows: list[dict[str, Any]] = []
    step_id = 1
    for phase in PHASES:
        phase_key = phase["key"]
        for order, entry in enumerate(_STEPS[phase_key], start=1):
            step_name, _exec, _val, _dur, _msg, server_override = entry
            slug = _proc_slug(step_name)
            rows.append(
                {
                    "step_id": step_id,
                    "job_id": JOB_ID,
                    "step_name": step_name,
                    "phase": phase_key,
                    "server_name": server_override or PRIMARY_SERVER,
                    "step_order": order,
                    "execute_proc_name": f"orchestration.usp_Execute_{slug}",
                    "validate_proc_name": f"orchestration.usp_Validate_{slug}",
                    "is_enabled": True,
                }
            )
            step_id += 1
    return rows


def get_step_runs() -> dict[int, dict[str, Any]]:
    """Per-step runtime state keyed by ``step_id`` (shaped like ``step_runs``)."""
    runs: dict[int, dict[str, Any]] = {}
    step_id = 1
    elapsed = 0
    for phase in PHASES:
        for entry in _STEPS[phase["key"]]:
            _name, exec_status, val_status, duration, message, _server = entry
            completed_at = None
            started_at = None
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


def get_execution_log() -> list[dict[str, Any]]:
    """Detailed log rows shaped like ``orchestration.db_execution_log``.

    Newest first, as the UI log panel expects.
    """
    steps = {row["step_id"]: row for row in get_job_steps()}
    runs = get_step_runs()
    log: list[dict[str, Any]] = []
    log_id = 5000
    for step_id, run in runs.items():
        step = steps[step_id]
        if run["execution_status"] in ("Success", "Failed"):
            log.append(
                {
                    "log_id": log_id,
                    "run_id": RUN_ID,
                    "phase": step["phase"],
                    "step_name": step["step_name"],
                    "message": "Step started execution",
                    "status": "Info",
                    "duration_seconds": None,
                    "server_name": step["server_name"],
                    "logged_at": run["started_at"],
                }
            )
            log_id += 1
            log.append(
                {
                    "log_id": log_id,
                    "run_id": RUN_ID,
                    "phase": step["phase"],
                    "step_name": step["step_name"],
                    "message": run["last_message"],
                    "status": "Success" if run["execution_status"] == "Success" else "Failed",
                    "duration_seconds": run["duration_seconds"],
                    "server_name": step["server_name"],
                    "logged_at": run["completed_at"],
                }
            )
            log_id += 1
        elif run["execution_status"] == "Running":
            log.append(
                {
                    "log_id": log_id,
                    "run_id": RUN_ID,
                    "phase": step["phase"],
                    "step_name": step["step_name"],
                    "message": run["last_message"],
                    "status": "Running",
                    "duration_seconds": None,
                    "server_name": step["server_name"],
                    "logged_at": run["started_at"],
                }
            )
            log_id += 1

    log.sort(key=lambda row: (row["logged_at"] or ""), reverse=True)
    return log


def get_current_run() -> dict[str, Any]:
    """Run header shaped like an ``orchestration.job_runs`` row."""
    return {
        "run_id": RUN_ID,
        "job_id": JOB_ID,
        "job_name": "RRA Month-End Orchestration",
        "period_label": "May 2025",
        "status": "In Progress",
        "started_at": _seconds_after(0),
        "last_run_at": _RUN_DATE.strftime("%b %d, %Y %I:%M %p"),
    }


def _seconds_after(seconds: int) -> str:
    """Return a display timestamp ``seconds`` after the run start."""
    from datetime import timedelta

    return (_RUN_DATE + timedelta(seconds=seconds)).strftime("%m/%d %I:%M:%S %p")
