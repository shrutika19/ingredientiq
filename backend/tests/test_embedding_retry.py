from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.knowledge.embedding import client as embedding_client
from app.knowledge.embedding.retry import (
    EmbeddingRetryExhausted,
    with_embedding_retry,
)


def test_query_embeddings_are_cached_by_model_dimensions_and_text(
    monkeypatch,
):
    embedding_client._cached_query_embedding.cache_clear()
    settings = SimpleNamespace(
        EMBEDDING_MODEL="test-model",
        EMBEDDING_DIMENSIONS=3,
    )
    fake_client = MagicMock()
    fake_client.embed_query.return_value = [0.1, 0.2, 0.3]
    monkeypatch.setattr(
        embedding_client,
        "get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        embedding_client,
        "GeminiEmbeddingClient",
        lambda: fake_client,
    )

    try:
        first = embedding_client.embed_cached_query(" Glycerin ")
        second = embedding_client.embed_cached_query("Glycerin")

        assert first == second == [0.1, 0.2, 0.3]
        assert first is not second
        fake_client.embed_query.assert_called_once_with("Glycerin")
    finally:
        embedding_client._cached_query_embedding.cache_clear()


def test_timeout_then_success():
    import httpx

    calls = 0

    def operation():
        nonlocal calls
        calls += 1

        if calls == 1:
            raise httpx.ReadTimeout("Simulated timeout")

        return [0.1, 0.2]

    result = with_embedding_retry(
        operation,
        max_retries=3,
        base_delay=0.1,
        sleep=lambda _: None,
    )

    assert result == [0.1, 0.2]
    assert calls == 2


def test_timeout_exhaustion():
    import httpx

    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("Simulated timeout")

    with pytest.raises(EmbeddingRetryExhausted):
        with_embedding_retry(
            operation,
            max_retries=2,
            base_delay=0.1,
            sleep=lambda _: None,
        )

    assert calls == 3


def test_invalid_input_not_retried():
    calls = 0

    def operation():
        nonlocal calls
        calls += 1
        raise ValueError("Invalid content")

    with pytest.raises(ValueError):
        with_embedding_retry(
            operation,
            max_retries=3,
            base_delay=0.1,
            sleep=lambda _: None,
        )

    assert calls == 1