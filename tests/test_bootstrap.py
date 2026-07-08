"""Tests for bootstrap configuration validation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from config.bootstrap import (
    BootstrapConfig,
    format_incomplete_bootstrap_message,
    load_bootstrap_config,
    require_bootstrap_config,
)


def test_bootstrap_config_complete():
    cfg = BootstrapConfig(
        server="SDAZ001MLD21",
        database="MonthEndOrchestrationDB",
        user="MonthEndApp",
        password="secret",
        env_file=Path("G:/EM/.env"),
    )
    assert cfg.is_complete
    assert cfg.password_loaded


def test_bootstrap_config_incomplete():
    cfg = BootstrapConfig(
        server="",
        database="MonthEndOrchestrationDB",
        user="MonthEndApp",
        password="secret",
        env_file=Path("G:/EM/.env"),
    )
    assert not cfg.is_complete


def test_require_bootstrap_config_exits_when_incomplete(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("BOOTSTRAP_SERVER=\nBOOTSTRAP_DATABASE=\n", encoding="utf-8")
    monkeypatch.setattr("config.settings.get_env_file_path", lambda: env_file)
    monkeypatch.delenv("BOOTSTRAP_SERVER", raising=False)
    monkeypatch.delenv("BOOTSTRAP_DATABASE", raising=False)
    monkeypatch.delenv("BOOTSTRAP_USER", raising=False)
    monkeypatch.delenv("BOOTSTRAP_PASSWORD", raising=False)

    with pytest.raises(SystemExit) as exc:
        require_bootstrap_config()
    assert exc.value.code == 1


def test_load_bootstrap_config_from_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BOOTSTRAP_SERVER=SDAZ001MLD21\n"
        "BOOTSTRAP_DATABASE=MonthEndOrchestrationDB\n"
        "BOOTSTRAP_USER=MonthEndApp\n"
        "BOOTSTRAP_PASSWORD=secret\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("config.settings.get_env_file_path", lambda: env_file)

    cfg = load_bootstrap_config()
    assert cfg.is_complete
    assert cfg.server == "SDAZ001MLD21"


def test_incomplete_message_contains_env_path():
    cfg = BootstrapConfig(
        server="",
        database="",
        user="",
        password="",
        env_file=Path("G:/EM/.env"),
    )
    msg = format_incomplete_bootstrap_message(cfg)
    assert "G:\\EM\\.env" in msg or "G:/EM/.env" in msg
    assert "BOOTSTRAP_SERVER=SDAZ001MLD21" in msg
