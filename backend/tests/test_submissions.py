
from uuid import uuid4
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.database.dependencies import get_db
from app.api.routes import submissions


def fake_db():
    db = MagicMock()
    db.execute.return_value.one.return_value = (1, 0, 1, 0)
    yield db


def test_submit_ingredients(monkeypatch):
    fake_submission = MagicMock()
    fake_submission.id = uuid4()
    fake_submission.status = "pending"

    monkeypatch.setattr(
        submissions,
        "create_submission",
        lambda db, ingredient_text: fake_submission,
    )

    app.dependency_overrides[get_db] = fake_db

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                "/api/v1/submissions",
                json={
                    "ingredient_text": "Aqua, Glycerin"
                },
            )

        assert response.status_code == 201
        assert response.json()["status"] == "pending"
        assert response.json()["submission_id"] == str(
            fake_submission.id
        )

    finally:
        app.dependency_overrides.clear()


def test_invalid_ingredient_text():
    app.dependency_overrides[get_db] = fake_db

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                "/api/v1/submissions",
                json={"ingredient_text": "   "},
            )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    finally:
        app.dependency_overrides.clear()


def test_database_failure(monkeypatch):
    def raise_database_error(db, ingredient_text):
        raise OperationalError(
            "INSERT",
            {},
            Exception("Connection failed"),
        )

    monkeypatch.setattr(
        submissions,
        "create_submission",
        raise_database_error,
    )

    app.dependency_overrides[get_db] = fake_db

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                "/api/v1/submissions",
                json={"ingredient_text": "Aqua, Glycerin"},
            )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == (
            "DATABASE_UNAVAILABLE"
        )

    finally:
        app.dependency_overrides.clear()


def test_openapi_documentation():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    assert "/api/v1/submissions" in schema["paths"]
    assert "post" in schema["paths"]["/api/v1/submissions"]

    components = schema["components"]["schemas"]
    assert "IngredientSubmissionRequest" in components
    assert "IngredientSubmissionResponse" in components
    assert "ErrorResponse" in components
