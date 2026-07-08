"""Dashboard service tests — post-login view models (mock mode)."""

from app import create_app
from app.dashboard.service import DashboardService
from config.settings import TestingConfig


def test_validation_includes_all_job_steps():
    app = create_app(TestingConfig)
    with app.app_context():
        svc = DashboardService()
        validation = svc.get_validation()
        steps = validation["rows"]
        assert len(steps) >= 1
        assert all("step_name" in row for row in steps)
        assert all("ValidationStatus" in row for row in steps)


def test_agent_jobs_groups_by_environment_name():
    app = create_app(TestingConfig)
    with app.app_context():
        svc = DashboardService()
        view = svc.get_agent_jobs()
        assert view["groups"]
        assert view["totals"]["total"] >= 1
        for group in view["groups"]:
            assert group["environment_name"]
            assert group["jobs"]


def test_settings_handles_active_connection_display():
    app = create_app(TestingConfig)
    with app.app_context():
        svc = DashboardService()
        settings = svc.get_settings()
        assert "connections" in settings
        assert settings["active_connection"]
