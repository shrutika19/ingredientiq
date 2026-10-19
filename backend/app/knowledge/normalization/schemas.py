from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    UNRECOGNIZED = "unrecognized"
    AMBIGUOUS = "ambiguous"


class IngredientMatch(BaseModel):
    position: int
    original_name: str
    normalized_name: str

    status: ResolutionStatus

    ingredient_id: UUID | None = None
    canonical_name: str | None = None
    match_type: str | None = None

    candidate_names: list[str] = Field(
        default_factory=list
    )


class NormalizationResult(BaseModel):
    submission_id: UUID
    original_text: str
    ingredients: list[IngredientMatch]

    @property
    def resolved_count(self) -> int:
        return sum(
            item.status == ResolutionStatus.RESOLVED
            for item in self.ingredients
        )