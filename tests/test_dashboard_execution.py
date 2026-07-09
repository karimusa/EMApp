"""Tests for dashboard execution API."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app import create_app
from app.dashboard.errors import ExecutionError, LiveExecutionRequiredError
from app.dashboard.execution import ExecutionService
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
    @patch("app.dashboard.execution.use_mock_data", return_value=True)
    def test_start_run_blocked_in_mock_mode(self, _mock_live):
        service = ExecutionService()
        with pytest.raises(LiveExecutionRequiredError):
            service.start_run(actor="admin")

    @patch("app.dashboard.execution.use_mock_data", return_value=False)
    @patch.object(ExecutionService, "_active_run")
    def test_start_run_blocks_when_run_in_progress(self, mock_active, _mock_live):
        mock_active.return_value = {"run_id": 1, "status": "Running"}
        service = ExecutionService()
        with pytest.raises(ExecutionError, match="already in progress"):
            service.start_run(actor="admin")
