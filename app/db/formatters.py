"""Format database values into the UI contract strings."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def format_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def format_run_datetime(value: Any) -> str | None:
    """e.g. May 31, 2025 02:15 AM"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y %I:%M %p")
    return str(value)


def format_log_datetime(value: Any) -> str | None:
    """e.g. 05/31 02:19 AM"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime("%m/%d %I:%M:%S %p")
    return str(value)


def format_agent_job_time(value: Any) -> str | None:
    """Short agent-job timestamp for cards."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.strftime("%m/%d %I:%M %p")
    return str(value)


def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return bool(int(value))
