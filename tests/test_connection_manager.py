"""Tests for runtime connection password resolution."""

from __future__ import annotations

from app.db.connection_manager import (
    _matches_bootstrap_target,
    _resolve_sql_password,
)


def test_resolve_sql_password_plain_text():
    password = _resolve_sql_password("MonthEndApp", secret_key="")
    assert password == "MonthEndApp"


def test_resolve_sql_password_empty_uses_bootstrap_fallback():
    config = {
        "BOOTSTRAP_SERVER": "SDAZ001MLD21",
        "BOOTSTRAP_DATABASE": "MonthEndOrchestrationDB",
        "BOOTSTRAP_USER": "MonthEndApp",
        "BOOTSTRAP_PASSWORD": "MonthEndApp",
    }
    password = _resolve_sql_password(
        None,
        secret_key="",
        server_name="SDAZ001MLD21",
        database_name="MonthEndOrchestrationDB",
        sql_username="MonthEndApp",
        config=config,
    )
    assert password == "MonthEndApp"


def test_resolve_sql_password_empty_no_fallback_when_target_differs():
    config = {
        "BOOTSTRAP_SERVER": "SDAZ001MLD21",
        "BOOTSTRAP_DATABASE": "MonthEndOrchestrationDB",
        "BOOTSTRAP_USER": "MonthEndApp",
        "BOOTSTRAP_PASSWORD": "MonthEndApp",
    }
    password = _resolve_sql_password(
        "",
        secret_key="",
        server_name="OTHER-SERVER",
        database_name="MonthEndOrchestrationDB",
        sql_username="MonthEndApp",
        config=config,
    )
    assert password == ""


def test_matches_bootstrap_target_case_insensitive():
    config = {
        "BOOTSTRAP_SERVER": "sdaz001mld21",
        "BOOTSTRAP_DATABASE": "monthendorchestrationdb",
        "BOOTSTRAP_USER": "monthendapp",
    }
    assert _matches_bootstrap_target(
        "SDAZ001MLD21",
        "MonthEndOrchestrationDB",
        "MonthEndApp",
        config,
    )
