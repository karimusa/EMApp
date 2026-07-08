"""Tests for PRIMARY readiness gating."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from config.settings import TestingConfig


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    return app.test_client()


def test_login_blocks_when_primary_not_ready(client):
    message = (
        "PRIMARY: orchestration.app_connections stores a one-way hash "
        "(6A1E8FF1…), which cannot be used for SQL Server authentication."
    )
    manager = MagicMock()
    manager.get_primary_error.return_value = message
    manager.reload.return_value = None

    with patch("app.routes.auth.use_mock_data", return_value=False), patch(
        "app.routes.auth.get_connection_manager", return_value=manager
    ):
        response = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
        )

    assert response.status_code == 200
    assert message.encode() in response.data
