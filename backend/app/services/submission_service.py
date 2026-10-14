
from sqlalchemy.orm import Session

from app.models.ingredient_submission import IngredientSubmission


def create_submission(
    db: Session,
    ingredient_text: str,
) -> IngredientSubmission:

    submission = IngredientSubmission(
        original_text=ingredient_text,
        status="pending",
    )

    try:
        db.add(submission)
        db.commit()
        db.refresh(submission)

        return submission

    except Exception:
        db.rollback()
        raise
