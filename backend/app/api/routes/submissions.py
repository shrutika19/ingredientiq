
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.submission import (
    IngredientSubmissionRequest,
    IngredientSubmissionResponse,
)
from app.schemas.error import ErrorResponse
from app.services.submission_service import create_submission


router = APIRouter(
    prefix="/submissions",
    tags=["Ingredient Submissions"],
)


@router.post(
    "",
    response_model=IngredientSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {
            "model": ErrorResponse,
            "description": "Invalid ingredient submission payload",
        },
        503: {
            "model": ErrorResponse,
            "description": "Database temporarily unavailable",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error",
        },
    },
    summary="Submit skincare ingredients",
    description=(
        "Accepts raw skincare ingredient text, "
        "stores a submission in PostgreSQL, "
        "and returns a unique submission ID."
    ),
)
def submit_ingredients(
    payload: IngredientSubmissionRequest,
    db: Session = Depends(get_db),
) -> IngredientSubmissionResponse:

    submission = create_submission(
        db=db,
        ingredient_text=payload.ingredient_text,
    )

    return IngredientSubmissionResponse(
        submission_id=submission.id,
        status=submission.status,
        message="Ingredient submission received successfully.",
    )
