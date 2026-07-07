"""Application tests."""

import pytest

from app import create_app
from app.db.connection_manager import init_connection_manager
from config.settings import TestingConfig


@pytest.fixture
def app():
    application = create_app(TestingConfig)
    with application.app_context():
        init_connection_manager(application)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


class TestAuth:
    def test_login_page_renders(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Sign In" in response.data

    def test_dashboard_requires_login(self, client):
        response = client.get("/dashboard")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_admin_login_success(self, client):
        response = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Orchestration Steps" in response.data

    def test_readonly_login_success(self, client):
        response = client.post(
            "/login",
            data={"username": "viewer", "password": "viewer123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Orchestration Steps" in response.data

    def test_readonly_cannot_see_admin_nav(self, client):
        client.post("/login", data={"username": "viewer", "password": "viewer123"})
        response = client.get("/dashboard")
        assert b"Administration" not in response.data

    def test_admin_can_see_admin_nav(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.get("/dashboard")
        assert b"Administration" in response.data


class TestDashboard:
    def test_dashboard_shows_phases(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.get("/dashboard")
        assert response.status_code == 200
        for phase in ("PRE", "MAIN", "BI", "DAY5", "POST"):
            assert phase.encode() in response.data

    def test_dashboard_shows_step_cards(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.get("/dashboard?phase=MAIN")
        assert b"GL Posting" in response.data


class TestAPI:
    def test_execute_requires_admin(self, client):
        client.post("/login", data={"username": "viewer", "password": "viewer123"})
        response = client.post("/api/steps/1/execute")
        assert response.status_code == 302

    def test_execute_step_admin(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.post("/api/steps/1/execute")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True

    def test_validate_step_admin(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.post("/api/steps/1/validate")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["result"]["pass_fail"] == "PASS"

    def test_logs_api(self, client):
        client.post("/login", data={"username": "viewer", "password": "viewer123"})
        response = client.get("/api/logs")
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)


class TestAdmin:
    def test_admin_users_requires_admin(self, client):
        client.post("/login", data={"username": "viewer", "password": "viewer123"})
        response = client.get("/admin/users")
        assert response.status_code == 302

    def test_admin_users_list(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.get("/admin/users")
        assert response.status_code == 200
        assert b"admin" in response.data


class TestJobs:
    def test_jobs_page(self, client):
        client.post("/login", data={"username": "viewer", "password": "viewer123"})
        response = client.get("/jobs")
        assert response.status_code == 200
        assert b"SPUS001BDBEXT" in response.data
        assert b"SPAZ001EDM10" in response.data
