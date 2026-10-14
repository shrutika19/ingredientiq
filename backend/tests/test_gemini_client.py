
import pytest

from app.core.config import get_settings
from app.services.gemini_client import (
    GeminiConfigurationError,
    create_gemini_client,
)


def test_missing_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "")

    get_settings.cache_clear()

    try:
        with pytest.raises(GeminiConfigurationError):
            create_gemini_client()
    finally:
        get_settings.cache_clear()
