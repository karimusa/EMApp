"""Data layer tests — mock/SQL facade and repository contracts."""

from app import create_app
from app.dashboard import data
from app.db.repositories.base import use_mock_data
from config.settings import TestingConfig


def test_use_mock_data_in_testing():
    app = create_app(TestingConfig)
    with app.app_context():
        assert use_mock_data() is True
        assert data.data_source_label() == "mock"


def test_mock_job_steps_shape():
    app = create_app(TestingConfig)
    with app.app_context():
        steps = data.get_job_steps()
        assert len(steps) >= 1
        step = steps[0]
        assert "step_id" in step
        assert "phase_code" in step
        assert "execute_proc_name" in step


def test_mock_dashboard_contract():
    app = create_app(TestingConfig)
    with app.app_context():
        metrics = data.get_run_metrics()
        assert "progress_pct" in metrics
        assert "total_steps" in metrics
        runs = data.get_job_runs()
        assert runs[0]["period_label"]


def test_mock_validation_contract():
    app = create_app(TestingConfig)
    with app.app_context():
        results = data.get_validation_results()
        first = next(iter(results.values()))
        assert first["ValidationStatus"] in ("PASS", "FAIL", "PENDING")
