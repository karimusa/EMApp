"""Tests for Windows-safe .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from config.settings import (
    _apply_parsed_env,
    _parse_dotenv_text,
    build_runtime_config,
    load_env_file,
    should_use_mock_data,
)


def test_parse_dotenv_strips_quotes_and_comments():
    text = """
# comment
BOOTSTRAP_SERVER=SDAZ001MLD21
BOOTSTRAP_DATABASE="MonthEndOrchestrationDB"
DATA_SOURCE=auto
"""
    parsed = _parse_dotenv_text(text)
    assert parsed["BOOTSTRAP_SERVER"] == "SDAZ001MLD21"
    assert parsed["BOOTSTRAP_DATABASE"] == "MonthEndOrchestrationDB"
    assert parsed["DATA_SOURCE"] == "auto"


def test_apply_parsed_env_non_empty_wins_over_empty_process(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_SERVER", "")
    _apply_parsed_env({"BOOTSTRAP_SERVER": "SDAZ001MLD21"})
    assert os.environ["BOOTSTRAP_SERVER"] == "SDAZ001MLD21"


def test_apply_parsed_env_does_not_wipe_non_empty_process(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_SERVER", "SDAZ001MLD21")
    _apply_parsed_env({"BOOTSTRAP_SERVER": ""})
    assert os.environ["BOOTSTRAP_SERVER"] == "SDAZ001MLD21"


def test_load_env_file_utf16(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    content = "BOOTSTRAP_SERVER=SDAZ001MLD21\r\nBOOTSTRAP_DATABASE=MonthEndOrchestrationDB\r\n"
    env_file.write_text(content, encoding="utf-16")

    monkeypatch.setattr("config.settings.get_env_file_path", lambda: env_file)
    monkeypatch.delenv("BOOTSTRAP_SERVER", raising=False)
    monkeypatch.delenv("BOOTSTRAP_DATABASE", raising=False)

    load_env_file()
    assert os.environ["BOOTSTRAP_SERVER"] == "SDAZ001MLD21"
    assert os.environ["BOOTSTRAP_DATABASE"] == "MonthEndOrchestrationDB"


def test_build_runtime_config_enters_sql_mode(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATA_SOURCE=auto\nBOOTSTRAP_SERVER=SDAZ001MLD21\nBOOTSTRAP_DATABASE=MonthEndOrchestrationDB\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("config.settings.get_env_file_path", lambda: env_file)
    monkeypatch.delenv("BOOTSTRAP_SERVER", raising=False)

    config = build_runtime_config()
    assert config["BOOTSTRAP_SERVER"] == "SDAZ001MLD21"
    assert should_use_mock_data(config) is False
