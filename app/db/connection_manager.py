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

from app.db.credentials import (
    ConnectionCredentialError,
    is_one_way_hash,
    resolve_sql_login_password,
    stored_credential_from_row,
)
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
        sql_password_encrypted,
        sql_password_hash,
        description,
        created_at,
        updated_at
    FROM orchestration.app_connections
"""

ACTIVE_APP_CONNECTIONS_SQL = f"{APP_CONNECTIONS_SELECT}\n    WHERE is_active = 1"

LEGACY_APP_CONNECTIONS_SELECT = """
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

ACTIVE_APP_CONNECTIONS_LEGACY_SQL = (
    f"{LEGACY_APP_CONNECTIONS_SELECT}\n    WHERE is_active = 1"
)

APP_CONNECTIONS_REGISTRY_SQL = f"{APP_CONNECTIONS_SELECT}\n    ORDER BY environment_name"

LEGACY_APP_CONNECTIONS_REGISTRY_SQL = (
    f"{LEGACY_APP_CONNECTIONS_SELECT}\n    ORDER BY environment_name"
)


def _import_pyodbc():
    import pyodbc

    return pyodbc


def _uses_integrated_auth(auth_type: str | None) -> bool:
    value = (auth_type or "").strip().upper()
    return value in {"WINDOWS", "INTEGRATED", "SSPI", "NTLM"}


def _friendly_sql_error(environment_name: str, exc: Exception) -> ConnectionError:
    message = str(exc)
    if "18456" in message or "Login failed" in message:
        return ConnectionError(
            f"{environment_name}: SQL Server rejected the login for the configured "
            "runtime credentials. Update orchestration.app_connections."
            "sql_password_encrypted with the real SQL login password or Fernet "
            "ciphertext from scripts/encrypt_password.py."
        )
    return ConnectionError(
        f"{environment_name}: database connection failed. Contact your administrator."
    )


def is_pyodbc_error(exc: BaseException) -> bool:
    return exc.__class__.__module__.startswith("pyodbc")


@dataclass
class AppConnection:
    connection_id: int
    environment_name: str
    server_name: str
    database_name: str
    auth_type: str
    sql_username: str
    stored_credential: str | None
    description: str
    is_active: bool
    driver: str
    trust_server_certificate: str = "yes"
    password: str = ""


