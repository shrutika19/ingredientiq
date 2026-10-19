import logging
import random
import time
from collections.abc import Callable
from typing import TypeVar

import httpx
from google.genai.errors import ClientError, ServerError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class EmbeddingRetryExhausted(Exception):
    pass


def with_embedding_retry(
    operation: Callable[[], T],
    max_retries: int,
    base_delay: float,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    for attempt in range(max_retries + 1):
        try:
            return operation()

        except (ClientError, ServerError, httpx.TimeoutException) as exc:
            status = getattr(exc, "code", None)

            is_timeout = isinstance(exc, httpx.TimeoutException)
            is_retryable = is_timeout or status in {
                408, 429, 500, 502, 503, 504
            }

            if not is_retryable:
                raise

            if attempt == max_retries:
                raise EmbeddingRetryExhausted(
                    f"Embedding failed after {attempt + 1} attempts"
                ) from exc

            delay = min(
                base_delay * (2 ** attempt) + random.uniform(0, 0.5),
                30.0,
            )

            logger.warning(
                "Embedding retry %d/%d; status=%s; delay=%.2fs",
                attempt + 1,
                max_retries,
                status if status is not None else "timeout",
                delay,
            )

            sleep(delay)

    raise RuntimeError("Unexpected retry state")