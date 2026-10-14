
import logging

from google import genai
from google.genai import types

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class GeminiConfigurationError(Exception):
    """Gemini is not configured for this environment."""


def create_gemini_client() -> genai.Client:
    """Create a Gemini client using backend configuration."""
    settings = get_settings()

    if (
        settings.GEMINI_API_KEY is None
        or not settings.GEMINI_API_KEY.get_secret_value().strip()
    ):
        raise GeminiConfigurationError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=settings.GEMINI_API_KEY.get_secret_value(),
        http_options=types.HttpOptions(
            timeout=settings.GEMINI_TIMEOUT_SECONDS * 1000,
        ),
    )


def verify_gemini_connection() -> bool:
    """Run a minimal request to verify Gemini connectivity."""
    settings = get_settings()

    with create_gemini_client() as client:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Reply with only OK.",
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=20,
            ),
        )

    if not response.text or response.text.strip() != "OK":
        raise RuntimeError(
            "Gemini returned an unexpected verification response."
        )

    logger.info("Gemini connectivity verification succeeded")
    return True
