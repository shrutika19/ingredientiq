
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from google.genai import errors

from app.services.skincare_analysis_service import (
    analyze_skincare_ingredients,
)
from app.services.gemini_exceptions import (
    GeminiAuthenticationError,
    GeminiInvalidResponseError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from app.schemas.analysis import GeminiAnalysisOutput


VALID_OUTPUT = {
    "overall_assessment": "low_concern",
    "summary": "Contains common moisturizing ingredients.",
    "ingredients": [
        {
            "name": "Glycerin",
            "function": "Humectant",
            "concern_level": "low",
            "explanation": "Helps retain moisture.",
        }
    ],
    "cautions": [],
    "uncertainties": [],
}


def make_client(*, response=None, error=None):
    client = MagicMock()
    client.__enter__.return_value = client

    if error is not None:
        client.models.generate_content.side_effect = error
    else:
        client.models.generate_content.return_value.text = (
            json.dumps(response)
        )

    return client


def run_with_client(client):
    with patch(
        "app.services.skincare_analysis_service.create_gemini_client",
        return_value=client,
    ):
        return analyze_skincare_ingredients("Glycerin")


def mock_gemini_response(payload):
    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value.text = (
        json.dumps(payload)
    )

    return client, client


def test_valid_gemini_analysis():
    manager, client = mock_gemini_response(VALID_OUTPUT)

    with patch(
        "app.services.skincare_analysis_service.create_gemini_client",
        return_value=manager,
    ):
        result = analyze_skincare_ingredients("Glycerin")

    assert result.ingredients[0].name == "Glycerin"
    assert result.overall_assessment == "low_concern"

    config = client.models.generate_content.call_args.kwargs[
        "config"
    ]
    assert config.system_instruction
    assert config.response_mime_type == "application/json"
    assert config.response_schema is None
    assert config.response_json_schema == (
        GeminiAnalysisOutput.model_json_schema()
    )


def test_missing_required_field():
    invalid = dict(VALID_OUTPUT)
    invalid.pop("summary")

    manager, _ = mock_gemini_response(invalid)

    with patch(
        "app.services.skincare_analysis_service.create_gemini_client",
        return_value=manager,
    ):
        with pytest.raises(GeminiInvalidResponseError):
            analyze_skincare_ingredients("Glycerin")


def test_invalid_concern_level():
    invalid = json.loads(json.dumps(VALID_OUTPUT))
    invalid["ingredients"][0]["concern_level"] = "very_safe"

    manager, _ = mock_gemini_response(invalid)

    with patch(
        "app.services.skincare_analysis_service.create_gemini_client",
        return_value=manager,
    ):
        with pytest.raises(GeminiInvalidResponseError):
            analyze_skincare_ingredients("Glycerin")


def test_empty_gemini_response():
    manager = MagicMock()
    manager.__enter__.return_value.models.generate_content.return_value.text = None

    with patch(
        "app.services.skincare_analysis_service.create_gemini_client",
        return_value=manager,
    ):
        with pytest.raises(GeminiInvalidResponseError):
            analyze_skincare_ingredients("Glycerin")


def test_successful_analysis():
    client = make_client(response=VALID_OUTPUT)

    result = run_with_client(client)

    assert result.ingredients[0].name == "Glycerin"
    assert result.overall_assessment == "low_concern"
    assert client.models.generate_content.call_count == 1


def test_invalid_model_response():
    invalid = dict(VALID_OUTPUT)
    invalid.pop("summary")

    client = make_client(response=invalid)

    with pytest.raises(GeminiInvalidResponseError):
        run_with_client(client)

    assert client.models.generate_content.call_count == 1


def test_authentication_failure():
    client = make_client(
        error=errors.ClientError(
            401,
            {"error": {"message": "Invalid API key"}},
        )
    )

    with pytest.raises(GeminiAuthenticationError):
        run_with_client(client)

    assert client.models.generate_content.call_count == 1


@patch(
    "app.services.skincare_analysis_service.time.sleep"
)
def test_rate_limit_retries(mock_sleep):
    client = make_client(
        error=errors.ClientError(
            429,
            {"error": {"message": "Rate limited"}},
        )
    )

    with pytest.raises(GeminiRateLimitError):
        run_with_client(client)

    assert client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


@patch(
    "app.services.skincare_analysis_service.time.sleep"
)
def test_timeout_retries(mock_sleep):
    request = httpx.Request(
        "POST",
        "https://generativelanguage.googleapis.com",
    )

    client = make_client(
        error=httpx.ReadTimeout(
            "Request timed out",
            request=request,
        )
    )

    with pytest.raises(GeminiTimeoutError):
        run_with_client(client)

    assert client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


@patch(
    "app.services.skincare_analysis_service.time.sleep"
)
def test_provider_unavailable(mock_sleep):
    client = make_client(
        error=errors.ServerError(
            503,
            {"error": {"message": "Unavailable"}},
        )
    )

    with pytest.raises(GeminiUnavailableError):
        run_with_client(client)

    assert client.models.generate_content.call_count == 3
    assert mock_sleep.call_count == 2


def test_invalid_input():
    with pytest.raises(ValueError):
        analyze_skincare_ingredients(" ")
