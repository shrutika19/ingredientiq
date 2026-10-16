
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.ingestion.normalizer import (
    content_hash,
    normalize_content,
)
from app.knowledge.ingestion.schemas import SeedDocument
from app.models.knowledge import (
    KnowledgeSource,
    IngredientIdentity,
    EvidenceDocument,
    EvidenceDocumentIngredient,
    EvidenceChunk,
)


class IngestionRejected(Exception):
    pass


@dataclass
class IngestionResult:
    status: str
    reason: str
    document_id: UUID | None = None


def ingest_document(
    db: Session,
    item: SeedDocument,
) -> IngestionResult:
    source = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.source_key == item.source_key
        )
    )

    if source is None or not source.is_active:
        raise IngestionRejected(
            f"Unknown or inactive source: {item.source_key}"
        )

    if not source.full_text_storage_allowed:
        raise IngestionRejected(
            "Source is not approved for content storage"
        )

    if item.license != source.license:
        raise IngestionRejected(
            "Document license differs from approved source license"
        )

    normalized = normalize_content(item.content)
    if not normalized:
        raise IngestionRejected("Empty normalized content")

    if len(normalized) > 5000:
        raise IngestionRejected(
            "Content exceeds the MVP single-chunk limit"
        )

    digest = content_hash(normalized)
    url = str(item.original_url)

    existing = db.scalar(
        select(EvidenceDocument).where(
            EvidenceDocument.source_id == source.id,
            EvidenceDocument.original_url == url,
            EvidenceDocument.source_version == item.source_version,
        )
    )

    if existing is not None:
        if existing.content_hash == digest:
            return IngestionResult(
                status="skipped",
                reason="Unchanged document version",
                document_id=existing.id,
            )
        raise IngestionRejected(
            "Existing source version has different content; "
            "assign a new source_version"
        )

    # Validate all identities before making changes.
    normalized_names = {
        name.strip().casefold()
        for name in item.ingredient_names
    }

    ingredients = db.scalars(
        select(IngredientIdentity).where(
            IngredientIdentity.normalized_name.in_(
                normalized_names
            ),
            IngredientIdentity.is_active.is_(True),
        )
    ).all()

    found_names = {
        ingredient.normalized_name
        for ingredient in ingredients
    }

    missing = normalized_names - found_names
    if missing:
        raise IngestionRejected(
            f"Unknown ingredient identities: {sorted(missing)}"
        )

    # Retain historical versions instead of deleting them.
    previous_versions = db.scalars(
        select(EvidenceDocument).where(
            EvidenceDocument.source_id == source.id,
            EvidenceDocument.original_url == url,
            EvidenceDocument.is_active.is_(True),
        )
    ).all()

    for previous in previous_versions:
        previous.is_active = False

    document = EvidenceDocument(
        source_id=source.id,
        title=item.title,
        original_url=url,
        source_version=item.source_version,
        publication_date=item.publication_date,
        retrieved_date=item.retrieved_date,
        content_hash=digest,
        license=item.license,
        evidence_type=item.evidence_type,
        is_active=True,
    )
    db.add(document)
    db.flush()

    for ingredient in ingredients:
        db.add(
            EvidenceDocumentIngredient(
                document_id=document.id,
                ingredient_id=ingredient.id,
            )
        )

    db.add(
        EvidenceChunk(
            source_id=source.id,
            document_id=document.id,
            chunk_index=0,
            content=normalized,
            content_hash=digest,
            location_reference=item.location_reference,
            embedding=None,
            embedding_model=None,
            is_active=True,
        )
    )

    db.flush()

    return IngestionResult(
        status="ingested",
        reason="New document version stored",
        document_id=document.id,
    )
