
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.database.dependencies import get_db


client = TestClient(app)


def test_application_health():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_database_ready():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "database": "connected",
        }

        mock_db.execute.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_database_unavailable():
    mock_db = MagicMock()

    mock_db.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("Connection failed"),
    )

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 503
        assert response.json()["detail"]["status"] == "not_ready"

    finally:
        app.dependency_overrides.clear()
