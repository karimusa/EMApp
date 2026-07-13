"""Tests for the frozen step registry and proc-name normalization."""

from __future__ import annotations

from app.db.registry import (
    normalize_proc_name,
    registry_step_for_command,
    registry_step_for_name,
)
from app.db.repositories.orchestration import OrchestrationRepository


def test_normalize_proc_name_strips_exec_prefix():
    assert normalize_proc_name("EXEC orchestration.sp_send_month_end_start_email") == (
        "orchestration.sp_send_month_end_start_email"
    )
    assert normalize_proc_name("  exec usp_backup_bi  ") == "usp_backup_bi"


def test_registry_step_for_command_matches_exec_prefix():
    step = registry_step_for_command("EXEC orchestration.sp_send_month_end_start_email")
    assert step is not None
    assert step.step_name == "Send Start Email"
    assert step.validate_proc == "orchestration.sp_validate_month_end_start_email"


def test_registry_step_for_name_lookup():
    step = registry_step_for_name("Send Start Email")
    assert step is not None
    assert step.execute_proc == "orchestration.sp_send_month_end_start_email"


def test_proc_sql_accepts_exec_prefixed_name():
    assert OrchestrationRepository._proc_sql(
        "EXEC orchestration.sp_send_month_end_start_email"
    ) == "EXEC orchestration.sp_send_month_end_start_email"
