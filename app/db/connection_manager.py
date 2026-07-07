"""Database connection manager — loads active connections from orchestration.app_connections."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generator, Optional

from app.db.crypto import decrypt_password

if TYPE_CHECKING:
    import pyodbc

logger = logging.getLogger(__name__)


def _import_pyodbc():
    import pyodbc

    return pyodbc


@dataclass
class AppConnection:
    connection_id: int
    connection_name: str
    server_name: str
    database_name: str
    username: str
    password: str
    driver: str
    is_active: bool
    trust_server_certificate: str = "yes"


class ConnectionManager:
    """Manages SQL Server connections loaded from orchestration.app_connections."""

    def __init__(self, app_config: dict):
        self._config = app_config
        self._connections: dict[str, AppConnection] = {}
        self._loaded = False

    def load_connections(self) -> None:
        """Load all active rows from orchestration.app_connections."""
        if self._config.get("TESTING"):
            self._connections = self._mock_connections()
            self._loaded = True
            return

        rows = self._fetch_app_connections()
        secret_key = self._config.get("CONNECTION_SECRET_KEY", "")
        self._connections = {}
        for row in rows:
            password = row.get("password_encrypted") or ""
            if password and secret_key:
                password = decrypt_password(password, secret_key)
            elif row.get("password_plain"):
                password = row["password_plain"]

            conn = AppConnection(
                connection_id=row["connection_id"],
                connection_name=row["connection_name"],
                server_name=row["server_name"],
                database_name=row["database_name"],
                username=row.get("username") or "",
                password=password,
                driver=row.get("driver") or self._config.get("BOOTSTRAP_DRIVER", ""),
                is_active=bool(row.get("is_active", True)),
                trust_server_certificate=row.get("trust_server_certificate") or "yes",
            )
            if conn.is_active:
                self._connections[conn.connection_name.upper()] = conn

        self._loaded = True
        logger.info("Loaded %d active app connection(s)", len(self._connections))

    def reload(self) -> None:
        self._loaded = False
        self.load_connections()

    def get(self, connection_name: str) -> Optional[AppConnection]:
        if not self._loaded:
            self.load_connections()
        return self._connections.get(connection_name.upper())

    def get_primary(self) -> Optional[AppConnection]:
        return self.get("PRIMARY")

    def get_remote(self) -> Optional[AppConnection]:
        return self.get("REMOTE_SQL")

    def all_connections(self) -> dict[str, AppConnection]:
        if not self._loaded:
            self.load_connections()
        return dict(self._connections)

    def build_connection_string(self, conn: AppConnection) -> str:
        parts = [
            f"DRIVER={{{conn.driver}}}",
            f"SERVER={conn.server_name}",
            f"DATABASE={conn.database_name}",
            f"UID={conn.username}",
            f"PWD={conn.password}",
            f"TrustServerCertificate={conn.trust_server_certificate}",
        ]
        return ";".join(parts)

    @contextmanager
    def connect(
        self, connection_name: str = "PRIMARY"
    ) -> Generator[Any, None, None]:
        pyodbc = _import_pyodbc()
        conn_info = self.get(connection_name)
        if not conn_info:
            raise ConnectionError(f"Connection '{connection_name}' not found or not active")
        connection_string = self.build_connection_string(conn_info)
        db = pyodbc.connect(connection_string, timeout=30)
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def connect_bootstrap(self) -> Generator[Any, None, None]:
        """Bootstrap connection using env vars to read orchestration.app_connections."""
        if self._config.get("TESTING"):
            raise ConnectionError("Bootstrap not available in test mode")

        pyodbc = _import_pyodbc()

        server = self._config.get("BOOTSTRAP_SERVER")
        database = self._config.get("BOOTSTRAP_DATABASE")
        user = self._config.get("BOOTSTRAP_USER")
        password = self._config.get("BOOTSTRAP_PASSWORD")
        driver = self._config.get("BOOTSTRAP_DRIVER")
        trust = self._config.get("BOOTSTRAP_TRUST_CERT", "yes")

        if not all([server, database, user]):
            raise ConnectionError(
                "Bootstrap connection not configured. Set BOOTSTRAP_SERVER, "
                "BOOTSTRAP_DATABASE, and BOOTSTRAP_USER environment variables."
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
        sql = """
            SELECT
                connection_id,
                connection_name,
                server_name,
                database_name,
                username,
                password_encrypted,
                password_plain,
                driver,
                is_active,
                trust_server_certificate
            FROM orchestration.app_connections
            WHERE is_active = 1
            ORDER BY connection_name
        """
        with self.connect_bootstrap() as db:
            cursor = db.cursor()
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _mock_connections(self) -> dict[str, AppConnection]:
        return {
            "PRIMARY": AppConnection(
                connection_id=1,
                connection_name="PRIMARY",
                server_name="SPUS001BDBEXT",
                database_name="MonthEndOrchestrationDB",
                username="mock_user",
                password="mock_pass",
                driver="ODBC Driver 18 for SQL Server",
                is_active=True,
            ),
            "REMOTE_SQL": AppConnection(
                connection_id=2,
                connection_name="REMOTE_SQL",
                server_name="SPAZ001EDM10",
                database_name="msdb",
                username="mock_user",
                password="mock_pass",
                driver="ODBC Driver 18 for SQL Server",
                is_active=True,
            ),
        }


_connection_manager: Optional[ConnectionManager] = None


def init_connection_manager(app) -> ConnectionManager:
    global _connection_manager
    _connection_manager = ConnectionManager(app.config)
    try:
        _connection_manager.load_connections()
    except Exception:
        logger.exception("Failed to load app_connections on startup")
    return _connection_manager


def get_connection_manager() -> ConnectionManager:
    if _connection_manager is None:
        raise RuntimeError("ConnectionManager not initialized")
    return _connection_manager
