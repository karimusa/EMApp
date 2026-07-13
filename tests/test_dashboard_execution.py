"""Tests for dashboard execution API."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app import create_app
from app.dashboard.errors import ExecutionError, LiveExecutionRequiredError
from app.dashboard.execution import ExecutionService
from app.db.repositories.orchestration import OrchestrationRepository
from config.settings import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    return app.test_client()


def _login(client, username="admin", password="admin123"):
    return client.post("/login", data={"username": username, "password": password})


class TestDashboardExecutionApi:
    @patch("app.routes.api.use_mock_data", return_value=True)
    def test_start_run_requires_live_connection(self, _mock_live, client):
        _login(client)
        response = client.post("/api/v1/runs", json={})
        assert response.status_code == 503
        assert response.get_json()["reason"] == "live_connection_unavailable"

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(ExecutionService, "start_run")
    def test_start_run_success(self, mock_start, _mock_live, client):
        mock_start.return_value = {"run_id": 12, "status": "Running", "period_label": "July 2026"}
        _login(client)
        response = client.post("/api/v1/runs", json={})
        assert response.status_code == 201
        assert response.get_json()["run"]["run_id"] == 12

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(ExecutionService, "run_step")
    def test_run_step_success(self, mock_run, _mock_live, client):
        mock_run.return_value = {
            "run_id": 12,
            "step_id": 3,
            "execution_status": "Success",
            "message": "ok",
        }
        _login(client)
        response = client.post("/api/v1/steps/3/run", json={"run_id": 12})
        assert response.status_code == 200
        mock_run.assert_called_once()

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(ExecutionService, "stop_run")
    def test_stop_run_success(self, mock_stop, _mock_live, client):
        mock_stop.return_value = {"run_id": 12, "status": "Stopped", "stopped_by": "admin"}
        _login(client)
        response = client.post("/api/v1/runs/12/stop", json={})
        assert response.status_code == 200
        assert response.get_json()["run"]["status"] == "Stopped"

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(ExecutionService, "run_sequence")
    def test_run_sequence_success(self, mock_sequence, _mock_live, client):
        mock_sequence.return_value = {"run_id": 12, "executed_count": 2, "completed": True, "executed": []}
        _login(client)
        response = client.post("/api/v1/runs/sequence", json={"run_id": 12})
        assert response.status_code == 200
        assert response.get_json()["sequence"]["completed"] is True

    def test_execution_requires_admin(self, client):
        _login(client, "viewer", "viewer123")
        response = client.post("/api/v1/runs", json={})
        assert response.status_code == 403


class TestExecutionServiceRules:
    @patch("app.dashboard.execution.get_execution_runtime")
    def test_start_run_blocked_in_mock_mode(self, mock_runtime):
        mock_runtime.return_value = {
            "execution_block_reason": "Live SQL connection unavailable.",
            "execution_enabled": False,
        }
        service = ExecutionService()
        with pytest.raises(LiveExecutionRequiredError):
            service.start_run(actor="admin")

    @patch("app.dashboard.execution.get_execution_runtime")
    @patch("app.dashboard.execution.execution_enabled", return_value=True)
    @patch.object(ExecutionService, "_blocking_run_for_start")
    @patch.object(ExecutionService, "_active_run")
    def test_start_run_blocks_when_run_in_progress(
        self, mock_active, mock_blocking, _mock_enabled, mock_runtime
    ):
        mock_runtime.return_value = {"execution_block_reason": None, "execution_enabled": True}
        mock_blocking.return_value = {"run_id": 1, "status": "In Progress"}
        mock_active.return_value = {"run_id": 1, "status": "In Progress"}
        service = ExecutionService()
        with pytest.raises(ExecutionError, match="already in progress"):
            service.start_run(actor="admin")

    @patch("app.dashboard.execution.get_execution_runtime")
    @patch("app.dashboard.execution.execution_enabled", return_value=True)
    @patch.object(ExecutionService, "_active_run", return_value=None)
    @patch.object(ExecutionService, "_get_jobs")
    @patch.object(OrchestrationRepository, "create_job_run", return_value=99)
    @patch.object(OrchestrationRepository, "get_current_run_id", return_value=None)
    @patch.object(OrchestrationRepository, "get_step_by_id")
    @patch.object(OrchestrationRepository, "execute_step_procedure")
    def test_run_step_auto_starts_run_when_none_active(
        self,
        mock_execute,
        mock_get_step,
        _mock_current_run,
        _mock_create_run,
        mock_get_jobs,
        _mock_active,
        _mock_enabled,
        mock_runtime,
    ):
        mock_runtime.return_value = {"execution_block_reason": None, "execution_enabled": True}
        mock_get_jobs.return_value = [{"job_id": 1}]
        mock_get_step.return_value = {"step_id": 3, "step_name": "Send Start Email", "is_enabled": True}
        mock_execute.return_value = {"execution_status": "Success", "message": "ok"}

        service = ExecutionService()
        result = service.run_step(3, run_id=None, actor="admin")

        assert result["run_id"] == 99
        _mock_create_run.assert_called_once()
        mock_execute.assert_called_once()
