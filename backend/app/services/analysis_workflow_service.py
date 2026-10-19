
import logging
from uuid import UUID

import httpx
from google.genai import errors
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.knowledge.embedding.client import EmbeddingError
from app.knowledge.normalization.parser import (
    normalize_name,
    parse_ingredient_list,
)
from app.knowledge.retrieval.schemas import RetrievedEvidence
from app.knowledge.retrieval.service import retrieve_ingredient_evidence
from app.models.ingredient_analysis import (
    AnalysisStatus,
    IngredientAnalysis,
)
from app.schemas.analysis import GeminiAnalysisOutput
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
    MAX_EVIDENCE_SNIPPETS,
    MAX_EVIDENCE_EXCERPT_CHARACTERS,
    analyze_skincare_ingredients,
)
from app.prompts.skincare_v1 import PROMPT_VERSION


logger = logging.getLogger(__name__)
RETRIEVAL_CONFIG_VERSION = "retrieval-v1.0.0"


class SubmissionNotFound(Exception):
    pass


class AnalysisAlreadyRunning(Exception):
    pass


class AnalysisExecutionFailed(Exception):
    def __init__(self, code: str, http_status: int):
        self.code = code
        self.http_status = http_status
        super().__init__(code)


def _retrieve_submission_evidence(
    db: Session,
    ingredient_text: str,
) -> tuple[list[RetrievedEvidence], dict[str, list[str]]]:
    ingredient_names = parse_ingredient_list(ingredient_text)
    evidence: list[RetrievedEvidence] = []
    evidence_by_ingredient: dict[str, list[str]] = {}
    seen_names: set[str] = set()
    seen_evidence_ids: set[str] = set()

    for ingredient_name in ingredient_names:
        normalized_name = normalize_name(ingredient_name)
        if normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)

        remaining = MAX_EVIDENCE_SNIPPETS - len(evidence)
        if remaining <= 0:
            break

        retrieval = retrieve_ingredient_evidence(
            db=db,
            ingredient_name=ingredient_name,
            top_k=min(2, remaining),
        )

        for item in retrieval.evidence[:remaining]:
            evidence_id = str(item.chunk_id)
            if evidence_id not in seen_evidence_ids:
                evidence.append(item)
                seen_evidence_ids.add(evidence_id)

            for name in (ingredient_name, item.ingredient_name):
                normalized = normalize_name(name)
                ids = evidence_by_ingredient.setdefault(normalized, [])
                if evidence_id not in ids:
                    ids.append(evidence_id)

    return evidence, evidence_by_ingredient


def _evidence_coverage(
    ingredient_text: str,
    evidence_by_ingredient: dict[str, list[str]],
) -> str:
    ingredient_names = {
        normalize_name(name)
        for name in parse_ingredient_list(ingredient_text)
    }
    covered = ingredient_names.intersection(evidence_by_ingredient)

    if not covered:
        return "unavailable"
    if covered == ingredient_names:
        return "full"
    return "partial"


def _evidence_reference_snapshots(
    result: GeminiAnalysisOutput,
    evidence: list[RetrievedEvidence],
) -> list[dict[str, object]]:
    used_ids = set(result.evidence_ids)
    for ingredient in result.ingredients:
        used_ids.update(ingredient.evidence_ids)

    snapshots = []
    for item in evidence:
        evidence_id = str(item.chunk_id)
        if evidence_id not in used_ids:
            continue

        snapshots.append(
            {
                "evidence_id": evidence_id,
                "source_id": str(item.source_id),
                "source_identifier": item.source_key,
                "document_id": str(item.document_id),
                "document_version": item.source_version,
                "chunk_id": evidence_id,
                "ingredient_name": item.ingredient_name,
                "excerpt": item.excerpt[
                    :MAX_EVIDENCE_EXCERPT_CHARACTERS
                ],
                "original_url": item.original_url,
                "document_title": item.document_title,
                "location_reference": item.location_reference,
            }
        )

    return snapshots


def _retrieval_config_snapshot() -> dict[str, object]:
    settings = get_settings()
    return {
        "version": RETRIEVAL_CONFIG_VERSION,
        "embedding_model": settings.EMBEDDING_MODEL,
        "top_k_per_ingredient": 2,
        "max_evidence_snippets": MAX_EVIDENCE_SNIPPETS,
        "max_excerpt_characters": MAX_EVIDENCE_EXCERPT_CHARACTERS,
        "min_similarity": settings.RETRIEVAL_MIN_SIMILARITY,
        "candidate_multiplier": settings.RETRIEVAL_CANDIDATE_MULTIPLIER,
    }


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
        evidence, evidence_by_ingredient = _retrieve_submission_evidence(
            db,
            submission.original_text,
        )

        result = analyze_skincare_ingredients(
            submission.original_text,
            retrieved_evidence=evidence,
            evidence_by_ingredient=evidence_by_ingredient,
        )

        evidence_references = _evidence_reference_snapshots(
            result,
            evidence,
        )
        evidence_coverage = _evidence_coverage(
            submission.original_text,
            evidence_by_ingredient,
        )

        return mark_completed(
            db=db,
            analysis_id=analysis_id,
            result=result,
            evidence_references=evidence_references,
            evidence_coverage=evidence_coverage,
            retrieval_config=_retrieval_config_snapshot(),
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

    except (
        EmbeddingError,
        SQLAlchemyError,
        httpx.TransportError,
        errors.APIError,
        ValueError,
    ) as exc:
        if isinstance(exc, SQLAlchemyError):
            db.rollback()

        logger.warning(
            "Ingredient evidence retrieval failed: analysis_id=%s type=%s",
            analysis_id,
            type(exc).__name__,
        )
        mark_failed(
            db=db,
            analysis_id=analysis_id,
            failure_code="ANALYSIS_ERROR",
        )
        raise AnalysisExecutionFailed(
            code="ANALYSIS_ERROR",
            http_status=502,
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

    if not analyses:
        return None

    latest = analyses[0]
    if latest.status == AnalysisStatus.FAILED:
        return next(
            (
                analysis
                for analysis in analyses[1:]
                if analysis.status == AnalysisStatus.COMPLETED
            ),
            latest,
        )

    return latest
