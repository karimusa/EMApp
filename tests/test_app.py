"""Production-readiness tests — routes, permissions, and API contracts."""

import pytest

from app import create_app
from config.settings import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    return app.test_client()


def _login(client, username="admin", password="admin123"):
    return client.post("/login", data={"username": username, "password": password})


CONSOLE_PAGES = [
    ("/dashboard", b"Month-End Orchestration"),
    ("/run-history", b"Run History"),
    ("/agent-jobs", b"SQL Agent Jobs"),
    ("/logs", b"Execution Log"),
    ("/monitoring", b"Operations Monitoring"),
    ("/validation", b"Step Validation"),
    ("/reports", b"Coming Soon"),
    ("/settings", b"Settings"),
]

API_ENDPOINTS = [
    "/api/v1/dashboard",
    "/api/v1/run-history",
    "/api/v1/agent-jobs",
    "/api/v1/logs",
    "/api/v1/monitoring",
    "/api/v1/validation",
    "/api/v1/settings",
]


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
    def test_admin_login_redirects_to_dashboard(self, client):
        response = _login(client)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_viewer_can_access_console(self, client):
        _login(client, "viewer", "viewer123")
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert b"Read-only view" in response.data

    def test_post_login_redirects_to_dashboard(self, client):
        _login(client)
        response = client.get("/post-login", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_logout(self, client):
        _login(client)
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


class TestConsolePages:
    @pytest.mark.parametrize("path,needle", CONSOLE_PAGES)
    def test_requires_login(self, client, path, needle):
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    @pytest.mark.parametrize("path,needle", CONSOLE_PAGES)
    def test_admin_can_view(self, client, path, needle):
        _login(client)
        response = client.get(path)
        assert response.status_code == 200
        assert needle in response.data

    @pytest.mark.parametrize("path,needle", CONSOLE_PAGES)
    def test_readonly_can_view_non_admin_pages(self, client, path, needle):
        if path == "/admin/users":
            pytest.skip("Users is admin-only")
        _login(client, "viewer", "viewer123")
        response = client.get(path)
        assert response.status_code == 200
        assert needle in response.data


class TestAdminPermissions:
    def test_users_requires_admin(self, client):
        _login(client, "viewer", "viewer123")
        response = client.get("/admin/users", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_users_admin_access(self, client):
        _login(client)
        response = client.get("/admin/users")
        assert response.status_code == 200
        assert b"dbo.users" in response.data

    def test_readonly_nav_hides_users(self, client):
        _login(client, "viewer", "viewer123")
        response = client.get("/dashboard")
        assert b">Users</span>" not in response.data

    def test_admin_nav_shows_users(self, client):
        _login(client)
        response = client.get("/dashboard")
        assert b">Users</span>" in response.data

    def test_dashboard_renders_execution_controls(self, client):
        _login(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert b"window.rraDashboard" in response.data
        assert b"Stop Run" in response.data
        assert b"Run Sequence" in response.data
        assert b"dashboard-execution-2026-07-10" in response.data
        assert b"execution-status-bar" in response.data


class TestApi:
    def test_health(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.get_json()["status"] == "healthy"

    @pytest.mark.parametrize("path", API_ENDPOINTS)
    def test_api_requires_login(self, client, path):
        response = client.get(path)
        assert response.status_code == 302

    @pytest.mark.parametrize("path", API_ENDPOINTS)
    def test_api_returns_json(self, client, path):
        _login(client)
        response = client.get(path)
        assert response.status_code == 200
        assert response.is_json

    def test_users_api_admin_only(self, client):
        _login(client, "viewer", "viewer123")
        response = client.get("/api/v1/users")
        assert response.status_code == 403

    def test_dashboard_api_shape(self, client):
        _login(client)
        data = client.get("/api/v1/dashboard").get_json()
        assert "run" in data
        assert "metrics" in data
        assert "phases" in data
        assert "execution_log" in data


class TestNavigation:
    def test_no_broken_hash_links_in_nav(self, client):
        _login(client)
        response = client.get("/dashboard")
        html = response.data.decode()
        nav_start = html.find('aria-label="Main navigation"')
        nav_end = html.find("</nav>", nav_start)
        nav_html = html[nav_start:nav_end]
        assert 'href="#"' not in nav_html

    def test_reports_marked_coming_soon(self, client):
        _login(client)
        response = client.get("/reports")
        assert b"Coming Soon" in response.data
