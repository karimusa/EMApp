"""Bootstrap configuration validation and self-test."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.app_connections_schema import (
    active_app_connections_sql,
    detect_sql_password_encrypted_column,
)
from config.settings import (
    _detect_env_file_encoding,
    _parse_dotenv_file,
    _read_env_file_text,
    get_env_file_path,
    load_env_file,
)

BOOTSTRAP_REGISTRY_PREVIEW_SQL = active_app_connections_sql(
    include_encrypted_password=False
)


@dataclass(frozen=True)
class BootstrapConfig:
    server: str
    database: str
    user: str
    password: str
    env_file: Path

    @property
    def password_loaded(self) -> bool:
        return bool((self.password or "").strip())

    @property
    def is_complete(self) -> bool:
        return bool(
            self.server.strip()
            and self.database.strip()
            and self.user.strip()
            and self.password_loaded
        )

    @classmethod
    def from_environment(cls, env_file: Path | None = None) -> BootstrapConfig:
        load_env_file()
        path = env_file or get_env_file_path()
        return cls(
            server=(os.getenv("BOOTSTRAP_SERVER") or "").strip(),
            database=(os.getenv("BOOTSTRAP_DATABASE") or "").strip(),
            user=(os.getenv("BOOTSTRAP_USER") or "").strip(),
            password=os.getenv("BOOTSTRAP_PASSWORD") or "",
            env_file=path,
        )


def _redact_env_line(line: str) -> str:
    if "=" not in line:
        return line
    key, _value = line.split("=", 1)
    if "PASSWORD" in key.upper() or "SECRET" in key.upper():
        return f"{key}=***"
    return line


def print_bootstrap_validation() -> BootstrapConfig:
    """Print exactly what was loaded from .env before mock vs SQL is decided."""
    env_file = load_env_file()
    bootstrap = BootstrapConfig.from_environment(env_file)

    print("BOOTSTRAP_SERVER =", repr(os.getenv("BOOTSTRAP_SERVER")))
    print("BOOTSTRAP_DATABASE =", repr(os.getenv("BOOTSTRAP_DATABASE")))
    print("BOOTSTRAP_USER =", repr(os.getenv("BOOTSTRAP_USER")))
    print("BOOTSTRAP_PASSWORD loaded =", bootstrap.password_loaded)
    print(".env =", env_file)

    if env_file.is_file():
        encoding = _detect_env_file_encoding(env_file)
        print(".env encoding =", encoding)
        print(".env file contents:")
        text = _read_env_file_text(env_file)
        if not text.strip():
            print("  <file is empty>")
        else:
            for line in text.splitlines():
                print(" ", _redact_env_line(line.rstrip("\r")))
        parsed = _parse_dotenv_file(env_file)
        print(".env parsed keys =", ", ".join(sorted(parsed.keys())) or "<none>")
    else:
        print(".env file contents:")
        print("  <file does not exist>")

    return bootstrap


def format_incomplete_bootstrap_message(bootstrap: BootstrapConfig) -> str:
    return f"""Bootstrap configuration is incomplete.

Edit:

{bootstrap.env_file}

Expected:

BOOTSTRAP_SERVER=SDAZ001MLD21
BOOTSTRAP_DATABASE=MonthEndOrchestrationDB
BOOTSTRAP_USER=MonthEndApp
BOOTSTRAP_PASSWORD=MonthEndApp

CONNECTION_SECRET_KEY is optional unless sql_password_encrypted is present and values are Fernet-encrypted.
Store SQL login passwords in orchestration.app_connections.sql_password_hash (current schema).
Do not store one-way hashes in orchestration.app_connections — use dbo.users.password_hash for app logins only.
"""


def require_bootstrap_config() -> BootstrapConfig:
    """Exit immediately when bootstrap credentials are missing."""
    bootstrap = print_bootstrap_validation()
    if not bootstrap.is_complete:
        print(format_incomplete_bootstrap_message(bootstrap), file=sys.stderr)
        raise SystemExit(1)
    return bootstrap


def load_bootstrap_config() -> BootstrapConfig:
    """Return bootstrap config after loading .env (no exit)."""
    load_env_file()
    return BootstrapConfig.from_environment()


def run_bootstrap_self_test(app_config: dict) -> list[dict[str, Any]]:
    """Connect with bootstrap credentials and read active app_connections rows."""
    from app.db.connection_manager import ConnectionManager

    manager = ConnectionManager(app_config)
    with manager.connect_bootstrap() as db:
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        include_encrypted = detect_sql_password_encrypted_column(cursor)
        registry_sql = active_app_connections_sql(
            include_encrypted_password=include_encrypted
        )
        cursor.execute(registry_sql)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def print_registry_rows(rows: list[dict[str, Any]]) -> None:
    print("\nActive orchestration.app_connections:")
    if not rows:
        print("  <no active rows>")
        return
    for row in rows:
        print(
            "  {environment_name} -> {server_name} / {database_name}".format(
                environment_name=row.get("environment_name"),
                server_name=row.get("server_name"),
                database_name=row.get("database_name"),
            )
        )


def run_bootstrap_self_test_and_print(app_config: dict) -> list[dict[str, Any]]:
    try:
        rows = run_bootstrap_self_test(app_config)
    except Exception as exc:
        print("Bootstrap connection: FAILED", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print_registry_rows(rows)
    print("\nBootstrap connection: SUCCESS")
    print("Runtime registry loaded successfully.")
    return rows
