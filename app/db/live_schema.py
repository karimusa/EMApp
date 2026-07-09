"""Live MonthEndOrchestrationDB column contracts and row normalizers.

Repositories SELECT only columns that exist in production and map them into the
UI/service contract used by templates and mock_data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.formatters import format_log_datetime, format_run_datetime, format_timestamp
from app.db.registry import STEP_REGISTRY, agent_job_for_proc, job_key, registry_step_for_command

_REGISTRY_BY_COMMAND = {step.execute_proc: step for step in STEP_REGISTRY}

USERS_COLUMNS = (
    "user_id",
    "username",
    "password_hash",
    "display_name",
    "email",
    "is_active",
    "created_at",
    "last_login",
    "role",
)

APP_CONNECTIONS_COLUMNS = (
    "connection_id",
    "environment_name",
    "is_active",
    "server_name",
    "database_name",
    "auth_type",
    "sql_username",
    "sql_password_hash",
    "description",
    "created_at",
    "updated_at",
)


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_execution_status(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return "Pending"
    lowered = text.lower()
    mapping = {
        "success": "Success",
        "succeeded": "Success",
        "completed": "Success",
        "complete": "Success",
        "failed": "Failed",
        "failure": "Failed",
        "error": "Failed",
        "running": "Running",
        "in progress": "Running",
        "in_progress": "Running",
        "pending": "Pending",
        "queued": "Pending",
        "skipped": "Skipped",
    }
    return mapping.get(lowered, text)


def normalize_run_status(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return "Pending"
    lowered = text.lower()
    mapping = {
        "completed": "Completed",
        "complete": "Completed",
        "success": "Completed",
        "succeeded": "Completed",
        "failed": "Failed",
        "failure": "Failed",
        "in progress": "In Progress",
        "in_progress": "In Progress",
        "running": "In Progress",
        "pending": "Pending",
    }
    return mapping.get(lowered, text)


def normalize_validation_status(
    approval_status: Any,
    *,
    execution_status: str,
) -> str:
    approval = _coerce_text(approval_status)
    if approval:
        lowered = approval.lower()
        mapping = {
            "approved": "Passed",
            "passed": "Passed",
            "success": "Passed",
            "rejected": "Failed",
            "failed": "Failed",
            "denied": "Failed",
            "pending": "Pending",
            "notrequired": "NotRequired",
            "not required": "NotRequired",
        }
        return mapping.get(lowered, approval)

    if execution_status == "Success":
        return "Passed"
    if execution_status == "Failed":
        return "Failed"
    if execution_status == "Running":
        return "Pending"
    return "Pending"


def _duration_seconds(start: Any, end: Any, explicit: Any = None) -> int | None:
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    if isinstance(start, datetime) and isinstance(end, datetime):
        return max(int((end - start).total_seconds()), 0)
    return None


def normalize_user_row(row: dict[str, Any], *, include_hash: bool = True) -> dict[str, Any]:
    out = {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "display_name": row.get("display_name") or row["username"],
        "email": row.get("email") or "",
        "created_at": format_timestamp(row.get("created_at")),
        "last_login": format_timestamp(row.get("last_login")),
        "updated_at": format_timestamp(row.get("last_login")),
    }
    if include_hash and "password_hash" in row:
        out["password_hash"] = row["password_hash"]
    return out


def normalize_job_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": row["job_id"],
        "job_name": row["job_name"],
        "description": "",
        "is_active": bool(row["is_active"]),
        "created_at": format_timestamp(row.get("created_at")),
    }


def normalize_job_step_row(row: dict[str, Any]) -> dict[str, Any]:
    command = _coerce_text(row.get("command"))
    registry_step = _REGISTRY_BY_COMMAND.get(command) or registry_step_for_command(command)
    execute_proc_name = command or (registry_step.execute_proc if registry_step else "")
    validate_proc_name = registry_step.validate_proc if registry_step else ""
    agent_job = registry_step.agent_job if registry_step else agent_job_for_proc(execute_proc_name)
    environment_name = registry_step.environment_name if registry_step else "PRIMARY"
    return {
        "step_id": row["step_id"],
        "job_id": row["job_id"],
        "step_name": row["step_name"],
        "phase_code": row.get("phase_code") or "",
        "server_name": row.get("server_name") or "",
        "step_order": row.get("step_order") or 0,
        "execute_proc_name": execute_proc_name,
        "validate_proc_name": validate_proc_name,
        "environment_name": environment_name,
        "is_enabled": bool(row.get("is_active", True)),
        "agent_job_name": agent_job,
        "agent_job_key": job_key(agent_job) if agent_job else None,
    }


def normalize_job_run_row(row: dict[str, Any]) -> dict[str, Any]:
    started_at = row.get("start_time")
    completed_at = row.get("end_time")
    period_label = _coerce_text(row.get("run_name")) or _coerce_text(row.get("phase_code"))
    if not period_label:
        period_label = f"Run {row['run_id']}"
    return {
        "run_id": row["run_id"],
        "job_id": row["job_id"],
        "period_label": period_label,
        "status": normalize_run_status(row.get("status")),
        "started_at": format_run_datetime(started_at),
        "completed_at": format_run_datetime(completed_at),
        "duration_seconds": _duration_seconds(started_at, completed_at),
        "started_by": row.get("triggered_by") or "",
    }


def normalize_step_run_row(row: dict[str, Any]) -> dict[str, Any]:
    execution_status = normalize_execution_status(row.get("status"))
    validation_status = normalize_validation_status(
        row.get("approval_status"),
        execution_status=execution_status,
    )
    message = _coerce_text(row.get("log_message")) or _coerce_text(row.get("error_message"))
    return {
        "step_run_id": row["step_run_id"],
        "run_id": row["run_id"],
        "step_id": row["step_id"],
        "execution_status": execution_status,
        "validation_status": validation_status,
        "last_message": message,
        "duration_seconds": _duration_seconds(
            row.get("start_time"),
            row.get("end_time"),
            row.get("duration_sec"),
        ),
        "started_at": format_log_datetime(row.get("start_time")),
        "completed_at": format_log_datetime(row.get("end_time")),
        "run_by": row.get("approved_by") or "",
    }


def normalize_execution_log_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "log_id": row["log_id"],
        "run_id": None,
        "phase": "",
        "step_name": row.get("step") or row.get("process_name") or "",
        "process_name": row.get("process_name") or "",
        "message": row.get("message") or "",
        "status": normalize_execution_status(row.get("status")),
        "duration_seconds": None,
        "server_name": row.get("database_name") or row.get("process_name") or "",
        "logged_at": format_log_datetime(row.get("log_time")),
    }


def build_step_run_from_execution_log_row(
    row: dict[str, Any],
    *,
    step_id: int,
) -> dict[str, Any]:
    execution_status = normalize_execution_status(row.get("status"))
    validation_status = normalize_validation_status(
        None,
        execution_status=execution_status,
    )
    logged_at = format_log_datetime(row.get("log_time"))
    return {
        "step_run_id": None,
        "run_id": None,
        "step_id": step_id,
        "execution_status": execution_status,
        "validation_status": validation_status,
        "last_message": row.get("message") or "",
        "duration_seconds": None,
        "started_at": logged_at,
        "completed_at": logged_at,
        "run_by": "",
        "data_source": "orchestration.db_execution_log",
    }


def normalize_run_metrics_row(row: dict[str, Any]) -> dict[str, Any]:
    total = int(row.get("total_steps") or 0)
    success = int(row.get("success_count") or 0)
    failed = int(row.get("failed_count") or 0)
    progress = round((success / total) * 100) if total else 0
    return {
        "metric_id": row.get("run_id"),
        "run_id": row["run_id"],
        "total_steps": total,
        "success_count": success,
        "failed_count": failed,
        "running_count": 0,
        "pending_count": max(total - success - failed, 0),
        "validation_failed_count": 0,
        "progress_pct": progress,
        "updated_at": "—",
    }
