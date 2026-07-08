"""Application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    BASE_DIR = BASE_DIR
    LOGS_DIR = BASE_DIR / "logs"

    PORT = int(os.environ.get("PORT", 50006))
    HOST = os.environ.get("HOST", "127.0.0.1")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 28800

    # mock | sql | auto (sql when BOOTSTRAP_SERVER is set, else mock)
    DATA_SOURCE = os.environ.get("DATA_SOURCE", "auto")

    # Bootstrap — reaches MonthEndOrchestrationDB to load orchestration.app_connections
    BOOTSTRAP_DRIVER = os.environ.get("BOOTSTRAP_DRIVER", "ODBC Driver 18 for SQL Server")
    BOOTSTRAP_SERVER = os.environ.get("BOOTSTRAP_SERVER", "")
    BOOTSTRAP_DATABASE = os.environ.get("BOOTSTRAP_DATABASE", "MonthEndOrchestrationDB")
    BOOTSTRAP_USER = os.environ.get("BOOTSTRAP_USER", "")
    BOOTSTRAP_PASSWORD = os.environ.get("BOOTSTRAP_PASSWORD", "")
    BOOTSTRAP_TRUST_CERT = os.environ.get("BOOTSTRAP_TRUST_CERT", "yes")

    CONNECTION_SECRET_KEY = os.environ.get("CONNECTION_SECRET_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATA_SOURCE = "mock"
