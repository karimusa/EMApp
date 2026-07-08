"""Application configuration — single source of truth for .env and runtime settings.

Enterprise connection model
---------------------------
``.env`` supplies only the **bootstrap** connection to MonthEndOrchestrationDB
(``BOOTSTRAP_*``). After bootstrap succeeds, every operational SQL connection
is loaded from ``orchestration.app_connections`` by ``ConnectionManager`` and
used exclusively through the repository layer.

The running application never reads runtime server/database names from ``.env``.
Seed-time connection targets (``SEED_*``) belong in ``scripts/seed.env``, not
the application ``.env``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_ENV_FILE_PATH: Path | None = None
_ENV_LINE_RE = re.compile(
    r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$",
    re.IGNORECASE,
)


def get_env_file_path() -> Path:
    """Absolute path to the project-root .env file (e.g. G:\\EM\\.env)."""
    return BASE_DIR / ".env"


def _detect_env_file_encoding(path: Path) -> str:
    """Best-effort encoding detection for debug output."""
    if not path.is_file():
        return "missing"
    raw = path.read_bytes()[:4]
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    for encoding in ("utf-8-sig", "utf-16", "utf-8", "cp1252"):
        try:
            path.read_text(encoding=encoding)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "unknown"


def _read_env_file_text(path: Path) -> str:
    """Read .env text, trying common Windows encodings (UTF-8, UTF-16, BOM)."""
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def _parse_dotenv_text(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines — matches setup.ps1 Load-DotEnv behavior."""
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(line)
        if not match:
            continue
        name = match.group(1).strip().lstrip("\ufeff")
        value = match.group(2).strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]
        parsed[name] = value
    return parsed


def _parse_dotenv_file(path: Path) -> dict[str, str]:
    return _parse_dotenv_text(_read_env_file_text(path))


def _apply_parsed_env(parsed: dict[str, str]) -> None:
    """Apply parsed .env values.

    Non-empty file values always win. Empty file values do not wipe non-empty
    process-environment values (common when .env.example placeholders exist).
    """
    for key, file_value in parsed.items():
        if file_value.strip():
            os.environ[key] = file_value
        elif key not in os.environ:
            os.environ[key] = file_value


def load_env_file(*, override: bool = True) -> Path:
    """Load G:\\EM\\.env (project root) into os.environ.

    Uses a Windows-safe parser (UTF-8/UTF-16/BOM) aligned with setup.ps1
    Load-DotEnv. The override flag is accepted for API compatibility.
    """
    del override  # manual parser applies non-empty file values unconditionally
    global _ENV_FILE_PATH
    path = get_env_file_path()
    _ENV_FILE_PATH = path
    if path.is_file():
        parsed = _parse_dotenv_file(path)
        _apply_parsed_env(parsed)
    return path


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or str(raw).strip() == "":
        return default
    return int(raw)


def build_runtime_config(*, testing: bool = False) -> dict:
    """Read configuration from the environment at call time (not import time)."""
    load_env_file()
    env_path = _ENV_FILE_PATH or get_env_file_path()
    return {
        "SECRET_KEY": _env("SECRET_KEY", "dev-secret-key-change-in-production"),
        "BASE_DIR": BASE_DIR,
        "LOGS_DIR": BASE_DIR / "logs",
        "PORT": _env_int("PORT", 50006),
        "HOST": _env("HOST", "127.0.0.1"),
        "DATA_SOURCE": _env("DATA_SOURCE", "auto"),
        "BOOTSTRAP_DRIVER": _env("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server"),
        "BOOTSTRAP_SERVER": _env("BOOTSTRAP_SERVER", "").strip(),
        "BOOTSTRAP_DATABASE": _env("BOOTSTRAP_DATABASE", "").strip(),
        "BOOTSTRAP_USER": _env("BOOTSTRAP_USER", "").strip(),
        "BOOTSTRAP_PASSWORD": _env("BOOTSTRAP_PASSWORD", ""),
        "BOOTSTRAP_TRUST_CERT": _env("BOOTSTRAP_TRUST_CERT", "yes"),
        "CONNECTION_SECRET_KEY": _env("CONNECTION_SECRET_KEY", ""),
        "ENV_FILE_PATH": str(env_path),
    }


def should_use_mock_data(config: dict) -> bool:
    """Return True when the app should use mock_data instead of SQL repositories."""
    if config.get("TESTING"):
        return True
    mode = (config.get("DATA_SOURCE") or "auto").lower()
    if mode == "mock":
        return True
    if mode == "sql":
        return False
    return not bool((config.get("BOOTSTRAP_SERVER") or "").strip())


def print_config_debug(config: dict) -> None:
    """Temporary debug output — bootstrap settings only (not runtime connections)."""
    from config.bootstrap import print_bootstrap_validation

    print("DATA_SOURCE =", config.get("DATA_SOURCE"))
    print_bootstrap_validation()
    print("Runtime connections = orchestration.app_connections (loaded after bootstrap)")


def apply_runtime_config(app) -> None:
    """Apply live .env values to Flask app.config after from_object()."""
    testing = bool(app.config.get("TESTING"))
    runtime = build_runtime_config(testing=testing)
    runtime["TESTING"] = app.config.get("TESTING", False)
    runtime["DEBUG"] = app.config.get("DEBUG", False)
    if app.config.get("SESSION_COOKIE_SECURE") is not None:
        runtime["SESSION_COOKIE_SECURE"] = app.config["SESSION_COOKIE_SECURE"]
    if testing:
        runtime["DATA_SOURCE"] = "mock"
    app.config.update(runtime)
    print_config_debug(app.config)


class Config:
    """Static Flask defaults; env-driven values are applied in apply_runtime_config()."""

    DEBUG = False
    TESTING = False

    BASE_DIR = BASE_DIR
    LOGS_DIR = BASE_DIR / "logs"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 28800

    # Placeholders — overwritten by apply_runtime_config() at app startup
    SECRET_KEY = "dev-secret-key-change-in-production"
    PORT = 50006
    HOST = "127.0.0.1"
    DATA_SOURCE = "auto"
    BOOTSTRAP_DRIVER = "ODBC Driver 18 for SQL Server"
    BOOTSTRAP_SERVER = ""
    BOOTSTRAP_DATABASE = ""
    BOOTSTRAP_USER = ""
    BOOTSTRAP_PASSWORD = ""
    BOOTSTRAP_TRUST_CERT = "yes"
    CONNECTION_SECRET_KEY = ""
    ENV_FILE_PATH = ""


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATA_SOURCE = "mock"
