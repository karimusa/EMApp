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

from app.db.app_connections_schema import (
    active_app_connections_sql,
    detect_sql_password_encrypted_column,
    registry_app_connections_sql,
    runtime_credential_column_label,
)
from app.db.credentials import (
    ConnectionCredentialError,
    is_one_way_hash,
    is_unusable_stored_credential,
    matches_bootstrap_target,
    resolve_sql_login_password,
    resolve_sql_login_password_with_source,
    stored_credential_details,
    stored_credential_from_row,
)
from config.settings import should_use_mock_data

if TYPE_CHECKING:
    import pyodbc

logger = logging.getLogger(__name__)

# Bump when PRIMARY runtime credential behavior changes (visible in startup logs).
RUNTIME_CREDENTIAL_BUILD_ID = "live-schema-compat-2026-07-09"

# Backward-compatible exports for tests and callers.
APP_CONNECTIONS_SELECT = active_app_connections_sql(include_encrypted_password=False).replace(
    "\n    WHERE is_active = 1", ""
)
ACTIVE_APP_CONNECTIONS_SQL = active_app_connections_sql(include_encrypted_password=False)
LEGACY_APP_CONNECTIONS_SELECT = APP_CONNECTIONS_SELECT
ACTIVE_APP_CONNECTIONS_LEGACY_SQL = ACTIVE_APP_CONNECTIONS_SQL
APP_CONNECTIONS_REGISTRY_SQL = registry_app_connections_sql(include_encrypted_password=False)
LEGACY_APP_CONNECTIONS_REGISTRY_SQL = APP_CONNECTIONS_REGISTRY_SQL


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
            "sql_password_hash with the real SQL login password (plain text for "
            "development) or apply the sql_password_encrypted migration and store "
            "a Fernet ciphertext from scripts/encrypt_password.py."
        )
    return ConnectionError(
        f"{environment_name}: database connection failed. Contact your administrator."
    )


def is_pyodbc_error(exc: BaseException) -> bool:
    module = getattr(exc.__class__, "__module__", "") or ""
    if module.startswith("pyodbc"):
        return True
    if exc.__class__.__name__ in {
        "InterfaceError",
        "OperationalError",
        "ProgrammingError",
        "DatabaseError",
        "Error",
    }:
        if "pyodbc" in module.lower():
            return True
    message = str(exc)
    return "18456" in message or "[Microsoft][ODBC Driver" in message


def sql_connection_error_message(
    environment_name: str,
    exc: BaseException,
) -> str:
    return str(_friendly_sql_error(environment_name, exc))


@dataclass(frozen=True)
class ConnectionDiagnostics:
    driver: str
    server: str
    database: str
    uid: str
    trust_server_certificate: str
    password_source: str
    encrypt: str = "<not set>"


def _format_connection_diagnostics(params: ConnectionDiagnostics) -> str:
    lines = [
        f"Driver={{{params.driver}}}",
        f"Server={params.server}",
        f"Database={params.database}",
        f"UID={params.uid}",
        "PWD=<hidden>",
        f"Encrypt={params.encrypt}",
        f"TrustServerCertificate={params.trust_server_certificate}",
        f"PasswordSource={params.password_source}",
    ]
    return "\n".join(lines)


def _log_bootstrap_vs_primary(
    bootstrap: ConnectionDiagnostics,
    primary: ConnectionDiagnostics,
) -> None:
    logger.info("=== ODBC connection comparison: BOOTSTRAP vs PRIMARY ===")
    logger.info(
        "BOOTSTRAP connection string values:\n%s",
        _format_connection_diagnostics(bootstrap),
    )
    logger.info(
        "PRIMARY connection string values:\n%s",
        _format_connection_diagnostics(primary),
    )

    fields = (
        ("Driver", bootstrap.driver, primary.driver),
        ("Server", bootstrap.server, primary.server),
        ("Database", bootstrap.database, primary.database),
        ("UID", bootstrap.uid, primary.uid),
        ("Encrypt", bootstrap.encrypt, primary.encrypt),
        (
            "TrustServerCertificate",
            bootstrap.trust_server_certificate,
            primary.trust_server_certificate,
        ),
        ("PasswordSource", bootstrap.password_source, primary.password_source),
    )
    for label, left, right in fields:
        if left == right:
            logger.info("  MATCH %-24s %r", label + ":", left)
        else:
            logger.info(
                "  DIFF  %-24s bootstrap=%r primary=%r",
                label + ":",
                left,
                right,
            )
    logger.info("=== end ODBC connection comparison ===")


