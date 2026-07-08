"""SQL repository helpers — all runtime connections come from ConnectionManager."""

from __future__ import annotations

from typing import Any

from flask import current_app, has_app_context

from app.db.connection_manager import get_connection_manager
from config.settings import should_use_mock_data


def use_mock_data() -> bool:
    if not has_app_context():
        return True
    return should_use_mock_data(current_app.config)


def data_source_label() -> str:
    return "mock" if use_mock_data() else "sql"


def _require_primary_ready() -> None:
    if use_mock_data():
        return
    manager = get_connection_manager()
    primary_error = manager.get_primary_error()
    if primary_error:
        raise ConnectionError(primary_error)
    if not manager.primary_ready():
        raise ConnectionError(
            "PRIMARY connection is not ready. Run setup.ps1 -TestConnection."
        )


def query_primary(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    _require_primary_ready()
    with get_connection_manager().connect("PRIMARY") as db:
        cursor = db.cursor()
        cursor.execute(sql, params)
        if not cursor.description:
            return []
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def query_connection(environment_name: str, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with get_connection_manager().connect(environment_name) as db:
        cursor = db.cursor()
        cursor.execute(sql, params)
        if not cursor.description:
            return []
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def exec_primary(sql: str, params: tuple = ()) -> None:
    _require_primary_ready()
    with get_connection_manager().connect("PRIMARY") as db:
        cursor = db.cursor()
        cursor.execute(sql, params)
        db.commit()
