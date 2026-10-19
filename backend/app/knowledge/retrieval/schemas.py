from uuid import UUID

from pydantic import BaseModel, Field


class RetrievedEvidence(BaseModel):
    chunk_id: UUID
    source_id: UUID
    source_key: str
    document_id: UUID

    ingredient_id: UUID
    ingredient_name: str

    relevance_score: float = Field(ge=0, le=1)
    distance: float

    excerpt: str
    content_hash: str = ""
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    original_url: str
    document_title: str
    source_version: str
    location_reference: str | None = None


class IngredientRetrievalResult(BaseModel):
    ingredient: str
    normalized_ingredient: str

    status: str
    evidence: list[RetrievedEvidence] = Field(
        default_factory=list
    )