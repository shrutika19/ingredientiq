
import math
from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings


@lru_cache(maxsize=512)
def _cached_query_embedding(
    model: str,
    dimensions: int,
    query: str,
) -> tuple[float, ...]:
    client = GeminiEmbeddingClient()
    return tuple(client.embed_query(query))


class EmbeddingError(Exception):
    pass


class InvalidEmbeddingError(EmbeddingError):
    pass


def embed_cached_query(query: str) -> list[float]:
    if not isinstance(query, str) or not query.strip():
        raise InvalidEmbeddingError("Empty retrieval query")

    settings = get_settings()
    return list(
        _cached_query_embedding(
            settings.EMBEDDING_MODEL,
            settings.EMBEDDING_DIMENSIONS,
            query.strip(),
        )
    )


class GeminiEmbeddingClient:
    def __init__(self):
        self.settings = get_settings()

        if self.settings.GEMINI_API_KEY is None:
            raise EmbeddingError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(
            api_key=self.settings.GEMINI_API_KEY.get_secret_value(),
            http_options=types.HttpOptions(
                timeout=self.settings.EMBEDDING_TIMEOUT_SECONDS * 1000
            ),
        )

    def embed_document(
        self,
        content: str,
        title: str,
    ) -> list[float]:
        if not isinstance(content, str) or not content.strip():
            raise InvalidEmbeddingError("Empty embedding input")

        if not isinstance(title, str) or not title.strip():
            raise InvalidEmbeddingError("Empty embedding title")

        if len(content) > 4000:
            raise InvalidEmbeddingError(
                "Embedding input exceeds the safety limit"
            )

        response = self.client.models.embed_content(
            model=self.settings.EMBEDDING_MODEL,
            contents=content,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                title=title,
                output_dimensionality=(
                    self.settings.EMBEDDING_DIMENSIONS
                ),
            ),
        )

        embeddings = response.embeddings or []

        if len(embeddings) != 1 or embeddings[0].values is None:
            raise InvalidEmbeddingError(
                "Unexpected embedding response"
            )

        vector = list(embeddings[0].values)

        if len(vector) != self.settings.EMBEDDING_DIMENSIONS:
            raise InvalidEmbeddingError(
                f"Expected {self.settings.EMBEDDING_DIMENSIONS} "
                f"dimensions, received {len(vector)}"
            )

        if not all(math.isfinite(float(v)) for v in vector):
            raise InvalidEmbeddingError(
                "Embedding contains non-finite values"
            )

        if not any(float(v) != 0 for v in vector):
            raise InvalidEmbeddingError("Embedding is a zero vector")

        return [float(v) for v in vector]

    def embed_query(self, query: str) -> list[float]:
        if not isinstance(query, str) or not query.strip():
            raise InvalidEmbeddingError("Empty retrieval query")

        if len(query) > 1000:
            raise InvalidEmbeddingError("Retrieval query too long")

        response = self.client.models.embed_content(
            model=self.settings.EMBEDDING_MODEL,
            contents=query.strip(),
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=(
                    self.settings.EMBEDDING_DIMENSIONS
                ),
            ),
        )

        embeddings = response.embeddings or []

        if len(embeddings) != 1 or embeddings[0].values is None:
            raise InvalidEmbeddingError(
                "Unexpected query embedding response"
            )

        vector = [float(v) for v in embeddings[0].values]

        if len(vector) != self.settings.EMBEDDING_DIMENSIONS:
            raise InvalidEmbeddingError(
                "Unexpected query embedding dimensions"
            )

        if not all(math.isfinite(v) for v in vector):
            raise InvalidEmbeddingError(
                "Query embedding contains non-finite values"
            )

        if not any(v != 0 for v in vector):
            raise InvalidEmbeddingError(
                "Query embedding is a zero vector"
            )

        return vector
