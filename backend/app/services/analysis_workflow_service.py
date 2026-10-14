
import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ingredient_analysis import (
    AnalysisStatus,
    IngredientAnalysis,
)
from app.models.ingredient_submission import IngredientSubmission
from app.services.analysis_persistence_service import (
    create_analysis,
    get_submission_analyses,
    mark_completed,
    mark_failed,
    mark_processing,
)
from app.services.gemini_exceptions import (
    GeminiAuthenticationError,
    GeminiInvalidResponseError,
    GeminiRateLimitError,
    GeminiServiceError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)
from app.services.skincare_analysis_service import (
    analyze_skincare_ingredients,
)
from app.core.config import get_settings
from app.prompts.skincare_v1 import PROMPT_VERSION


logger = logging.getLogger(__name__)


class SubmissionNotFound(Exception):
    pass


class AnalysisAlreadyRunning(Exception):
    pass


class AnalysisExecutionFailed(Exception):
    def __init__(self, code: str, http_status: int):
        self.code = code
        self.http_status = http_status
        super().__init__(code)


def _failure_details(exc: Exception) -> tuple[str, int]:
    if isinstance(exc, GeminiAuthenticationError):
        return "GEMINI_AUTH_ERROR", 503
    if isinstance(exc, GeminiRateLimitError):
        return "GEMINI_RATE_LIMIT", 429
    if isinstance(exc, GeminiTimeoutError):
        return "GEMINI_TIMEOUT", 504
    if isinstance(exc, GeminiUnavailableError):
        return "GEMINI_UNAVAILABLE", 503
    if isinstance(exc, GeminiInvalidResponseError):
        return "INVALID_AI_RESPONSE", 502
    return "ANALYSIS_ERROR", 502


def start_analysis(
    db: Session,
    submission_id: UUID,
) -> IngredientAnalysis:
    submission = db.get(IngredientSubmission, submission_id)

    if submission is None:
        raise SubmissionNotFound()

    active = (
        db.query(IngredientAnalysis)
        .filter(
            IngredientAnalysis.submission_id == submission_id,
            IngredientAnalysis.status.in_([
                AnalysisStatus.PENDING,
                AnalysisStatus.PROCESSING,
            ]),
        )
        .first()
    )

    if active is not None:
        raise AnalysisAlreadyRunning()

    settings = get_settings()

    try:
        analysis = create_analysis(
            db=db,
            submission_id=submission_id,
            model_id=settings.GEMINI_MODEL,
            prompt_version=PROMPT_VERSION,
        )
    except IntegrityError as exc:
        db.rollback()
        raise AnalysisAlreadyRunning() from exc

    analysis_id = analysis.id
    mark_processing(db, analysis_id)

    try:
        result = analyze_skincare_ingredients(
            submission.original_text
        )

        return mark_completed(
            db=db,
            analysis_id=analysis_id,
            result=result,
        )

    except GeminiServiceError as exc:
        code, http_status = _failure_details(exc)

        logger.warning(
            "Ingredient analysis failed: analysis_id=%s code=%s",
            analysis_id,
            code,
        )

        mark_failed(
            db=db,
            analysis_id=analysis_id,
            failure_code=code,
        )

        raise AnalysisExecutionFailed(
            code=code,
            http_status=http_status,
        ) from exc


def get_latest_analysis(
    db: Session,
    submission_id: UUID,
) -> IngredientAnalysis | None:
    submission = db.get(IngredientSubmission, submission_id)

    if submission is None:
        raise SubmissionNotFound()

    analyses = get_submission_analyses(
        db=db,
        submission_id=submission_id,
    )

    return analyses[0] if analyses else None
