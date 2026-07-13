"""Tests for live dashboard step-run resolution fallbacks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app import create_app
from app.db.repositories.orchestration import OrchestrationRepository
from config.settings import DevelopmentConfig


JOB_STEPS = [
    {
        "step_id": 19,
        "job_id": 1,
        "step_name": "Area Manager Dashboard Load",
        "phase_code": "BI",
        "server_name": "SPUS001BDBEXT",
        "step_order": 19,
        "execute_proc_name": "usp_me_19_area_manager_dashboard_load",
        "validate_proc_name": "usp_validate_me_19_area_manager_dashboard_load",
        "is_enabled": True,
        "agent_job_name": None,
        "agent_job_key": None,
    }
]

EXECUTION_LOG_ROW = {
    "log_id": 501,
    "process_name": "usp_me_19_area_manager_dashboard_load",
    "database_name": "MonthEndOrchestrationDB",
    "step": "Area Manager Dashboard Load",
    "status": "Succeeded",
    "message": "Area Manager Dashboard load completed successfully",
    "log_time": "2026-07-02T15:33:04",
}


def test_execution_log_matches_step_by_name_and_proc():
    assert OrchestrationRepository._execution_log_matches_step(
        JOB_STEPS[0],
        log_step="Area Manager Dashboard Load",
        log_process="usp_me_19_area_manager_dashboard_load",
    )


@patch("app.db.repositories.orchestration.use_mock_data", return_value=False)
@patch("app.db.repositories.orchestration.query_primary")
def test_get_step_runs_falls_back_to_execution_log(mock_query, _mock_mode):
    repo = OrchestrationRepository()

    def query_side_effect(sql, params=()):
        text = " ".join(sql.split())
        if "FROM orchestration.job_steps" in text:
            return [
                {
                    "step_id": 19,
                    "job_id": 1,
                    "step_order": 19,
                    "step_name": "Area Manager Dashboard Load",
                    "parameters": None,
                    "is_active": True,
                    "step_type": "sql",
                    "command": "usp_me_19_area_manager_dashboard_load",
                    "server_name": "SPUS001BDBEXT",
                    "requires_approval": False,
                    "on_failure_action": "stop",
                    "retry_count": 0,
                    "retry_delay_sec": 0,
                    "execution_mode": "sync",
                    "phase_code": "BI",
                }
            ]
        if "FROM orchestration.job_runs" in text:
            return []
        if "FROM orchestration.step_runs" in text and "MAX(step_run_id)" in text:
            return []
        if "FROM orchestration.step_runs" in text and "WHERE run_id" in text:
            return []
        if "FROM orchestration.db_execution_log" in text:
            return [EXECUTION_LOG_ROW]
        return []

    mock_query.side_effect = query_side_effect

    runs = repo.get_step_runs()
    assert 19 in runs
    assert runs[19]["execution_status"] == "Success"
    assert runs[19]["validation_status"] == "Passed"
    assert runs[19]["data_source"] == "orchestration.db_execution_log"
    assert repo.last_step_run_source == "orchestration.db_execution_log"


@patch("app.db.repositories.base.get_connection_manager")
def test_use_mock_data_false_when_primary_ready(mock_get_manager):
    manager = MagicMock()
    manager.primary_ready.return_value = True
    mock_get_manager.return_value = manager

    app = create_app(DevelopmentConfig)
    app.config["DATA_SOURCE"] = "auto"
    app.config["BOOTSTRAP_SERVER"] = "SDAZ001MLD21"
    app.config["TESTING"] = False

    with app.app_context():
        from app.db.repositories.base import use_mock_data

        assert use_mock_data() is False


@patch("app.db.repositories.base.get_connection_manager")
def test_use_mock_data_true_when_primary_not_ready(mock_get_manager):
    manager = MagicMock()
    manager.primary_ready.return_value = False
    mock_get_manager.return_value = manager

    app = create_app(DevelopmentConfig)
    app.config["DATA_SOURCE"] = "auto"
    app.config["BOOTSTRAP_SERVER"] = "SDAZ001MLD21"
    app.config["TESTING"] = False

    with app.app_context():
        from app.db.repositories.base import use_mock_data

        assert use_mock_data() is True
