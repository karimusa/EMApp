"""Resolve logical connection targets from orchestration.app_connections.

Repositories and the dashboard must never treat job_steps.server_name as the
runtime host. Steps declare a logical environment (PRIMARY, REMOTE_SQL, …);
physical server/database/username values come from the live registry only.
"""

from __future__ import annotations

from typing import Any

from app.db.registry import STEP_REGISTRY, StepDef

_REGISTRY_BY_COMMAND = {step.execute_proc: step for step in STEP_REGISTRY}

_CONNECTION_ENV_KEYS = (
    "connection_environment",
    "environment_name",
    "connection_name",
)


def _norm_env(name: str | None) -> str:
    return (name or "").strip().upper()


def list_runtime_connections() -> list[dict[str, Any]]:
    """Active connections from ConnectionManager, or mock/offline fallback."""
    try:
        from app.db.connection_manager import get_connection_manager

        manager = get_connection_manager()
        connections = manager.all_connections()
        if connections:
            return [
                {
                    "environment_name": conn.environment_name,
                    "server_name": conn.server_name,
                    "database_name": conn.database_name,
                    "sql_username": conn.sql_username,
                    "auth_type": conn.auth_type,
                    "is_active": conn.is_active,
                }
                for conn in connections.values()
            ]
    except RuntimeError:
        pass

    try:
        from flask import has_app_context

        if has_app_context():
            from app.db.repositories.connections import ConnectionsRepository

            return ConnectionsRepository().list_connections()
    except Exception:
        pass

    from app.dashboard import mock_data

    return mock_data.get_app_connections()


def resolve_connection_by_environment(environment_name: str) -> dict[str, Any]:
    """Lookup one registry row by logical environment name."""
    env_key = _norm_env(environment_name)
    for conn in list_runtime_connections():
        if _norm_env(conn.get("environment_name")) == env_key:
            return dict(conn)
    return {
        "environment_name": env_key,
        "server_name": "",
        "database_name": "",
        "sql_username": "",
        "auth_type": "sql",
        "is_active": False,
    }


def resolve_step_connection_environment(
    row: dict[str, Any],
    registry_step: StepDef | None = None,
) -> str:
    """Logical execution target for a job step row."""
    for key in _CONNECTION_ENV_KEYS:
        raw = row.get(key)
        if raw:
            return _norm_env(str(raw))
    if registry_step is None:
        command = _coerce_command(row)
        if command:
            registry_step = _REGISTRY_BY_COMMAND.get(command)
    if registry_step is not None:
        return _norm_env(registry_step.environment_name)
    return "PRIMARY"


def _coerce_command(row: dict[str, Any]) -> str:
    for key in ("command", "execute_proc_name"):
        value = row.get(key)
        if value:
            return str(value).strip()
    return ""


def resolve_step_runtime_target(
    row: dict[str, Any],
    registry_step: StepDef | None = None,
) -> dict[str, str]:
    """Resolve display and execution metadata for a job step."""
    connection_environment = resolve_step_connection_environment(row, registry_step)
    conn = resolve_connection_by_environment(connection_environment)
    return {
        "connection_environment": connection_environment,
        "server_name": conn.get("server_name") or "",
        "database_name": conn.get("database_name") or "",
        "sql_username": conn.get("sql_username") or "",
    }


def resolve_execution_log_target(database_name: str | None) -> dict[str, str]:
    """Map execution-log database context to a registry connection."""
    db_key = (database_name or "").strip().lower()
    if db_key:
        for conn in list_runtime_connections():
            if (conn.get("database_name") or "").strip().lower() == db_key:
                env = _norm_env(conn.get("environment_name"))
                return {
                    "connection_environment": env,
                    "server_name": conn.get("server_name") or "",
                    "database_name": conn.get("database_name") or "",
                }
    primary = resolve_connection_by_environment("PRIMARY")
    return {
        "connection_environment": "PRIMARY",
        "server_name": primary.get("server_name") or "",
        "database_name": primary.get("database_name") or "",
    }
