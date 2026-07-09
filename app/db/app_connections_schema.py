"""Schema helpers for orchestration.app_connections.

The live database may not yet have ``sql_password_encrypted``. Runtime code must
probe for that column and only include it in SELECT statements when present.
"""

from __future__ import annotations

_COLUMN_DETECTION_SQL = (
    "SELECT COL_LENGTH('orchestration.app_connections', 'sql_password_encrypted')"
)

_BASE_SELECT_COLUMNS = """
        connection_id,
        environment_name,
        is_active,
        server_name,
        database_name,
        auth_type,
        sql_username,
"""

_TRAILING_SELECT_COLUMNS = """
        sql_password_hash,
        description,
        created_at,
        updated_at
    FROM orchestration.app_connections
"""


def detect_sql_password_encrypted_column(cursor) -> bool:
    """Return True when sql_password_encrypted exists on app_connections."""
    cursor.execute(_COLUMN_DETECTION_SQL)
    row = cursor.fetchone()
    return bool(row and row[0] is not None)


def build_app_connections_select(*, include_encrypted_password: bool) -> str:
    columns = _BASE_SELECT_COLUMNS
    if include_encrypted_password:
        columns += "        sql_password_encrypted,\n"
    return f"SELECT\n{columns}{_TRAILING_SELECT_COLUMNS}"


def active_app_connections_sql(*, include_encrypted_password: bool) -> str:
    return (
        f"{build_app_connections_select(include_encrypted_password=include_encrypted_password)}\n"
        "    WHERE is_active = 1"
    )


def registry_app_connections_sql(*, include_encrypted_password: bool) -> str:
    return (
        f"{build_app_connections_select(include_encrypted_password=include_encrypted_password)}\n"
        "    ORDER BY environment_name"
    )


def runtime_credential_column_label(*, include_encrypted_password: bool) -> str:
    if include_encrypted_password:
        return "sql_password_encrypted"
    return "sql_password_hash"
