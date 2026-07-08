"""Unified data access facade.

Services import from this module instead of mock_data. When DATA_SOURCE=sql and
bootstrap credentials are configured, SQL repositories return the same dict
shapes the UI and /api/v1/* contracts expect.
"""

from __future__ import annotations

from typing import Any

from app.db.registry import PHASES, STEP_REGISTRY, job_key, trigger_for_job
from app.db.repositories import (
    ConnectionsRepository,
    OrchestrationRepository,
    SqlAgentRepository,
    UserRepository,
)
from app.db.repositories.base import data_source_label

_orchestration = OrchestrationRepository()
_connections = ConnectionsRepository()
_sql_agent = SqlAgentRepository()
_users = UserRepository()


def get_phases() -> list[dict[str, str]]:
    return _orchestration.get_phases()


def get_users() -> list[dict[str, Any]]:
    if data_source_label() == "mock":
        from app.dashboard import mock_data

        return mock_data.get_users()
    rows = []
    for row in _users.list_users():
        full = _users.get_by_username(row["username"])
        if full:
            rows.append(full)
    return rows


def get_app_connections() -> list[dict[str, Any]]:
    return _connections.list_connections()


def get_active_connection() -> dict[str, Any]:
    return _connections.get_active()


def get_jobs() -> list[dict[str, Any]]:
    return _orchestration.get_jobs()


def get_job_steps() -> list[dict[str, Any]]:
    return _orchestration.get_job_steps()


def get_step_runs() -> dict[int, dict[str, Any]]:
    return _orchestration.get_step_runs()


def get_validation_results() -> dict[int, dict[str, Any]]:
    return _orchestration.get_validation_results()


def get_execution_log() -> list[dict[str, Any]]:
    return _orchestration.get_execution_log()


def get_run_metrics() -> dict[str, Any]:
    return _orchestration.get_run_metrics()


def get_job_runs() -> list[dict[str, Any]]:
    return _orchestration.get_job_runs()


def get_current_run() -> dict[str, Any]:
    return _orchestration.get_current_run()


def get_monitored_agent_jobs() -> list[dict[str, Any]]:
    return _sql_agent.get_monitored_agent_jobs()


def get_trigger_for_agent_job(job_name: str) -> dict[str, str | None]:
    return trigger_for_job(job_name)


def connection_latency_ms(environment_name: str) -> int | None:
    return _connections.ping_latency_ms(environment_name)


__all__ = [
    "PHASES",
    "STEP_REGISTRY",
    "job_key",
    "data_source_label",
    "get_phases",
    "get_users",
    "get_app_connections",
    "get_active_connection",
    "get_jobs",
    "get_job_steps",
    "get_step_runs",
    "get_validation_results",
    "get_execution_log",
    "get_run_metrics",
    "get_job_runs",
    "get_current_run",
    "get_monitored_agent_jobs",
    "get_trigger_for_agent_job",
    "connection_latency_ms",
]
