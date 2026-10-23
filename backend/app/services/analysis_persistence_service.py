
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.ingredient_analysis import (
    AnalysisStatus,
    IngredientAnalysis,
)
from app.models.ingredient_submission import IngredientSubmission
from app.schemas.analysis import GeminiAnalysisOutput


class SubmissionNotFoundError(Exception):
    pass


class InvalidAnalysisStateError(Exception):
    pass


def create_analysis(
    db: Session,
    submission_id: UUID,
    model_id: str,
    prompt_version: str,
) -> IngredientAnalysis:
    submission = db.get(
        IngredientSubmission,
        submission_id,
    )

    if submission is None:
        raise SubmissionNotFoundError(
            "Ingredient submission not found."
        )

    analysis = IngredientAnalysis(
        submission_id=submission_id,
        model_id=model_id,
        prompt_version=prompt_version,
        status=AnalysisStatus.PENDING,
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


def mark_processing(
    db: Session,
    analysis_id: UUID,
) -> IngredientAnalysis:
    analysis = db.get(IngredientAnalysis, analysis_id)

    if analysis is None:
        raise InvalidAnalysisStateError(
            "Analysis not found."
        )

    if analysis.status != AnalysisStatus.PENDING:
        raise InvalidAnalysisStateError(
            "Only pending analyses can start processing."
        )

    analysis.status = AnalysisStatus.PROCESSING
    db.commit()
    db.refresh(analysis)

    return analysis


def mark_completed(
    db: Session,
    analysis_id: UUID,
    result: GeminiAnalysisOutput,
    *,
    evidence_references: list[dict[str, Any]] | None = None,
    evidence_coverage: str = "unavailable",
    retrieval_config: dict[str, Any] | None = None,
) -> IngredientAnalysis:
    analysis = db.get(IngredientAnalysis, analysis_id)

    if analysis is None or analysis.status != AnalysisStatus.PROCESSING:
        raise InvalidAnalysisStateError(
            "Analysis must be processing before completion."
        )

    analysis.result = result.model_dump(mode="json")
    analysis.evidence_references = evidence_references or []
    analysis.evidence_coverage = evidence_coverage
    analysis.retrieval_config = retrieval_config or {}
    analysis.status = AnalysisStatus.COMPLETED
    analysis.completed_at = datetime.now(timezone.utc)
    analysis.failure_code = None
    analysis.failure_message = None

    db.commit()
    db.refresh(analysis)

    return analysis


ALLOWED_FAILURES = {
    "GEMINI_AUTH_ERROR": "AI provider authentication failed.",
    "GEMINI_RATE_LIMIT": "AI provider rate limit exceeded.",
    "GEMINI_TIMEOUT": "AI provider request timed out.",
    "GEMINI_UNAVAILABLE": "AI provider temporarily unavailable.",
    "INVALID_AI_RESPONSE": "AI provider returned an invalid response.",
    "ANALYSIS_ERROR": "Analysis could not be completed.",
}


def mark_failed(
    db: Session,
    analysis_id: UUID,
    failure_code: str,
) -> IngredientAnalysis:
    analysis = db.get(IngredientAnalysis, analysis_id)

    if analysis is None or analysis.status not in (
        AnalysisStatus.PENDING,
        AnalysisStatus.PROCESSING,
    ):
        raise InvalidAnalysisStateError(
            "Analysis cannot transition to failed."
        )

    if failure_code not in ALLOWED_FAILURES:
        failure_code = "ANALYSIS_ERROR"

    analysis.status = AnalysisStatus.FAILED
    analysis.result = None
    analysis.failure_code = failure_code
    analysis.failure_message = ALLOWED_FAILURES[failure_code]
    analysis.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(analysis)

    return analysis


def fail_stale_active_analyses(
    db: Session,
    stale_after: timedelta = timedelta(minutes=3),
) -> int:
    cutoff = datetime.now(timezone.utc) - stale_after
    result = db.execute(
        update(IngredientAnalysis)
        .where(
            IngredientAnalysis.status.in_(
                [AnalysisStatus.PENDING, AnalysisStatus.PROCESSING]
            ),
            IngredientAnalysis.created_at < cutoff,
        )
        .values(
            status=AnalysisStatus.FAILED,
            result=None,
            failure_code="ANALYSIS_ERROR",
            failure_message=ALLOWED_FAILURES["ANALYSIS_ERROR"],
            completed_at=datetime.now(timezone.utc),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount or 0


def get_analysis(
    db: Session,
    analysis_id: UUID,
) -> IngredientAnalysis | None:
    return db.get(IngredientAnalysis, analysis_id)


def get_submission_analyses(
    db: Session,
    submission_id: UUID,
) -> list[IngredientAnalysis]:
    return list(
        db.scalars(
            select(IngredientAnalysis)
            .where(
                IngredientAnalysis.submission_id == submission_id
            )
            .order_by(
                IngredientAnalysis.created_at.desc(),
                IngredientAnalysis.id.desc(),
            )
        ).all()
    )
