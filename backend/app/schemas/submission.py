
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IngredientSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingredient_text: str = Field(
        ...,
        description="Raw skincare ingredient list",
        examples=[
            "Aqua, Glycerin, Niacinamide"
        ],
    )

    @field_validator("ingredient_text")
    @classmethod
    def validate_ingredient_text(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError(
                "Ingredient text must contain at least 3 characters."
            )

        if len(value) > 10000:
            raise ValueError(
                "Ingredient text must not exceed 10000 characters."
            )

        return value


class IngredientSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    submission_id: UUID
    status: str
    message: str
