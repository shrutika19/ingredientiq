from io import BytesIO
from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes import image_extraction
from app.main import app
from app.services.api_limits import enforce_image_extraction_limits
from app.services.gemini_client import GeminiConfigurationError


def make_png() -> bytes:
    image = Image.new("RGB", (200, 200), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def post_image(image_bytes: bytes, content_type: str = "image/png"):
    app.dependency_overrides[enforce_image_extraction_limits] = lambda: None
    try:
        with TestClient(app) as client:
            return client.post(
                "/api/v1/ingredients/extract-image",
                files={"file": ("label.png", image_bytes, content_type)},
            )
    finally:
        app.dependency_overrides.clear()


def test_rejects_oversized_image_before_provider_request(monkeypatch):
    extractor = MagicMock(side_effect=AssertionError("must not call provider"))
    monkeypatch.setattr(image_extraction, "extract_ingredient_text", extractor)

    response = post_image(b"x" * (image_extraction.MAX_FILE_SIZE + 1))

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_TOO_LARGE"
    extractor.assert_not_called()


def test_rejects_corrupted_image_before_provider_request(monkeypatch):
    extractor = MagicMock(side_effect=AssertionError("must not call provider"))
    monkeypatch.setattr(image_extraction, "extract_ingredient_text", extractor)

    response = post_image(b"not a valid image")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_IMAGE"
    extractor.assert_not_called()


def test_returns_successful_extraction(monkeypatch):
    extractor = MagicMock(return_value="Aqua, Glycerin, Niacinamide")
    monkeypatch.setattr(image_extraction, "extract_ingredient_text", extractor)
    image_bytes = make_png()

    response = post_image(image_bytes)

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "ingredient_text": "Aqua, Glycerin, Niacinamide",
        "extraction_status": "review_required",
        "warnings": [],
    }
    extractor.assert_called_once_with(image_bytes, "image/png")


def test_returns_unreadable_status_for_empty_provider_result(monkeypatch):
    monkeypatch.setattr(image_extraction, "extract_ingredient_text", lambda *_: "")

    response = post_image(make_png())

    assert response.status_code == 200
    assert response.json()["ingredient_text"] == ""
    assert response.json()["extraction_status"] == "unreadable"
    assert response.json()["warnings"]


def test_sanitizes_missing_provider_configuration(monkeypatch):
    def raise_configuration_error(*_args):
        raise GeminiConfigurationError("sensitive configuration detail")

    monkeypatch.setattr(
        image_extraction,
        "extract_ingredient_text",
        raise_configuration_error,
    )

    response = post_image(make_png())

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "VISION_UNAVAILABLE",
            "message": "Extraction unavailable.",
        }
    }
    assert "sensitive configuration detail" not in response.text


def test_sanitizes_provider_timeout(monkeypatch):
    def raise_timeout(*_args):
        raise httpx.ReadTimeout("sensitive provider response details")

    monkeypatch.setattr(
        image_extraction,
        "extract_ingredient_text",
        raise_timeout,
    )

    response = post_image(make_png())

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "VISION_TIMEOUT"
    assert "sensitive provider response details" not in response.text
