from uuid import UUID

from sqlalchemy.orm import Session

from app.knowledge.normalization.parser import (
    parse_ingredient_list,
)
from app.knowledge.normalization.resolver import resolve_name
from app.knowledge.normalization.schemas import (
    NormalizationResult,
)
from app.models.ingredient_submission import IngredientSubmission


class NormalizationSubmissionNotFound(Exception):
    pass


def normalize_submission(
    db: Session,
    submission_id: UUID,
) -> NormalizationResult:
    submission = db.get(
        IngredientSubmission,
        submission_id,
    )

    if submission is None:
        raise NormalizationSubmissionNotFound(
            f"Submission {submission_id} not found"
        )

    names = parse_ingredient_list(
        submission.original_text
    )

    matches = [
        resolve_name(
            db=db,
            name=name,
            position=index,
        )
        for index, name in enumerate(names)
    ]

    return NormalizationResult(
        submission_id=submission.id,
        original_text=submission.original_text,
        ingredients=matches,
    )