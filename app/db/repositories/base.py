"""SQL repository helpers."""

from __future__ import annotations

from typing import Any

from flask import current_app, has_app_context

from app.db.connection_manager import get_connection_manager


def use_mock_data() -> bool:
    if not has_app_context():
        return True
    cfg = current_app.config
    if cfg.get("TESTING"):
        return True
    mode = (cfg.get("DATA_SOURCE") or "auto").lower()
    if mode == "mock":
        return True
    if mode == "sql":
        return False
    return not bool(cfg.get("BOOTSTRAP_SERVER"))


def data_source_label() -> str:
    return "mock" if use_mock_data() else "sql"


def query_primary(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with get_connection_manager().connect("PRIMARY") as db:
        cursor = db.cursor()
        cursor.execute(sql, params)
        if not cursor.description:
            return []
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def query_connection(connection_name: str, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with get_connection_manager().connect(connection_name) as db:
        cursor = db.cursor()
        cursor.execute(sql, params)
        if not cursor.description:
            return []
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def exec_primary(sql: str, params: tuple = ()) -> None:
    with get_connection_manager().connect("PRIMARY") as db:
        cursor = db.cursor()
        cursor.execute(sql, params)
        db.commit()
