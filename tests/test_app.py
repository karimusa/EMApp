"""Step 1 — login page tests."""

import pytest

from app import create_app
from config.settings import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    return app.test_client()


class TestLoginPage:
    def test_root_redirects_to_login(self, client):
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_login_page_renders(self, client):
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Sign In" in response.data
        assert b"RRA Month-End Orchestration" in response.data

    def test_login_page_has_form_fields(self, client):
        response = client.get("/login")
        assert b'name="username"' in response.data
        assert b'name="password"' in response.data

    def test_empty_login_shows_error(self, client):
        response = client.post("/login", data={"username": "", "password": ""})
        assert response.status_code == 200
        assert b"Username and password are required" in response.data

    def test_invalid_credentials(self, client):
        response = client.post(
            "/login", data={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 200
        assert b"Invalid username or password" in response.data


class TestLoginFlow:
    def test_admin_login_success(self, client):
        response = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_viewer_login_success(self, client):
        response = client.post(
            "/login",
            data={"username": "viewer", "password": "viewer123"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Month-End Orchestration" in response.data

    def test_post_login_requires_session(self, client):
        response = client.get("/post-login")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_logout(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestConsolePages:
    def _login_admin(self, client):
        client.post("/login", data={"username": "admin", "password": "admin123"})

    def test_dashboard_requires_login(self, client):
        assert client.get("/dashboard").status_code == 302

    def test_dashboard_renders(self, client):
        self._login_admin(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert b"Month-End Orchestration" in response.data

    def test_logs_page_renders(self, client):
        self._login_admin(client)
        response = client.get("/logs")
        assert response.status_code == 200
        assert b"Logs" in response.data

    def test_agent_jobs_renders(self, client):
        self._login_admin(client)
        response = client.get("/agent-jobs")
        assert response.status_code == 200
        assert b"SQL Agent Jobs" in response.data
