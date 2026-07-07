"""Application tests."""

import pytest

from app import create_app
from config.settings import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    application = create_app(TestingConfig)
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_index_returns_200(client):
    """Home page should return 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"EMApp" in response.data


def test_health_endpoint(client):
    """Health endpoint should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["app"] == "EMApp"
