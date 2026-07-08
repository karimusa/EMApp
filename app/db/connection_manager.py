"""Database connection manager — bootstrap + orchestration.app_connections.

Bootstrap flow
--------------
1. Read ``BOOTSTRAP_*`` from ``.env`` (only place server names belong in env).
2. Connect to MonthEndOrchestrationDB.
3. SELECT active rows from ``orchestration.app_connections`` (``environment_name`` registry).
4. Build ODBC connection strings dynamically from those rows.
5. Repositories call ``connect()`` / ``query_primary()`` / ``query_connection()``.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generator, Optional

from app.db.crypto import decrypt_password
from config.settings import should_use_mock_data

if TYPE_CHECKING:
    import pyodbc

logger = logging.getLogger(__name__)

APP_CONNECTIONS_SELECT = """
    SELECT
        connection_id,
        environment_name,
        is_active,
        server_name,
        database_name,
        auth_type,
        sql_username,
        sql_password_hash,
        description,
        created_at,
        updated_at
    FROM orchestration.app_connections
"""

ACTIVE_APP_CONNECTIONS_SQL = f"{APP_CONNECTIONS_SELECT}\n    WHERE is_active = 1"

APP_CONNECTIONS_REGISTRY_SQL = f"{APP_CONNECTIONS_SELECT}\n    ORDER BY environment_name"


def _import_pyodbc():
    import pyodbc

    return pyodbc


def _normalize_sql_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def _matches_bootstrap_target(
    server_name: str,
    database_name: str,
    sql_username: str,
    config: dict,
) -> bool:
    return (
        _normalize_sql_identifier(server_name)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_SERVER"))
        and _normalize_sql_identifier(database_name)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_DATABASE"))
        and _normalize_sql_identifier(sql_username)
        == _normalize_sql_identifier(config.get("BOOTSTRAP_USER"))
    )


def _resolve_sql_password(
    sql_password_hash: str | None,
    secret_key: str,
    *,
    server_name: str = "",
    database_name: str = "",
    sql_username: str = "",
    config: dict | None = None,
) -> str:
    raw = (sql_password_hash or "").strip()
    if not raw:
        password = ""
    elif secret_key:
        password = decrypt_password(raw, secret_key)
        if not password:
            logger.warning(
                "Could not decrypt sql_password_hash for %s/%s; "
                "check CONNECTION_SECRET_KEY or store plain text",
                server_name,
                database_name,
            )
            password = ""
    else:
        password = raw

    if password:
        return password

    if config and _matches_bootstrap_target(
        server_name, database_name, sql_username, config
    ):
        bootstrap_password = config.get("BOOTSTRAP_PASSWORD") or ""
        if bootstrap_password:
            logger.info(
                "Using bootstrap password for %s/%s (%s)",
                server_name,
                database_name,
                sql_username,
            )
            return bootstrap_password

    return ""


def _uses_integrated_auth(auth_type: str | None) -> bool:
    value = (auth_type or "").strip().upper()
    return value in {"WINDOWS", "INTEGRATED", "SSPI", "NTLM"}


@dataclass
class AppConnection:
    connection_id: int
    environment_name: str
    server_name: str
    database_name: str
    auth_type: str
    sql_username: str
    password: str
    description: str
    is_active: bool
    driver: str
    trust_server_certificate: str = "yes"


class ConnectionManager:
    def __init__(self, app_config: dict):
        self._config = app_config
        self._connections: dict[str, AppConnection] = {}

    def load_connections(self) -> None:
        rows = self._fetch_app_connections()
        secret_key = self._config.get("CONNECTION_SECRET_KEY", "")
        self._connections = {}
        for row in rows:
            conn = AppConnection(
                connection_id=int(row["connection_id"]),
                environment_name=row["environment_name"],
                server_name=row["server_name"],
                database_name=row["database_name"],
                auth_type=(row.get("auth_type") or "sql").strip(),
                sql_username=row.get("sql_username") or "",
                password=_resolve_sql_password(
                    row.get("sql_password_hash"),
                    secret_key,
                    server_name=row["server_name"],
                    database_name=row["database_name"],
                    sql_username=row.get("sql_username") or "",
                    config=self._config,
                ),
                description=row.get("description") or "",
                is_active=True,
                driver=self._config.get("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server"),
                trust_server_certificate=self._config.get("BOOTSTRAP_TRUST_CERT", "yes"),
            )
            self._connections[conn.environment_name.upper()] = conn

        logger.info("Loaded %d active app connection(s)", len(self._connections))

    def reload(self) -> None:
        self.load_connections()

    def get(self, environment_name: str) -> Optional[AppConnection]:
        return self._connections.get(environment_name.upper())

    def get_primary(self) -> Optional[AppConnection]:
        return self.get("PRIMARY")

    def all_connections(self) -> dict[str, AppConnection]:
        return dict(self._connections)

    def build_connection_string(self, conn: AppConnection) -> str:
        parts = [
            f"DRIVER={{{conn.driver}}}",
            f"SERVER={conn.server_name}",
            f"DATABASE={conn.database_name}",
        ]
        if _uses_integrated_auth(conn.auth_type):
            parts.append("Trusted_Connection=yes")
        else:
            parts.extend([f"UID={conn.sql_username}", f"PWD={conn.password}"])
        parts.append(f"TrustServerCertificate={conn.trust_server_certificate}")
        return ";".join(parts)

    def test_connection(self, environment_name: str = "PRIMARY") -> None:
        """Open environment connection and run ``SELECT 1``."""
        with self.connect(environment_name) as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

    @contextmanager
    def connect(self, environment_name: str = "PRIMARY") -> Generator[Any, None, None]:
        pyodbc = _import_pyodbc()
        conn_info = self.get(environment_name)
        if not conn_info:
            raise ConnectionError(
                f"Environment '{environment_name}' not found or not active"
            )
        if not _uses_integrated_auth(conn_info.auth_type) and not conn_info.password:
            raise ConnectionError(
                f"Environment '{environment_name}' has no SQL password configured. "
                "Update orchestration.app_connections.sql_password_hash or ensure "
                "it matches the bootstrap target so BOOTSTRAP_PASSWORD can be used."
            )
        db = pyodbc.connect(self.build_connection_string(conn_info), timeout=30)
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def connect_bootstrap(self) -> Generator[Any, None, None]:
        pyodbc = _import_pyodbc()
        server = self._config.get("BOOTSTRAP_SERVER")
        database = self._config.get("BOOTSTRAP_DATABASE")
        user = self._config.get("BOOTSTRAP_USER")
        password = self._config.get("BOOTSTRAP_PASSWORD", "")
        driver = self._config.get("BOOTSTRAP_DRIVER")
        trust = self._config.get("BOOTSTRAP_TRUST_CERT", "yes")

        if not all([server, database, user]):
            raise ConnectionError(
                "Bootstrap connection not configured. Set BOOTSTRAP_SERVER, "
                "BOOTSTRAP_DATABASE, and BOOTSTRAP_USER."
            )

        connection_string = ";".join(
            [
                f"DRIVER={{{driver}}}",
                f"SERVER={server}",
                f"DATABASE={database}",
                f"UID={user}",
                f"PWD={password}",
                f"TrustServerCertificate={trust}",
            ]
        )
        db = pyodbc.connect(connection_string, timeout=30)
        try:
            yield db
        finally:
            db.close()

    def _fetch_app_connections(self) -> list[dict[str, Any]]:
        with self.connect_bootstrap() as db:
            cursor = db.cursor()
            cursor.execute(ACTIVE_APP_CONNECTIONS_SQL)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


_connection_manager: Optional[ConnectionManager] = None


def init_connection_manager(app) -> ConnectionManager:
    global _connection_manager
    _connection_manager = ConnectionManager(app.config)
    if app.config.get("TESTING"):
        return _connection_manager
    if should_use_mock_data(app.config):
        return _connection_manager
    if app.config.get("BOOTSTRAP_SERVER"):
        try:
            _connection_manager.load_connections()
        except Exception:
            logger.exception("Failed to load app_connections on startup")
    return _connection_manager


def get_connection_manager() -> ConnectionManager:
    if _connection_manager is None:
        raise RuntimeError("ConnectionManager not initialized")
    return _connection_manager
