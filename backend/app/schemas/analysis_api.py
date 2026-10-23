
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.analysis import GeminiAnalysisOutput
from app.schemas.error import ErrorResponse


class AnalysisApiStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnalysisEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID
    source_id: UUID
    source_identifier: str
    document_id: UUID
    document_version: str
    chunk_id: UUID
    ingredient_name: str
    excerpt: str
    content_hash: str = ""
    relevance_score: float = Field(default=0.0, ge=0, le=1)
    original_url: str
    document_title: str
    location_reference: str | None = None


class AnalysisApiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: UUID
    submission_id: UUID
    status: AnalysisApiStatus
    result: GeminiAnalysisOutput | None = None
    evidence_references: list[AnalysisEvidenceReference] = Field(
        default_factory=list
    )
    evidence_coverage: Literal[
        "full",
        "partial",
        "unavailable",
    ] = "unavailable"
    prompt_version: str | None = None
    retrieval_config: dict[str, Any] = Field(default_factory=dict)
    failure_code: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_status(self):
        if self.status == AnalysisApiStatus.COMPLETED:
            if self.result is None or self.completed_at is None:
                raise ValueError(
                    "Completed analysis requires result and timestamp."
                )

        return self


class AnalysisErrorResponse(ErrorResponse):
    pass
