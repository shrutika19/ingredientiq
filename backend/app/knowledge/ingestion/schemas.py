
from datetime import date
from typing import Annotated

from pydantic import (
    BaseModel, ConfigDict, Field, HttpUrl,
    StringConstraints, model_validator,
)

NonEmpty = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1)
]


class SeedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: NonEmpty
    title: NonEmpty
    original_url: HttpUrl
    source_version: NonEmpty
    publication_date: date | None = None
    retrieved_date: date
    license: NonEmpty
    evidence_type: NonEmpty
    content: NonEmpty | None = None
    location_reference: str | None = None
    ingredient_names: list[NonEmpty] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.publication_date is not None
            and self.publication_date > self.retrieved_date
        ):
            raise ValueError(
                "Publication date cannot exceed retrieval date"
            )

        placeholder_markers = (
            "replace with",
            "verified_license_or_permission_id",
            "verified document title",
            "verified section or page",
            "example.org/replace-with",
        )
        candidate_fields = {
            "title": self.title,
            "original_url": str(self.original_url),
            "source_version": self.source_version,
            "license": self.license,
            "content": self.content or "",
            "location_reference": self.location_reference or "",
        }
        placeholder_fields = [
            field
            for field, value in candidate_fields.items()
            if any(marker in value.casefold() for marker in placeholder_markers)
        ]
        if placeholder_fields:
            raise ValueError(
                "Dataset contains unresolved placeholder values in: "
                + ", ".join(placeholder_fields)
            )

        return self