class ConnectionManager:
    def __init__(self, app_config: dict):
        self._config = app_config
        self._connections: dict[str, AppConnection] = {}
        self._connection_errors: dict[str, str] = {}
        self._primary_error: str | None = None

    def load_connections(self) -> None:
        rows = self._fetch_app_connections()
        self._connections = {}
        self._connection_errors = {}
        self._primary_error = None

        for row in rows:
            env_name = str(row["environment_name"]).upper()
            auth_type = (row.get("auth_type") or "sql").strip()
            sql_username = row.get("sql_username") or ""
            stored_credential = stored_credential_from_row(row)

            if _uses_integrated_auth(auth_type):
                password = ""
            else:
                try:
                    password = self._resolve_runtime_password(
                        env_name,
                        server_name=row["server_name"],
                        database_name=row["database_name"],
                        sql_username=sql_username,
                        stored_credential=stored_credential,
                    )
                except ConnectionError as exc:
                    self._connection_errors[env_name] = str(exc)
                    password = ""
                    logger.error("%s", exc)

            conn = AppConnection(
                connection_id=int(row["connection_id"]),
                environment_name=row["environment_name"],
                server_name=row["server_name"],
                database_name=row["database_name"],
                auth_type=auth_type,
                sql_username=sql_username,
                stored_credential=stored_credential,
                password=password,
                description=row.get("description") or "",
                is_active=True,
                driver=self._config.get("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server"),
                trust_server_certificate=self._config.get("BOOTSTRAP_TRUST_CERT", "yes"),
            )
            self._connections[env_name] = conn

        logger.info("Loaded %d active app connection(s)", len(self._connections))

    def _resolve_runtime_password(
        self,
        environment_name: str,
        *,
        server_name: str,
        database_name: str,
        sql_username: str,
        stored_credential: str | None,
    ) -> str:
        try:
            return resolve_sql_login_password(
                stored_credential,
                secret_key=self._config.get("CONNECTION_SECRET_KEY", ""),
                environment_name=environment_name,
                server_name=server_name,
                database_name=database_name,
                sql_username=sql_username,
                config=self._config,
            )
        except ConnectionCredentialError as exc:
            raise ConnectionError(str(exc)) from exc

    def validate_primary(self) -> None:
        """Verify PRIMARY credentials without allowing login when misconfigured."""
        self._primary_error = None
        if "PRIMARY" in self._connection_errors:
            self._primary_error = self._connection_errors["PRIMARY"]
            return
        if "PRIMARY" not in self._connections:
            self._primary_error = (
                "PRIMARY connection not found or not active in orchestration.app_connections."
            )
            return
        try:
            self.test_connection("PRIMARY")
        except ConnectionError as exc:
            self._primary_error = str(exc)
        except Exception as exc:
            if is_pyodbc_error(exc):
                self._primary_error = str(_friendly_sql_error("PRIMARY", exc))
                return
            logger.exception("PRIMARY connection validation failed")
            self._primary_error = (
                "PRIMARY database connection failed. Contact your administrator."
            )

    def get_primary_error(self) -> str | None:
        return self._primary_error

    def primary_ready(self) -> bool:
        return self._primary_error is None and "PRIMARY" in self._connections

    def reload(self) -> None:
        self.load_connections()
        self.validate_primary()

    def get(self, environment_name: str) -> Optional[AppConnection]:
        return self._connections.get(environment_name.upper())

    def get_primary(self) -> Optional[AppConnection]:
        return self.get("PRIMARY")

    def all_connections(self) -> dict[str, AppConnection]:
        return dict(self._connections)

    def build_connection_string(
        self,
        conn: AppConnection,
        *,
        password: str | None = None,
    ) -> str:
        resolved_password = password
        if resolved_password is None and not _uses_integrated_auth(conn.auth_type):
            resolved_password = self._resolve_runtime_password(
                conn.environment_name,
                server_name=conn.server_name,
                database_name=conn.database_name,
                sql_username=conn.sql_username,
                stored_credential=conn.stored_credential,
            )
        parts = [
            f"DRIVER={{{conn.driver}}}",
            f"SERVER={conn.server_name}",
            f"DATABASE={conn.database_name}",
        ]
        if _uses_integrated_auth(conn.auth_type):
            parts.append("Trusted_Connection=yes")
        else:
            parts.extend([f"UID={conn.sql_username}", f"PWD={resolved_password or ''}"])
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
        env_name = environment_name.upper()
        if env_name in self._connection_errors:
            raise ConnectionError(self._connection_errors[env_name])

        conn_info = self.get(env_name)
        if not conn_info:
            raise ConnectionError(
                f"Environment '{environment_name}' not found or not active"
            )
        if not _uses_integrated_auth(conn_info.auth_type):
            try:
                runtime_password = self._resolve_runtime_password(
                    env_name,
                    server_name=conn_info.server_name,
                    database_name=conn_info.database_name,
                    sql_username=conn_info.sql_username,
                    stored_credential=conn_info.stored_credential,
                )
            except ConnectionError:
                raise
            if not runtime_password:
                raise ConnectionError(
                    f"Environment '{environment_name}' has no SQL login password configured."
                )
            if is_one_way_hash(runtime_password):
                raise ConnectionError(
                    f"{env_name}: refusing to connect with a one-way hash as the SQL password."
                )
        else:
            runtime_password = None

        try:
            db = pyodbc.connect(
                self.build_connection_string(conn_info, password=runtime_password),
                timeout=30,
            )
        except Exception as exc:
            if is_pyodbc_error(exc):
                raise _friendly_sql_error(env_name, exc) from exc
            raise
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
            for sql in (ACTIVE_APP_CONNECTIONS_SQL, ACTIVE_APP_CONNECTIONS_LEGACY_SQL):
                try:
                    cursor.execute(sql)
                    break
                except Exception as exc:
                    if sql is ACTIVE_APP_CONNECTIONS_LEGACY_SQL:
                        raise
                    if "sql_password_encrypted" not in str(exc):
                        raise
                    logger.warning(
                        "sql_password_encrypted column missing; using legacy registry query"
                    )
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
        try:
            _connection_manager.validate_primary()
        except Exception:
            logger.exception("Failed to validate PRIMARY connection on startup")
    return _connection_manager


def get_connection_manager() -> ConnectionManager:
    if _connection_manager is None:
        raise RuntimeError("ConnectionManager not initialized")
    return _connection_manager
