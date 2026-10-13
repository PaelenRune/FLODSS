"""Unit tests for FastAPI REST API endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root greeting / discovery endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["health"] == "/api/health"


def test_health_endpoint():
    """Verify GET /api/health returns 200 and system readiness payload."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Facility Layout" in data["project_name"]
    assert "version" in data
    assert "timestamp" in data
    assert "python_version" in data
    assert "modules" in data
    assert data["modules"]["core"] == "active"
    assert data["modules"]["models"] == "active"
    assert data["modules"]["algorithms"] == "ready"
    assert data["modules"]["evaluation"] == "ready"
