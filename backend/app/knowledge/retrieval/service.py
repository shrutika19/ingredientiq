import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from difflib import SequenceMatcher

from app.core.config import get_settings
from app.knowledge.embedding.client import GeminiEmbeddingClient
from app.knowledge.retrieval.schemas import (
    IngredientRetrievalResult,
    RetrievedEvidence,
)
from app.models.knowledge import (
    EvidenceChunk,
    EvidenceDocument,
    EvidenceDocumentIngredient,
    IngredientAlias,
    IngredientIdentity,
    KnowledgeSource,
)


def normalize_ingredient(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def resolve_ingredient(
    db: Session,
    normalized_name: str,
) -> IngredientIdentity | None:
    ingredient = db.scalar(
        select(IngredientIdentity).where(
            IngredientIdentity.normalized_name == normalized_name,
            IngredientIdentity.is_active.is_(True),
        )
    )

    if ingredient is not None:
        return ingredient

    return db.scalar(
        select(IngredientIdentity)
        .join(
            IngredientAlias,
            IngredientAlias.ingredient_id == IngredientIdentity.id,
        )
        .where(
            IngredientAlias.normalized_alias == normalized_name,
            IngredientIdentity.is_active.is_(True),
        )
        .order_by(IngredientIdentity.id)
        .limit(1)
    )


def retrieve_ingredient_evidence(
    db: Session,
    ingredient_name: str,
    embedding_client: GeminiEmbeddingClient | None = None,
    *,
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> IngredientRetrievalResult:
    settings = get_settings()

    if not isinstance(ingredient_name, str):
        raise ValueError("Ingredient name must be text")

    normalized = normalize_ingredient(ingredient_name)

    if not normalized or len(normalized) > 255:
        raise ValueError("Invalid ingredient name")

    k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
    threshold = (
        min_similarity
        if min_similarity is not None
        else settings.RETRIEVAL_MIN_SIMILARITY
    )

    if not 1 <= k <= 20:
        raise ValueError("top_k must be between 1 and 20")

    if not 0 <= threshold <= 1:
        raise ValueError("min_similarity must be between 0 and 1")

    ingredient = resolve_ingredient(db, normalized)

    if ingredient is None:
        return IngredientRetrievalResult(
            ingredient=ingredient_name,
            normalized_ingredient=normalized,
            status="unknown_ingredient",
            evidence=[],
        )

    # Avoid a Gemini request when no approved evidence exists.
    eligible_chunks = (
        select(EvidenceChunk.id)
        .join(
            EvidenceDocument,
            EvidenceChunk.document_id == EvidenceDocument.id,
        )
        .join(
            KnowledgeSource,
            EvidenceDocument.source_id == KnowledgeSource.id,
        )
        .join(
            EvidenceDocumentIngredient,
            EvidenceDocumentIngredient.document_id == EvidenceDocument.id,
        )
        .where(
            EvidenceDocumentIngredient.ingredient_id == ingredient.id,
            EvidenceChunk.is_active.is_(True),
            EvidenceDocument.is_active.is_(True),
            KnowledgeSource.is_active.is_(True),
            KnowledgeSource.full_text_storage_allowed.is_(True),
            KnowledgeSource.source_key != "TEST_SOURCE",
            KnowledgeSource.license != "TEST_ONLY",
            KnowledgeSource.license != "PERMISSION_REVIEW_REQUIRED",
            EvidenceChunk.embedding.is_not(None),
            EvidenceChunk.embedding_model == settings.EMBEDDING_MODEL,
        )
        .limit(1)
    )

    if db.scalar(eligible_chunks) is None:
        return IngredientRetrievalResult(
            ingredient=ingredient_name,
            normalized_ingredient=normalized,
            status="no_evidence",
            evidence=[],
        )

    if embedding_client is None:
        embedding_client = GeminiEmbeddingClient()

    query_vector = embedding_client.embed_query(
        f"Scientific cosmetic ingredient evidence about "
        f"{ingredient.canonical_name}: skin function, "
        f"benefits, limitations and safety."
    )

    distance = EvidenceChunk.embedding.cosine_distance(
        query_vector
    ).label("distance")

    candidate_limit = min(
        k * settings.RETRIEVAL_CANDIDATE_MULTIPLIER,
        200,
    )

    statement = (
        select(
            EvidenceChunk,
            EvidenceDocument,
            KnowledgeSource,
            distance,
        )
        .join(
            EvidenceDocument,
            EvidenceChunk.document_id == EvidenceDocument.id,
        )
        .join(
            KnowledgeSource,
            EvidenceDocument.source_id == KnowledgeSource.id,
        )
        .join(
            EvidenceDocumentIngredient,
            EvidenceDocumentIngredient.document_id == EvidenceDocument.id,
        )
        .where(
            EvidenceDocumentIngredient.ingredient_id == ingredient.id,
            EvidenceChunk.is_active.is_(True),
            EvidenceDocument.is_active.is_(True),
            KnowledgeSource.is_active.is_(True),
            KnowledgeSource.full_text_storage_allowed.is_(True),
            KnowledgeSource.source_key != "TEST_SOURCE",
            KnowledgeSource.license != "TEST_ONLY",
            KnowledgeSource.license != "PERMISSION_REVIEW_REQUIRED",
            EvidenceChunk.embedding.is_not(None),
            EvidenceChunk.embedding_model == settings.EMBEDDING_MODEL,
        )
        .order_by(distance, EvidenceChunk.id)
        .limit(candidate_limit)
    )

    rows = db.execute(statement).all()

    evidence = []
    accepted_claims: list[tuple[UUID, str]] = []

    for chunk, document, source, raw_distance in rows:
        if raw_distance is None:
            continue

        # Cosine distance typically ranges from 0 to 2.
        # Convert it into a bounded display score.
        similarity = max(
            0.0,
            min(1.0, 1.0 - float(raw_distance)),
        )

        if similarity < threshold:
            continue

        if is_near_duplicate(
            source.id,
            chunk.content,
            accepted_claims,
        ):
            continue

        accepted_claims.append(
            (source.id, normalize_claim(chunk.content))
        )

        evidence.append(
            RetrievedEvidence(
                chunk_id=chunk.id,
                source_id=source.id,
                source_key=source.source_key,
                document_id=document.id,
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.canonical_name,
                relevance_score=similarity,
                distance=float(raw_distance),
                excerpt=chunk.content,
                content_hash=chunk.content_hash,
                original_url=document.original_url,
                document_title=document.title,
                source_version=document.source_version,
                location_reference=chunk.location_reference,
            )
        )

        if len(evidence) >= k:
            break

    return IngredientRetrievalResult(
        ingredient=ingredient_name,
        normalized_ingredient=normalized,
        status="found" if evidence else "no_evidence",
        evidence=evidence,
    )


def normalize_claim(content: str) -> str:
    return re.sub(r"\s+", " ", content.strip()).casefold()


def is_near_duplicate(
    source_id: UUID,
    content: str,
    accepted: list[tuple[UUID, str]],
    threshold: float = 0.90,
) -> bool:
    normalized = normalize_claim(content)

    return any(
        existing_source == source_id
        and SequenceMatcher(
            None,
            normalized,
            existing_content,
        ).ratio() >= threshold
        for existing_source, existing_content in accepted
    )