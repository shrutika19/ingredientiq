
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


ConcernLevel = Literal[
    "low",
    "moderate",
    "high",
    "unknown",
]

OverallAssessment = Literal[
    "low_concern",
    "moderate_concern",
    "high_concern",
    "insufficient_data",
]


class AnalyzedIngredient(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    name: str = Field(min_length=1)
    function: str = Field(min_length=1)
    concern_level: ConcernLevel
    explanation: str = Field(min_length=1)

    @field_validator(
        "name",
        "function",
        "explanation",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Ingredient text fields cannot be empty."
            )

        return value

    @model_validator(mode="after")
    def validate_unknown_ingredient(self):
        if self.function.casefold() == "unknown":
            if self.concern_level != "unknown":
                raise ValueError(
                    "Unknown ingredient function requires "
                    "concern_level='unknown'."
                )

        if self.concern_level == "unknown":
            explanation = self.explanation.casefold()

            uncertainty_terms = (
                "unknown",
                "uncertain",
                "insufficient",
                "not enough",
                "cannot determine",
                "cannot be established",
                "unable to determine",
                "unverified",
                "not established",
                "not documented",
                "no documented",
                "no established",
                "no widely documented",
                "no reliable",
                "no known",
                "no information",
                "limited information",
                "limited evidence",
                "limited data",
                "lack of evidence",
                "lack of information",
                "not well characterized",
                "not widely recognized",
                "not recognized",
                "unrecognized",
                "ambiguous",
                "unidentifiable",
                "cannot be identified",
            )

            if not any(
                term in explanation
                for term in uncertainty_terms
            ):
                raise ValueError(
                    "Unknown ingredients must explain "
                    "the uncertainty or insufficient evidence."
                )

        return self


class GeminiAnalysisOutput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    overall_assessment: OverallAssessment
    summary: str = Field(min_length=1)

    ingredients: list[AnalyzedIngredient] = Field(
        min_length=1
    )

    cautions: list[str]
    uncertainties: list[str]

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Analysis summary cannot be empty."
            )

        return value

    @field_validator(
        "cautions",
        "uncertainties",
    )
    @classmethod
    def validate_list_items(
        cls,
        values: list[str],
    ) -> list[str]:
        cleaned_values = []

        for value in values:
            cleaned = value.strip()

            if not cleaned:
                raise ValueError(
                    "Caution and uncertainty entries "
                    "cannot be empty."
                )

            cleaned_values.append(cleaned)

        return cleaned_values

    @model_validator(mode="after")
    def validate_analysis(self):
        ingredient_names = [
            ingredient.name.casefold()
            for ingredient in self.ingredients
        ]

        if len(ingredient_names) != len(
            set(ingredient_names)
        ):
            raise ValueError(
                "Duplicate ingredient names are not allowed."
            )

        all_unknown = all(
            ingredient.concern_level == "unknown"
            for ingredient in self.ingredients
        )

        if (
            all_unknown
            and self.overall_assessment
            != "insufficient_data"
        ):
            raise ValueError(
                "Overall assessment must be "
                "'insufficient_data' when all "
                "ingredients are unknown."
            )

        return self


class AnalysisResponse(GeminiAnalysisOutput):
    analysis_id: UUID
    submission_id: UUID
    status: Literal["completed"]
