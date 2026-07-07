"""Application configuration settings."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    LOGS_DIR = BASE_DIR / "logs"

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    # Application port (Month-End Orchestration default)
    PORT = int(os.environ.get("PORT", 50006))
    HOST = os.environ.get("HOST", "0.0.0.0")

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 28800  # 8 hours

    # Bootstrap connection — used only to reach MonthEndOrchestrationDB and load app_connections.
    # Server/database names are NOT hardcoded in application logic beyond these env fallbacks.
    BOOTSTRAP_DRIVER = os.environ.get("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server")
    BOOTSTRAP_SERVER = os.environ.get("BOOTSTRAP_SERVER", "")
    BOOTSTRAP_DATABASE = os.environ.get("BOOTSTRAP_DATABASE", "MonthEndOrchestrationDB")
    BOOTSTRAP_USER = os.environ.get("BOOTSTRAP_USER", "")
    BOOTSTRAP_PASSWORD = os.environ.get("BOOTSTRAP_PASSWORD", "")
    BOOTSTRAP_TRUST_CERT = os.environ.get("BOOTSTRAP_TRUST_CERT", "yes")

    # Fernet key for decrypting orchestration.app_connections passwords
    CONNECTION_SECRET_KEY = os.environ.get("CONNECTION_SECRET_KEY", "")

    # Orchestration phases displayed on dashboard
    ORCHESTRATION_PHASES = ("PRE", "MAIN", "BI", "DAY5", "POST")

    # SQL Agent job servers (display labels; actual connections from app_connections)
    SQL_AGENT_CONNECTION_NAMES = ("PRIMARY", "REMOTE_SQL")


class DevelopmentConfig(Config):
    DEBUG = True
    ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False
