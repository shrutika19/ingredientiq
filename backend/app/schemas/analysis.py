
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

EvidenceStatus = Literal[
    "source_grounded",
    "limited",
]

FindingSupport = Literal[
    "supported",
    "limited",
    "conflicting",
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
    support_status: FindingSupport = "limited"
    evidence_ids: list[str] = Field(default_factory=list)

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

    @field_validator("evidence_ids")
    @classmethod
    def validate_evidence_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Evidence identifiers cannot be empty.")

        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate evidence identifiers are not allowed.")

        return cleaned

    @model_validator(mode="after")
    def validate_unknown_ingredient(self):
        if self.support_status == "supported" and not self.evidence_ids:
            raise ValueError(
                "Supported findings require evidence identifiers."
            )

        if self.support_status == "conflicting" and len(self.evidence_ids) < 2:
            raise ValueError(
                "Conflicting findings require at least two evidence identifiers."
            )

        if self.support_status == "limited" and self.evidence_ids:
            raise ValueError(
                "Limited findings cannot cite supporting evidence."
            )

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
    evidence_status: EvidenceStatus = "limited"
    evidence_ids: list[str] = Field(default_factory=list)
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
        if self.evidence_status == "source_grounded" and not self.evidence_ids:
            raise ValueError(
                "Source-grounded summaries require evidence identifiers."
            )

        if self.evidence_status == "limited" and self.evidence_ids:
            raise ValueError(
                "Limited summaries cannot cite supporting evidence."
            )

        if self.evidence_status == "limited" and any(
            ingredient.support_status != "limited"
            for ingredient in self.ingredients
        ):
            raise ValueError(
                "Limited analyses cannot contain supported or conflicting "
                "ingredient findings."
            )

        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Duplicate summary evidence identifiers are not allowed.")

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
