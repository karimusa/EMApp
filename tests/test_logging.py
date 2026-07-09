"""Logging configuration behavior."""

from unittest.mock import patch

from app import create_app
from config.settings import DevelopmentConfig, TestingConfig


def test_testing_config_uses_stderr_not_file_log():
    app = create_app(TestingConfig)
    handlers = app.logger.handlers
    assert handlers
    assert all(type(h).__name__ != "RotatingFileHandler" for h in handlers)


def test_skip_file_log_env_uses_stderr(monkeypatch):
    monkeypatch.setenv("EMAPP_SKIP_FILE_LOG", "1")
    app = create_app(DevelopmentConfig)
    handlers = app.logger.handlers
    assert handlers
    assert all(type(h).__name__ != "RotatingFileHandler" for h in handlers)


def test_locked_log_file_falls_back_to_stderr(monkeypatch, tmp_path):
    monkeypatch.delenv("EMAPP_SKIP_FILE_LOG", raising=False)

    class LockedConfig(DevelopmentConfig):
        LOGS_DIR = tmp_path / "logs"

    with patch(
        "app.RotatingFileHandler",
        side_effect=PermissionError(13, "Permission denied"),
    ):
        app = create_app(LockedConfig)

    handlers = app.logger.handlers
    assert any(type(h).__name__ == "StreamHandler" for h in handlers)
    assert all(type(h).__name__ != "RotatingFileHandler" for h in handlers)
