import json
import logging
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.logging_config import JsonLogFormatter
from app.main import app


def test_requests_return_and_log_structured_request_id(caplog) -> None:
    request_id = "2a51f770-992b-4f46-94e6-1a2a4177d0bd"
    formatter = JsonLogFormatter()

    with TestClient(app) as client, caplog.at_level(
        logging.INFO,
        logger="app.core.request_logging",
    ):
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": request_id},
        )

    assert response.headers["x-request-id"] == request_id
    request_record = next(
        record
        for record in caplog.records
        if record.getMessage() == "http_request_completed"
    )
    payload = json.loads(formatter.format(request_record))

    assert request_record.name == "app.core.request_logging"
    assert payload["request_id"] == request_id
    assert payload["http_method"] == "GET"
    assert payload["http_path"] == "/api/v1/health"
    assert payload["http_status_code"] == 200
    assert isinstance(payload["duration_ms"], float)


def test_invalid_request_id_is_replaced_with_generated_uuid() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "not-a-uuid\r\nforged-log"},
        )

    generated_id = response.headers["x-request-id"]
    assert str(UUID(generated_id)) == generated_id
