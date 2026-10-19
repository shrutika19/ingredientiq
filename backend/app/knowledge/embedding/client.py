
import math

from google import genai
from google.genai import types

from app.core.config import get_settings


class EmbeddingError(Exception):
    pass


class InvalidEmbeddingError(EmbeddingError):
    pass


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
