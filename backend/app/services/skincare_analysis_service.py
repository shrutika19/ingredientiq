
import logging
import random
import time

import httpx
from google.genai import errors, types
from pydantic import ValidationError

from app.core.config import get_settings
from app.prompts.skincare_v1 import (
    PROMPT_VERSION,
    SKINCARE_SYSTEM_PROMPT,
)
from app.schemas.analysis import GeminiAnalysisOutput
from app.services.gemini_client import (
    GeminiConfigurationError,
    create_gemini_client,
)
from app.services.gemini_exceptions import (
    GeminiAuthenticationError,
    GeminiInvalidResponseError,
    GeminiRateLimitError,
    GeminiServiceError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)


logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 4.0

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def _backoff_seconds(attempt: int) -> float:
    delay = min(
        BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
        MAX_DELAY_SECONDS,
    )
    return random.uniform(0, delay)


def _validate_input(ingredient_text: str) -> str:
    if not isinstance(ingredient_text, str):
        raise ValueError("Ingredient text must be a string.")

    value = ingredient_text.strip()

    if not 3 <= len(value) <= 10000:
        raise ValueError(
            "Ingredient text must contain 3 to 10000 characters."
        )

    return value


def _parse_response(response) -> GeminiAnalysisOutput:
    try:
        if not response.text:
            raise GeminiInvalidResponseError(
                "Gemini returned an empty response."
            )

        return GeminiAnalysisOutput.model_validate_json(
            response.text
        )

    except (ValidationError, ValueError, TypeError) as exc:
        raise GeminiInvalidResponseError(
            "Gemini returned an invalid analysis structure."
        ) from exc


def _map_provider_error(exc: Exception) -> GeminiServiceError:
    if isinstance(exc, errors.APIError):
        code = exc.code

        if code in (401, 403):
            return GeminiAuthenticationError(
                "Gemini authentication or access failed."
            )

        if code == 429:
            return GeminiRateLimitError(
                "Gemini request limit exceeded."
            )

        if code in RETRYABLE_STATUS_CODES:
            return GeminiUnavailableError(
                "Gemini provider is temporarily unavailable."
            )

        return GeminiServiceError(
            "Gemini provider rejected the request."
        )

    if isinstance(exc, httpx.TimeoutException):
        return GeminiTimeoutError(
            "Gemini request timed out."
        )

    if isinstance(exc, httpx.TransportError):
        return GeminiUnavailableError(
            "Gemini network connection failed."
        )

    return GeminiServiceError(
        "Gemini analysis failed unexpectedly."
    )


def analyze_skincare_ingredients(
    ingredient_text: str,
) -> GeminiAnalysisOutput:
    """Return a validated skincare analysis from Gemini."""

    validated_text = _validate_input(ingredient_text)
    settings = get_settings()

    try:
        client = create_gemini_client()
    except GeminiConfigurationError as exc:
        raise GeminiAuthenticationError(
            "Gemini credentials are not configured."
        ) from exc

    try:
        with client:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    logger.info(
                        "Gemini request: prompt=%s attempt=%d",
                        PROMPT_VERSION,
                        attempt,
                    )

                    response = client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_text(
                                        text=validated_text
                                    )
                                ],
                            )
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SKINCARE_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_json_schema=(
                                GeminiAnalysisOutput.model_json_schema()
                            ),
                            temperature=0,
                            max_output_tokens=4096,
                            http_options=types.HttpOptions(
                                retry_options=types.HttpRetryOptions(
                                    attempts=1,
                                )
                            ),
                        ),
                    )

                    result = _parse_response(response)

                    logger.info(
                        "Gemini analysis succeeded: prompt=%s",
                        PROMPT_VERSION,
                    )

                    return result

                except (
                    errors.APIError,
                    httpx.TransportError,
                ) as exc:
                    mapped_error = _map_provider_error(exc)

                    retryable = (
                        isinstance(
                            mapped_error,
                            (
                                GeminiRateLimitError,
                                GeminiTimeoutError,
                                GeminiUnavailableError,
                            ),
                        )
                    )

                    logger.warning(
                        "Gemini request failed: type=%s attempt=%d",
                        type(mapped_error).__name__,
                        attempt,
                    )

                    if not retryable or attempt == MAX_ATTEMPTS:
                        raise mapped_error from exc

                    time.sleep(_backoff_seconds(attempt))

    except GeminiServiceError:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected Gemini service failure"
        )
        raise GeminiServiceError(
            "Gemini analysis could not be completed."
        ) from exc
