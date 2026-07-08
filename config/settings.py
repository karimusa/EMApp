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
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

_ENV_FILE_PATH: Path | None = None


def get_env_file_path() -> Path:
    """Absolute path to the project-root .env file (e.g. G:\\EM\\.env)."""
    return BASE_DIR / ".env"


def load_env_file(*, override: bool = True) -> Path:
    """Load G:\\EM\\.env (project root) into os.environ.

    Uses override=True so values from .env win over empty pre-set environment
    variables (a common cause of DATA_SOURCE=auto staying in mock mode).
    """
    global _ENV_FILE_PATH
    path = get_env_file_path()
    if path.is_file():
        load_dotenv(path, override=override)
    _ENV_FILE_PATH = path
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
    print("DATA_SOURCE =", config.get("DATA_SOURCE"))
    print("BOOTSTRAP_SERVER =", config.get("BOOTSTRAP_SERVER"))
    print("BOOTSTRAP_DATABASE =", config.get("BOOTSTRAP_DATABASE"))
    print(".env loaded from =", config.get("ENV_FILE_PATH"))
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
