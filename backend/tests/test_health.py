
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.database.dependencies import get_db
from app.api.routes import health


client = TestClient(app)


def test_application_health():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_database_ready(monkeypatch):
    mock_db = MagicMock()
    head_revision = "current-revision"
    mock_db.scalar.return_value = head_revision
    monkeypatch.setattr(
        health,
        "_migration_head_revision",
        lambda: head_revision,
    )

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "database": "connected",
            "migrations": "current",
        }

        mock_db.execute.assert_called_once()
        mock_db.scalar.assert_called_once()

    finally:
        app.dependency_overrides.clear()


def test_migrations_not_at_head(monkeypatch):
    mock_db = MagicMock()
    mock_db.scalar.return_value = "old-revision"
    monkeypatch.setattr(
        health,
        "_migration_head_revision",
        lambda: "head-revision",
    )

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 503
        assert response.json() == {
            "error": {
                "code": "MIGRATIONS_NOT_AT_HEAD",
                "message": "Database migrations are not up to date.",
            }
        }

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
        assert response.json()["error"]["code"] == (
            "DATABASE_UNAVAILABLE"
        )

    finally:
        app.dependency_overrides.clear()


def test_http_errors_use_standard_error_envelope():
    response = client.get("/api/v1/route-that-does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "HTTP_ERROR",
            "message": "Not Found",
        }
    }
