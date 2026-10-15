"""Integration test for FastAPI application startup and health endpoint."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Coimbatore Institute of Technology" in data["campus"]
    assert data["status"] == "online"


def test_health_check_endpoint():
    """Verify health endpoint responds with database connection status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "thresholds" in data
    assert data["thresholds"]["warning"] == 0.25
    assert data["thresholds"]["critical"] == 0.50

