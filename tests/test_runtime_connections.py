"""Tests for registry-based runtime connection resolution."""

from __future__ import annotations

from app.db.live_schema import normalize_execution_log_row, normalize_job_step_row
from app.db.runtime_connections import (
    resolve_connection_by_environment,
    resolve_step_connection_environment,
    resolve_step_runtime_target,
)


def test_resolve_step_connection_environment_prefers_row_value():
    row = {"environment_name": "REMOTE_SQL", "server_name": "legacy-host.example"}
    assert resolve_step_connection_environment(row) == "REMOTE_SQL"


def test_resolve_step_connection_environment_uses_registry_for_command():
    row = {
        "command": "usp_me_07_run_azure_pshr_job",
        "server_name": "legacy-host.example",
    }
    assert resolve_step_connection_environment(row) == "REMOTE_SQL"


def test_normalize_job_step_row_ignores_stale_server_name():
    row = {
        "step_id": 31,
        "job_id": 1,
        "step_order": 1,
        "step_name": "Send Start Email",
        "parameters": None,
        "is_active": True,
        "step_type": "sql",
        "command": "orchestration.sp_send_month_end_start_email",
        "server_name": "legacy-prod-host.example",
        "requires_approval": False,
        "on_failure_action": "stop",
        "retry_count": 0,
        "retry_delay_sec": 0,
        "execution_mode": "STRICT",
        "phase_code": "PRE",
    }
    normalized = normalize_job_step_row(row)
    assert normalized["connection_environment"] == "PRIMARY"
    assert normalized["server_name"] == "mock-primary.local"
    assert normalized["database_name"] == "mock_orchestration"
    assert normalized["server_name"] != row["server_name"]


def test_resolve_connection_by_environment_uses_mock_registry():
    primary = resolve_connection_by_environment("PRIMARY")
    assert primary["server_name"] == "mock-primary.local"
    assert primary["database_name"] == "mock_orchestration"


def test_resolve_step_runtime_target_for_remote_step():
    row = {"command": "usp_me_07_run_azure_pshr_job"}
    target = resolve_step_runtime_target(row)
    assert target["connection_environment"] == "REMOTE_SQL"
    assert target["server_name"] == "mock-remote.local"


def test_normalize_execution_log_row_resolves_primary_target():
    row = {
        "log_id": 1,
        "process_name": "usp_backup_bi",
        "database_name": "mock_orchestration",
        "step": "Backup BI",
        "status": "Succeeded",
        "message": "Done",
        "log_time": "2026-07-02T15:33:04",
    }
    normalized = normalize_execution_log_row(row)
    assert normalized["connection_environment"] == "PRIMARY"
    assert normalized["server_name"] == "mock-primary.local"
    assert normalized["database_name"] == "mock_orchestration"
