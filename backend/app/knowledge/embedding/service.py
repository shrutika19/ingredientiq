
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import (
    EvidenceChunk,
    EvidenceDocument,
    KnowledgeSource,
)
from app.knowledge.embedding.client import (
    GeminiEmbeddingClient,
)
from app.core.config import get_settings


@dataclass
class EmbeddingResult:
    status: str
    reason: str
    chunk_id: UUID


def process_chunk(
    db: Session,
    chunk_id: UUID,
    client: GeminiEmbeddingClient,
    *,
    allow_test_source: bool = False,
) -> EmbeddingResult:
    settings = get_settings()

    row = db.execute(
        select(
            EvidenceChunk,
            EvidenceDocument,
            KnowledgeSource,
        )
        .join(
            EvidenceDocument,
            EvidenceChunk.document_id == EvidenceDocument.id,
        )
        .join(
            KnowledgeSource,
            EvidenceDocument.source_id == KnowledgeSource.id,
        )
        .where(EvidenceChunk.id == chunk_id)
    ).one_or_none()

    if row is None:
        raise ValueError("Chunk or its source was not found")

    chunk, document, source = row

    if not (
        chunk.is_active
        and document.is_active
        and source.is_active
    ):
        raise ValueError("Inactive evidence cannot be embedded")

    if not source.full_text_storage_allowed:
        raise ValueError("Source lacks approved content storage permission")

    if source.source_key == "TEST_SOURCE":
        if not(
            allow_test_source
            and settings.APP_ENV  in ("development", "testing")
        ):
            raise ValueError(
                "Synthetic test evidence is excluded from real indexing"
            )
    elif source.license == "PERMISSION_REVIEW_REQUIRED":
        raise ValueError(
            "Source permission is not verified"
        )
    

    if (
        chunk.embedding is not None
        and chunk.embedding_model == settings.EMBEDDING_MODEL
    ):
        return EmbeddingResult(
            "skipped",
            "Existing embedding matches configured model",
            chunk.id,
        )

    vector = client.embed_document(
        content=chunk.content,
        title=document.title,
    )

    chunk.embedding = vector
    chunk.embedding_model = settings.EMBEDDING_MODEL

    db.flush()

    return EmbeddingResult(
        "embedded",
        "Vector generated and stored",
        chunk.id,
    )
