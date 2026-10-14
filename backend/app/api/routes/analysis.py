
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.ingredient_analysis import IngredientAnalysis
from app.schemas.analysis_api import (
    AnalysisApiResponse,
    AnalysisErrorResponse,
)
from app.schemas.analysis import GeminiAnalysisOutput
from app.services.analysis_workflow_service import (
    AnalysisAlreadyRunning,
    AnalysisExecutionFailed,
    SubmissionNotFound,
    get_latest_analysis,
    start_analysis,
)


router = APIRouter(
    prefix="/submissions",
    tags=["Ingredient Analysis"],
)


def to_api_response(
    analysis: IngredientAnalysis,
) -> AnalysisApiResponse:
    result = None

    if analysis.result is not None:
        result = GeminiAnalysisOutput.model_validate(
            analysis.result
        )

    return AnalysisApiResponse(
        analysis_id=analysis.id,
        submission_id=analysis.submission_id,
        status=analysis.status.value,
        result=result,
        failure_code=analysis.failure_code,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


@router.post(
    "/{id}/analyze",
    response_model=AnalysisApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"model": AnalysisErrorResponse},
        409: {"model": AnalysisErrorResponse},
        429: {"model": AnalysisErrorResponse},
        502: {"model": AnalysisErrorResponse},
        503: {"model": AnalysisErrorResponse},
        504: {"model": AnalysisErrorResponse},
    },
)
def analyze_submission(
    id: UUID,
    db: Session = Depends(get_db),
):
    try:
        analysis = start_analysis(
            db=db,
            submission_id=id,
        )

        return to_api_response(analysis)

    except SubmissionNotFound:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SUBMISSION_NOT_FOUND",
                "message": "Ingredient submission not found.",
            },
        )

    except AnalysisAlreadyRunning:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "ANALYSIS_IN_PROGRESS",
                "message": "Analysis is already in progress.",
            },
        )

    except AnalysisExecutionFailed as exc:
        raise HTTPException(
            status_code=exc.http_status,
            detail={
                "error": exc.code,
                "message": "Ingredient analysis could not be completed.",
            },
        )


@router.get(
    "/{id}/analysis",
    response_model=AnalysisApiResponse,
    responses={
        404: {"model": AnalysisErrorResponse},
    },
)
def retrieve_analysis(
    id: UUID,
    db: Session = Depends(get_db),
):
    try:
        analysis = get_latest_analysis(
            db=db,
            submission_id=id,
        )

        if analysis is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "ANALYSIS_NOT_FOUND",
                    "message": "No analysis exists for this submission.",
                },
            )

        return to_api_response(analysis)

    except SubmissionNotFound:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "SUBMISSION_NOT_FOUND",
                "message": "Ingredient submission not found.",
            },
        )
