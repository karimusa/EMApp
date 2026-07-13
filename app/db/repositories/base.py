"""SQL repository helpers — all runtime connections come from ConnectionManager."""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app, has_app_context

from app.db.connection_manager import (
    get_connection_manager,
    is_pyodbc_error,
    sql_connection_error_message,
)

logger = logging.getLogger(__name__)


def use_mock_data() -> bool:
    if not has_app_context():
        return True
    config = current_app.config
    if config.get("TESTING"):
        return True
    mode = (config.get("DATA_SOURCE") or "auto").lower()
    if mode == "mock":
        return True
    if mode == "sql":
        return False
    if not (config.get("BOOTSTRAP_SERVER") or "").strip():
        return True
    try:
        manager = get_connection_manager()
        if manager.primary_ready():
            return False
        logger.warning(
            "PRIMARY is not validated — dashboard will use mock data until "
            "orchestration.app_connections PRIMARY credentials are fixed"
        )
        return True
    except RuntimeError:
        return True


def data_source_label() -> str:
    return "mock" if use_mock_data() else "sql"


def _require_primary_ready() -> None:
    if use_mock_data():
        return
    manager = get_connection_manager()
    primary_error = manager.ensure_primary_validated(reload_registry=False)
    if primary_error:
        raise ConnectionError(primary_error)


def query_primary(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    _require_primary_ready()
    manager = get_connection_manager()
    try:
        with manager.connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            if not cursor.description:
                return []
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except ConnectionError:
        raise
    except Exception as exc:
        if is_pyodbc_error(exc):
            raise ConnectionError(sql_connection_error_message("PRIMARY", exc)) from exc
        raise


def query_connection(environment_name: str, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    try:
        with get_connection_manager().connect(environment_name) as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            if not cursor.description:
                return []
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except ConnectionError:
        raise
    except Exception as exc:
        if is_pyodbc_error(exc):
            raise ConnectionError(
                sql_connection_error_message(environment_name, exc)
            ) from exc
        raise


def exec_connection(environment_name: str, sql: str, params: tuple = ()) -> None:
    try:
        with get_connection_manager().connect(environment_name) as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            db.commit()
    except ConnectionError:
        raise
    except Exception as exc:
        if is_pyodbc_error(exc):
            raise ConnectionError(
                sql_connection_error_message(environment_name, exc)
            ) from exc
        raise


def query_scalar_primary(sql: str, params: tuple = ()) -> Any:
    rows = query_primary(sql, params)
    if not rows:
        return None
    row = rows[0]
    return next(iter(row.values()))


def exec_primary(sql: str, params: tuple = ()) -> None:
    _require_primary_ready()
    manager = get_connection_manager()
    try:
        with manager.connect("PRIMARY") as db:
            cursor = db.cursor()
            cursor.execute(sql, params)
            db.commit()
    except ConnectionError:
        raise
    except Exception as exc:
        if is_pyodbc_error(exc):
            raise ConnectionError(sql_connection_error_message("PRIMARY", exc)) from exc
        raise
