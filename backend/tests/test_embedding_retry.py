import pytest

from app.knowledge.embedding.retry import (
    EmbeddingRetryExhausted,
    with_embedding_retry,
)


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