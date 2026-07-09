"""Tests for live database schema mapping and repository SQL contracts."""

from __future__ import annotations

from datetime import datetime

from app.db.live_schema import (
    APP_CONNECTIONS_COLUMNS,
    USERS_COLUMNS,
    normalize_execution_log_row,
    normalize_job_run_row,
    normalize_job_step_row,
    normalize_step_run_row,
    normalize_user_row,
)
from app.db.repositories.orchestration import OrchestrationRepository
from app.db.repositories.users import UserRepository


def test_users_columns_exclude_updated_at():
    assert "updated_at" not in USERS_COLUMNS
    assert "last_login" in USERS_COLUMNS


def test_app_connections_columns_match_live_schema():
    assert "environment_name" in APP_CONNECTIONS_COLUMNS
    assert "sql_password_hash" in APP_CONNECTIONS_COLUMNS
    assert "connection_name" not in APP_CONNECTIONS_COLUMNS
    assert "sql_password_encrypted" not in APP_CONNECTIONS_COLUMNS


def test_normalize_user_row_maps_last_login_to_updated_at_alias():
    row = {
        "user_id": 1,
        "username": "admin",
        "password_hash": "hash",
        "display_name": "Admin User",
        "email": "admin@example.com",
        "is_active": True,
        "created_at": datetime(2025, 1, 1, 9, 0, 0),
        "last_login": datetime(2025, 5, 1, 8, 0, 0),
        "role": "Admin",
    }
    normalized = normalize_user_row(row)
    assert normalized["last_login"] == "2025-05-01 08:00:00"
    assert normalized["updated_at"] == "2025-05-01 08:00:00"
    assert "updated_at" not in USERS_COLUMNS


def test_normalize_job_step_row_uses_command_and_is_active():
    row = {
        "step_id": 1,
        "job_id": 1,
        "step_order": 1,
        "step_name": "Backup BI",
        "parameters": None,
        "is_active": True,
        "step_type": "sql",
        "command": "usp_backup_bi",
        "server_name": "SDAZ001MLD21",
        "requires_approval": False,
        "on_failure_action": "stop",
        "retry_count": 0,
        "retry_delay_sec": 0,
        "execution_mode": "sync",
        "phase_code": "P1",
    }
    normalized = normalize_job_step_row(row)
    assert normalized["execute_proc_name"] == "usp_backup_bi"
    assert normalized["is_enabled"] is True
    assert normalized["phase_code"] == "P1"


def test_normalize_job_run_row_maps_live_columns():
    row = {
        "run_id": 42,
        "job_id": 1,
        "start_time": datetime(2025, 5, 31, 2, 15, 0),
        "end_time": None,
        "status": "In Progress",
        "triggered_by": "admin",
        "error_message": None,
        "phase_code": "P1",
        "run_name": "May 2025",
    }
    normalized = normalize_job_run_row(row)
    assert normalized["period_label"] == "May 2025"
    assert normalized["started_by"] == "admin"
    assert normalized["status"] == "In Progress"


def test_normalize_step_run_row_maps_live_columns():
    row = {
        "step_run_id": 1001,
        "run_id": 42,
        "step_id": 3,
        "start_time": datetime(2025, 5, 31, 2, 20, 0),
        "end_time": datetime(2025, 5, 31, 2, 25, 0),
        "status": "Succeeded",
        "log_message": "Completed",
        "duration_sec": 300,
        "approval_status": "Approved",
        "approved_by": "admin",
        "approved_at": None,
        "error_message": None,
        "log_ref_id": None,
        "step_order": 3,
        "step_name": "Backup RRAPS",
        "phase_code": "P1",
        "retry_attempt": 0,
    }
    normalized = normalize_step_run_row(row)
    assert normalized["execution_status"] == "Success"
    assert normalized["validation_status"] == "Passed"
    assert normalized["duration_seconds"] == 300


def test_normalize_execution_log_row_maps_live_columns():
    row = {
        "log_id": 1,
        "process_name": "usp_backup_bi",
        "database_name": "BI",
        "step": "Backup BI",
        "status": "Succeeded",
        "message": "Done",
        "log_time": datetime(2025, 5, 31, 2, 19, 0),
    }
    normalized = normalize_execution_log_row(row)
    assert normalized["step_name"] == "Backup BI"
    assert normalized["logged_at"].startswith("05/31 02:19")
    assert normalized["run_id"] is None


def test_user_repository_sql_uses_live_columns():
    import inspect

    source = inspect.getsource(UserRepository.get_by_username)
    assert "updated_at" not in source
    assert "USERS_COLUMNS" in source
    assert "last_login" in USERS_COLUMNS


def test_orchestration_repository_sql_uses_live_job_run_columns():
    import inspect

    source = inspect.getsource(OrchestrationRepository.get_job_runs)
    assert "start_time" in source
    assert "run_name" in source
    assert "started_at" not in source
    assert "period_label" not in source
