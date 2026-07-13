"""Tests for user administration API and service rules."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app import create_app
from app.admin.errors import LiveDataRequiredError, UserAdminError
from app.auth.service import AuthService
from app.db.repositories.users import UserRepository
from config.settings import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    return app.test_client()


def _login(client, username="admin", password="admin123"):
    return client.post("/login", data={"username": username, "password": password})


class TestUsersPageWiring:
    def test_users_page_exposes_admin_config(self, client):
        _login(client)
        response = client.get("/admin/users")
        assert response.status_code == 200
        assert b"window.rraUserAdmin" in response.data
        assert b"liveDbAvailable" in response.data

    def test_users_actions_disabled_in_mock_mode(self, client):
        _login(client)
        response = client.get("/admin/users")
        html = response.data.decode()
        assert "disabled" in html
        assert "User management is read-only" in html


class TestUsersApiPermissions:
    def test_create_user_requires_admin(self, client):
        _login(client, "viewer", "viewer123")
        response = client.post(
            "/api/v1/users",
            json={"username": "newbie", "password": "secret12", "role": "ReadOnly"},
        )
        assert response.status_code == 403
        assert response.get_json()["reason"] == "permission_denied"

    @patch("app.routes.api.use_mock_data", return_value=True)
    def test_create_user_requires_live_connection(self, mock_live, client):
        _login(client)
        response = client.post(
            "/api/v1/users",
            json={"username": "newbie", "password": "secret12", "role": "ReadOnly"},
        )
        assert response.status_code == 503
        payload = response.get_json()
        assert payload["reason"] == "live_connection_unavailable"
        assert "MonthEndOrchestrationDB" in payload["error"]


class TestUsersApiMutations:
    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(AuthService, "create_user")
    def test_create_user_success(self, mock_create, _mock_live, client):
        mock_create.return_value = {
            "user_id": 9,
            "username": "newbie",
            "role": "ReadOnly",
            "is_active": True,
        }
        _login(client)
        response = client.post(
            "/api/v1/users",
            json={
                "username": "newbie",
                "password": "secret12",
                "role": "ReadOnly",
                "display_name": "New User",
                "email": "new@example.com",
            },
        )
        assert response.status_code == 201
        assert response.get_json()["user"]["username"] == "newbie"
        mock_create.assert_called_once()

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(AuthService, "update_user_profile")
    def test_update_user_success(self, mock_update, _mock_live, client):
        mock_update.return_value = {"user_id": 2, "username": "viewer"}
        _login(client)
        response = client.patch(
            "/api/v1/users/2",
            json={"display_name": "Viewer", "email": "viewer@example.com"},
        )
        assert response.status_code == 200
        mock_update.assert_called_once_with(
            2,
            display_name="Viewer",
            email="viewer@example.com",
            actor_user_id=1,
        )

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(AuthService, "change_user_role")
    def test_change_role_success(self, mock_role, _mock_live, client):
        mock_role.return_value = {"user_id": 2, "username": "viewer", "role": "Admin"}
        _login(client)
        response = client.post("/api/v1/users/2/role", json={"role": "Admin"})
        assert response.status_code == 200
        mock_role.assert_called_once_with(2, role="Admin", actor_user_id=1)

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(AuthService, "reset_user_password")
    def test_reset_password_success(self, mock_reset, _mock_live, client):
        _login(client)
        response = client.post(
            "/api/v1/users/2/password",
            json={"password": "newpass1"},
        )
        assert response.status_code == 200
        assert response.get_json()["ok"] is True
        mock_reset.assert_called_once_with(2, password="newpass1", actor_user_id=1)

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(AuthService, "set_user_active")
    def test_set_active_success(self, mock_active, _mock_live, client):
        mock_active.return_value = {"user_id": 4, "username": "areyes", "is_active": False}
        _login(client)
        response = client.post("/api/v1/users/4/active", json={"is_active": False})
        assert response.status_code == 200
        mock_active.assert_called_once_with(4, is_active=False, actor_user_id=1)

    @patch("app.routes.api.use_mock_data", return_value=False)
    @patch.object(AuthService, "change_user_role")
    def test_validation_error_maps_to_400(self, mock_role, _mock_live, client):
        mock_role.side_effect = UserAdminError("You cannot change your own role.")
        _login(client)
        response = client.post("/api/v1/users/1/role", json={"role": "ReadOnly"})
        assert response.status_code == 400
        payload = response.get_json()
        assert payload["reason"] == "validation_error"
        assert "own role" in payload["error"]


class TestAuthServiceUserAdmin:
    @patch("app.auth.service.use_mock_data", return_value=True)
    def test_create_user_raises_when_mock_mode(self, _mock_live):
        service = AuthService()
        with pytest.raises(LiveDataRequiredError):
            service.create_user(
                username="x",
                password="secret12",
                role="ReadOnly",
            )

    @patch("app.auth.service.use_mock_data", return_value=False)
    @patch.object(UserRepository, "get_by_username")
    def test_create_user_rejects_duplicate_username(self, mock_get, _mock_live):
        mock_get.return_value = {"user_id": 1, "username": "admin"}
        service = AuthService()
        with pytest.raises(UserAdminError, match="already exists"):
            service.create_user(
                username="admin",
                password="secret12",
                role="ReadOnly",
            )

    @patch("app.auth.service.use_mock_data", return_value=False)
    @patch.object(UserRepository, "get_by_id")
    def test_set_user_active_blocks_self_disable(self, mock_get, _mock_live):
        mock_get.return_value = {
            "user_id": 1,
            "username": "admin",
            "role": "Admin",
            "is_active": True,
        }
        service = AuthService()
        with pytest.raises(UserAdminError, match="own account"):
            service.set_user_active(1, is_active=False, actor_user_id=1)
