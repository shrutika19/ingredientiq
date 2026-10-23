
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.dependencies import get_db
from app.models.ingredient_analysis import IngredientAnalysis
from app.schemas.analysis_api import (
    AnalysisApiResponse,
    AnalysisErrorResponse,
)
from app.schemas.analysis import GeminiAnalysisOutput
from app.services.analysis_workflow_service import (
    AnalysisAlreadyRunning,
    SubmissionNotFound,
    get_latest_analysis,
    queue_analysis,
    run_analysis_background,
)
from app.services.api_limits import enforce_analysis_limits


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
        evidence_references=getattr(
            analysis,
            "evidence_references",
            [],
        ) or [],
        evidence_coverage=getattr(
            analysis,
            "evidence_coverage",
            "unavailable",
        ),
        prompt_version=getattr(analysis, "prompt_version", None),
        retrieval_config=getattr(
            analysis,
            "retrieval_config",
            {},
        ) or {},
        failure_code=analysis.failure_code,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )


@router.post(
    "/{id}/analyze",
    response_model=AnalysisApiResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_analysis_limits)],
    description=(
        "Queues an ingredient analysis and returns its pending status. "
        "Poll the submission's analysis endpoint for progress and results."
    ),
    responses={
        404: {"model": AnalysisErrorResponse},
        409: {"model": AnalysisErrorResponse},
        429: {"model": AnalysisErrorResponse},
    },
)
def analyze_submission(
    id: UUID,
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        analysis = queue_analysis(
            db=db,
            submission_id=id,
        )
        analysis_response = to_api_response(analysis)
        db.close()

        background_tasks.add_task(
            run_analysis_background,
            id,
            analysis.id,
        )
        response.headers["Location"] = (
            f"{get_settings().API_V1_PREFIX}"
            f"{router.prefix}/{id}/analysis"
        )
        return analysis_response

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