@dataclass
class AppConnection:
    connection_id: int
    environment_name: str
    server_name: str
    database_name: str
    auth_type: str
    sql_username: str
    stored_credential: str | None
    credential_origin_column: str | None
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
        self._sql_password_encrypted_available: bool | None = None

    @property
    def sql_password_encrypted_available(self) -> bool:
        return bool(self._sql_password_encrypted_available)

    def load_connections(self) -> None:
        rows = self._fetch_app_connections()
        self._connections = {}
        self._connection_errors = {}
        self._primary_error = None

        for row in rows:
            env_name = str(row["environment_name"]).upper()
            auth_type = (row.get("auth_type") or "sql").strip()
            sql_username = row.get("sql_username") or ""
            credential_details = stored_credential_details(row)
            stored_credential = credential_details.value

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
                        origin_column=credential_details.origin_column,
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
                credential_origin_column=credential_details.origin_column,
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
        origin_column: str | None = None,
    ) -> str:
        return self._resolve_runtime_password_with_source(
            environment_name,
            server_name=server_name,
            database_name=database_name,
            sql_username=sql_username,
            stored_credential=stored_credential,
            origin_column=origin_column,
        ).password

    def _resolve_runtime_password_with_source(
        self,
        environment_name: str,
        *,
        server_name: str,
        database_name: str,
        sql_username: str,
        stored_credential: str | None,
        origin_column: str | None = None,
    ):
        try:
            return resolve_sql_login_password_with_source(
                stored_credential,
                secret_key=self._config.get("CONNECTION_SECRET_KEY", ""),
                environment_name=environment_name,
                server_name=server_name,
                database_name=database_name,
                sql_username=sql_username,
                config=self._config,
                origin_column=origin_column,
                include_encrypted_password=self.sql_password_encrypted_available,
            )
        except ConnectionCredentialError as exc:
            raise ConnectionError(str(exc)) from exc

    def _bootstrap_connection_diagnostics(self) -> ConnectionDiagnostics:
        return ConnectionDiagnostics(
            driver=self._config.get("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server"),
            server=(self._config.get("BOOTSTRAP_SERVER") or "").strip(),
            database=(self._config.get("BOOTSTRAP_DATABASE") or "").strip(),
            uid=(self._config.get("BOOTSTRAP_USER") or "").strip(),
            trust_server_certificate=self._config.get("BOOTSTRAP_TRUST_CERT", "yes"),
            password_source="BOOTSTRAP_PASSWORD",
        )

    def _primary_connection_diagnostics(
        self,
        conn_info: AppConnection,
        *,
        runtime_user: str,
        password_source: str,
    ) -> ConnectionDiagnostics:
        return ConnectionDiagnostics(
            driver=conn_info.driver,
            server=conn_info.server_name,
            database=conn_info.database_name,
            uid=runtime_user,
            trust_server_certificate=conn_info.trust_server_certificate,
            password_source=password_source,
        )

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

    def ensure_primary_validated(self, *, reload_registry: bool = True) -> str | None:
        """Same validation path used by setup.ps1 -TestConnection and /login."""
        if reload_registry:
            self.reload()
        else:
            self.validate_primary()
        return self.get_primary_error()

    def _runtime_sql_credentials(
        self,
        conn_info: AppConnection,
        *,
        environment_name: str,
    ) -> tuple[str, str, str]:
        if _uses_integrated_auth(conn_info.auth_type):
            return conn_info.sql_username, "", "integrated auth"

        bootstrap_user = (self._config.get("BOOTSTRAP_USER") or "").strip()
        bootstrap_password = (self._config.get("BOOTSTRAP_PASSWORD") or "").strip()
        sql_username = (conn_info.sql_username or "").strip() or bootstrap_user
        secret_key = self._config.get("CONNECTION_SECRET_KEY", "")

        if bootstrap_password and matches_bootstrap_target(
            conn_info.server_name,
            conn_info.database_name,
            sql_username,
            self._config,
        ) and is_unusable_stored_credential(
            conn_info.stored_credential,
            secret_key=secret_key,
        ):
            logger.info(
                "%s: inheriting BOOTSTRAP_PASSWORD because stored credential is unusable",
                environment_name,
            )
            return sql_username, bootstrap_password, "BOOTSTRAP_PASSWORD"

        resolution = self._resolve_runtime_password_with_source(
            environment_name,
            server_name=conn_info.server_name,
            database_name=conn_info.database_name,
            sql_username=sql_username,
            stored_credential=conn_info.stored_credential,
            origin_column=conn_info.credential_origin_column,
        )
        if is_one_way_hash(resolution.password):
            raise ConnectionError(
                f"{environment_name}: refusing to connect with a one-way hash as the SQL password."
            )
        return sql_username, resolution.password, resolution.source

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
        username: str | None = None,
    ) -> str:
        sql_username = username if username is not None else conn.sql_username
        resolved_password = password
        if resolved_password is None and not _uses_integrated_auth(conn.auth_type):
            _, resolved_password, _source = self._runtime_sql_credentials(
                conn,
                environment_name=conn.environment_name,
            )
        parts = [
            f"DRIVER={{{conn.driver}}}",
            f"SERVER={conn.server_name}",
            f"DATABASE={conn.database_name}",
        ]
        if _uses_integrated_auth(conn.auth_type):
            parts.append("Trusted_Connection=yes")
        else:
            parts.extend([f"UID={sql_username}", f"PWD={resolved_password or ''}"])
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
                runtime_user, runtime_password, password_source = (
                    self._runtime_sql_credentials(
                        conn_info,
                        environment_name=env_name,
                    )
                )
            except ConnectionError:
                raise
            if not runtime_password:
                raise ConnectionError(
                    f"Environment '{environment_name}' has no SQL login password configured."
                )
            if env_name == "PRIMARY":
                _log_bootstrap_vs_primary(
                    self._bootstrap_connection_diagnostics(),
                    self._primary_connection_diagnostics(
                        conn_info,
                        runtime_user=runtime_user,
                        password_source=password_source,
                    ),
                )
        else:
            runtime_user = conn_info.sql_username
            runtime_password = None
            password_source = "integrated auth"

        try:
            db = pyodbc.connect(
                self.build_connection_string(
                    conn_info,
                    password=runtime_password,
                    username=runtime_user,
                ),
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
            if self._sql_password_encrypted_available is None:
                self._sql_password_encrypted_available = detect_sql_password_encrypted_column(
                    cursor
                )
                if self._sql_password_encrypted_available:
                    logger.info(
                        "orchestration.app_connections.sql_password_encrypted is available"
                    )
                else:
                    logger.info(
                        "orchestration.app_connections uses legacy sql_password_hash column only"
                    )

            sql = active_app_connections_sql(
                include_encrypted_password=self._sql_password_encrypted_available
            )
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def registry_sql(self) -> str:
        include_encrypted = (
            self._sql_password_encrypted_available
            if self._sql_password_encrypted_available is not None
            else False
        )
        return registry_app_connections_sql(include_encrypted_password=include_encrypted)

    def runtime_credential_column(self) -> str:
        return runtime_credential_column_label(
            include_encrypted_password=self.sql_password_encrypted_available
        )


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
        logger.info(
            "ConnectionManager ready (%s)", RUNTIME_CREDENTIAL_BUILD_ID
        )
    return _connection_manager


def get_connection_manager() -> ConnectionManager:
    if _connection_manager is None:
        raise RuntimeError("ConnectionManager not initialized")
    return _connection_manager
