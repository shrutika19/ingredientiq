
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from app.core.config import get_settings
from app.services import gemini_client
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


def test_client_uses_configured_request_timeout(monkeypatch):
    settings = SimpleNamespace(
        GEMINI_API_KEY=SecretStr("test-key"),
        GEMINI_TIMEOUT_SECONDS=12,
    )
    monkeypatch.setattr(gemini_client, "get_settings", lambda: settings)
    fake_client = MagicMock()
    create_client = MagicMock(return_value=fake_client)
    monkeypatch.setattr(gemini_client.genai, "Client", create_client)

    result = create_gemini_client()

    assert result is fake_client
    options = create_client.call_args.kwargs["http_options"]
    assert options.timeout == 12_000
