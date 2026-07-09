"""Schema helpers for orchestration.job_steps target resolution."""

from __future__ import annotations

_TARGET_COLUMNS = (
    "environment_name",
    "connection_environment",
    "connection_name",
)

_BASE_SELECT_COLUMNS = """
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
                phase_code"""


def detect_job_steps_target_column(cursor) -> str | None:
    """Return the first logical-target column present on job_steps."""
    for column in _TARGET_COLUMNS:
        cursor.execute(
            f"SELECT COL_LENGTH('orchestration.job_steps', '{column}')"
        )
        row = cursor.fetchone()
        if row and row[0] is not None:
            return column
    return None


def job_steps_select_sql(*, target_column: str | None = None) -> str:
    columns = _BASE_SELECT_COLUMNS
    if target_column:
        columns = f"{columns},\n                {target_column}"
    return f"""
            SELECT
{columns}
            FROM orchestration.job_steps
            WHERE is_active = 1
            ORDER BY phase_code, step_order, step_id
            """
