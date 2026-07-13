"""Runtime flags for dashboard execution."""

from __future__ import annotations

import logging
import subprocess
from functools import lru_cache
from typing import Any

from flask import has_app_context

from app.db.connection_manager import get_connection_manager
from app.db.repositories.base import data_source_label, use_mock_data

logger = logging.getLogger(__name__)

EXECUTION_BUILD_ID = "dashboard-execution-2026-07-10"


@lru_cache(maxsize=1)
def _git_head() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def primary_ready() -> bool:
    if not has_app_context():
        return False
    if use_mock_data():
        return False
    try:
        return get_connection_manager().primary_ready()
    except Exception:
        return False


def execution_enabled() -> bool:
    """True when PRIMARY is validated and mutations may run."""
    return primary_ready() and not use_mock_data()


def execution_block_reason() -> str | None:
    if not has_app_context():
        return "Application context is not available."
    if use_mock_data():
        return (
            "Live SQL connection unavailable. Validate PRIMARY in Settings "
            "before running orchestration steps."
        )
    try:
        manager = get_connection_manager()
        if not manager.primary_ready():
            error = manager.ensure_primary_validated(reload_registry=False)
            return error or "PRIMARY connection is not validated."
    except Exception as exc:
        return str(exc)
    return None


def get_execution_runtime() -> dict[str, Any]:
    reason = execution_block_reason()
    return {
        "build_id": EXECUTION_BUILD_ID,
        "git_head": _git_head(),
        "data_source": data_source_label(),
        "live_db_available": execution_enabled(),
        "execution_enabled": execution_enabled(),
        "execution_block_reason": reason,
        "primary_ready": primary_ready(),
        "mock_mode": use_mock_data(),
    }
