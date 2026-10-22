
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.knowledge.chunking import chunk_document
from app.knowledge.ingestion.normalizer import (
    content_hash,
    normalize_content,
)
from app.knowledge.ingestion.schemas import SeedDocument
from app.knowledge.sources import is_known_unverified_license
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

    if item.content is not None and not source.full_text_storage_allowed:
        raise IngestionRejected(
            "Source is not approved for content storage"
        )

    if (
        item.content is not None
        and is_known_unverified_license(source.license)
    ):
        raise IngestionRejected(
            "Source permission is not verified"
        )

    if item.license != source.license:
        raise IngestionRejected(
            "Document license differs from approved source license"
        )

    if item.content is None:
        if source.full_text_storage_allowed:
            raise IngestionRejected(
                "Content is required for sources approved for storage"
            )
        normalized = None
        prepared_chunks = []
        digest = None
    else:
        normalized = normalize_content(item.content)
        if not normalized:
            raise IngestionRejected("Empty normalized content")

        try:
            prepared_chunks = chunk_document(
                normalized,
                location_reference=item.location_reference,
            )
        except ValueError as exc:
            raise IngestionRejected(str(exc)) from exc

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
        if existing.content_hash != digest:
            raise IngestionRejected(
                "Existing source version has different content; "
                "assign a new source_version"
            )

        chunk_count = db.scalar(
            select(func.count(EvidenceChunk.id)).where(
                EvidenceChunk.document_id == existing.id
            )
        )

        if item.content is not None:
            if chunk_count != len(prepared_chunks):
                raise IngestionRejected(
                    "Existing document has incomplete chunks; "
                    "requires an approved backfill"
                )

        return IngestionResult(
            status="skipped",
            reason="Unchanged document version",
            document_id=existing.id,
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

    for chunk in prepared_chunks:
        db.add(
            EvidenceChunk(
                source_id=source.id,
                document_id=document.id,
                chunk_index=chunk.index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                location_reference=chunk.location_reference,
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
