
import json
import logging
import random
import re
import time
from collections.abc import Mapping, Sequence

import httpx
from google.genai import errors, types
from pydantic import ValidationError

from app.core.config import get_settings
from app.knowledge.retrieval.schemas import RetrievedEvidence
from app.knowledge.retrieval.service import normalize_ingredient
from app.prompts.skincare_v1 import (
    PROMPT_VERSION,
    SKINCARE_SYSTEM_PROMPT,
)
from app.schemas.analysis import GeminiAnalysisOutput
from app.services.gemini_client import (
    GeminiConfigurationError,
    create_gemini_client,
)
from app.services.gemini_exceptions import (
    GeminiAuthenticationError,
    GeminiInvalidResponseError,
    GeminiRateLimitError,
    GeminiServiceError,
    GeminiTimeoutError,
    GeminiUnavailableError,
)


logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 4.0

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
MAX_EVIDENCE_SNIPPETS = 20
MAX_EVIDENCE_EXCERPT_CHARACTERS = 1200
PRODUCT_CONTEXT_CAUTION = (
    "Product-level effects cannot be determined without concentrations, "
    "full formulation, and individual skin context."
)


def _backoff_seconds(attempt: int) -> float:
    delay = min(
        BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
        MAX_DELAY_SECONDS,
    )
    return random.uniform(0, delay)


def _validate_input(ingredient_text: str) -> str:
    if not isinstance(ingredient_text, str):
        raise ValueError("Ingredient text must be a string.")

    value = ingredient_text.strip()

    if not 3 <= len(value) <= 10000:
        raise ValueError(
            "Ingredient text must contain 3 to 10000 characters."
        )

    return value


def _remove_citation_markers(value: str) -> str:
    return re.sub(r"\s*\[[^\]]+\]", "", value).strip()


def _normalize_candidate_evidence_statuses(
    candidate: object,
) -> object:
    if not isinstance(candidate, dict):
        return candidate

    if not isinstance(candidate.get("ingredients"), list):
        return candidate

    summary_ids = candidate.get("evidence_ids", [])
    if not isinstance(summary_ids, list):
        summary_ids = []
    summary_status = candidate.get("evidence_status", "limited")
    if (
        summary_status == "limited" and summary_ids
    ) or (
        summary_status == "source_grounded" and not summary_ids
    ):
        candidate["evidence_status"] = "limited"
        candidate["evidence_ids"] = []
        if isinstance(candidate.get("summary"), str):
            candidate["summary"] = _remove_citation_markers(
                candidate["summary"]
            )
        logger.warning(
            "Gemini response normalized: scope=summary "
            "reason=inconsistent_evidence_status"
        )

    for ingredient in candidate["ingredients"]:
        if not isinstance(ingredient, dict):
            continue

        evidence_ids = ingredient.get("evidence_ids", [])
        if not isinstance(evidence_ids, list):
            evidence_ids = []
        if (
            isinstance(ingredient.get("function"), str)
            and ingredient["function"].strip().casefold() == "unknown"
        ):
            ingredient["concern_level"] = "unknown"

        if ingredient.get("concern_level") == "unknown":
            if (
                ingredient.get("support_status") != "limited"
                or evidence_ids
            ):
                ingredient["support_status"] = "limited"
                ingredient["evidence_ids"] = []
                evidence_ids = []
                logger.warning(
                    "Gemini response normalized: scope=ingredient "
                    "reason=unknown_finding_cannot_be_supported"
                )

            explanation = ingredient.get("explanation")
            if isinstance(explanation, str):
                normalized_explanation = explanation.casefold()
                uncertainty_terms = (
                    "unknown",
                    "uncertain",
                    "insufficient",
                    "cannot determine",
                    "cannot be established",
                    "unverified",
                    "not established",
                    "not documented",
                    "limited evidence",
                    "limited information",
                    "lack of evidence",
                )
                if not any(
                    term in normalized_explanation
                    for term in uncertainty_terms
                ):
                    ingredient["explanation"] = (
                        f"{explanation.rstrip()} "
                        "Available evidence is insufficient to assess "
                        "this ingredient."
                    )

        support_status = ingredient.get("support_status", "limited")
        must_downgrade = (
            support_status == "supported" and not evidence_ids
        ) or (
            support_status == "conflicting" and len(evidence_ids) < 2
        ) or (
            support_status == "limited" and evidence_ids
        )
        if not must_downgrade:
            continue

        ingredient["support_status"] = "limited"
        ingredient["evidence_ids"] = []
        for field in ("function", "explanation"):
            value = ingredient.get(field)
            if isinstance(value, str):
                ingredient[field] = _remove_citation_markers(value)

        explanation = ingredient.get("explanation")
        if isinstance(explanation, str):
            ingredient["explanation"] = (
                f"{explanation} This finding is not evidence-backed."
            )

        logger.warning(
            "Gemini response normalized: scope=ingredient "
            "reason=inconsistent_evidence_status"
        )

    if candidate["ingredients"] and all(
        isinstance(ingredient, dict)
        and ingredient.get("concern_level") == "unknown"
        for ingredient in candidate["ingredients"]
    ):
        if candidate.get("overall_assessment") != "insufficient_data":
            candidate["overall_assessment"] = "insufficient_data"
            logger.warning(
                "Gemini response normalized: scope=analysis "
                "reason=all_findings_unknown"
            )

    return candidate


def _parse_response(response) -> GeminiAnalysisOutput:
    try:
        if not response.text:
            logger.warning(
                "Gemini response rejected: stage=parse reason=empty_response"
            )
            raise GeminiInvalidResponseError(
                "Gemini returned an empty response."
            )

        candidate = json.loads(response.text)
        candidate = _normalize_candidate_evidence_statuses(candidate)
        return GeminiAnalysisOutput.model_validate_json(
            json.dumps(candidate)
        )

    except ValidationError as exc:
        locations = [
            ".".join(str(part) for part in error["loc"])
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )[:5]
        ]
        error_types = [
            error["type"]
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )[:5]
        ]
        logger.warning(
            "Gemini response rejected: stage=parse "
            "reason=schema_validation error_count=%d "
            "locations=%s types=%s",
            exc.error_count(),
            locations,
            error_types,
        )
        raise GeminiInvalidResponseError(
            "Gemini returned an invalid analysis structure."
        ) from exc
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Gemini response rejected: stage=parse reason=%s",
            type(exc).__name__,
        )
        raise GeminiInvalidResponseError(
            "Gemini returned an invalid analysis structure."
        ) from exc


def _build_model_input(
    ingredient_text: str,
    retrieved_evidence: Sequence[RetrievedEvidence],
) -> str:
    return json.dumps(
        {
            "ingredient_text": ingredient_text,
            "retrieved_evidence": build_evidence_context_records(
                retrieved_evidence
            ),
        },
        ensure_ascii=False,
    )


def build_evidence_context_records(
    retrieved_evidence: Sequence[RetrievedEvidence],
) -> list[dict[str, object]]:
    evidence_records = [
        {
            "evidence_id": str(item.chunk_id),
            "source_identifier": item.source_key,
            "source_id": str(item.source_id),
            "document_id": str(item.document_id),
            "document_version": item.source_version,
            "chunk_id": str(item.chunk_id),
            "content_hash": item.content_hash,
            "relevance_score": item.relevance_score,
            "document_title": item.document_title[:200],
            "original_url": item.original_url[:500],
            "ingredient_name": item.ingredient_name,
            "excerpt": item.excerpt[:MAX_EVIDENCE_EXCERPT_CHARACTERS],
            "location_reference": item.location_reference,
        }
        for item in retrieved_evidence[:MAX_EVIDENCE_SNIPPETS]
    ]
    return evidence_records


def _normalized_claim_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _directly_supported(
    claim: str,
    evidence: Sequence[RetrievedEvidence],
) -> bool:
    normalized_claim = _normalized_claim_text(claim)
    if not normalized_claim:
        return False

    return any(
        normalized_claim
        in _normalized_claim_text(
            item.excerpt[:MAX_EVIDENCE_EXCERPT_CHARACTERS]
        )
        for item in evidence
    )


def _quote_appears_in_evidence(
    quote: str | None,
    evidence: Sequence[RetrievedEvidence],
) -> bool:
    if quote is None:
        return False

    return any(
        quote in item.excerpt[:MAX_EVIDENCE_EXCERPT_CHARACTERS]
        for item in evidence
    )


def _validate_evidence_references(
    result: GeminiAnalysisOutput,
    retrieved_evidence: Sequence[RetrievedEvidence],
    evidence_by_ingredient: Mapping[str, Sequence[str]],
) -> GeminiAnalysisOutput:
    records = {
        str(item.chunk_id): item
        for item in retrieved_evidence[:MAX_EVIDENCE_SNIPPETS]
    }
    data = result.model_dump(mode="python")
    summary_marker_ids = set(
        re.findall(r"\[([^\]]+)\]", result.summary)
    )
    invalid_summary_ids = (
        set(result.evidence_ids) | summary_marker_ids
    ) - set(records)
    unlisted_summary_ids = summary_marker_ids - set(result.evidence_ids)
    unreferenced_summary_ids = set(result.evidence_ids) - summary_marker_ids
    if (
        invalid_summary_ids
        or unlisted_summary_ids
        or unreferenced_summary_ids
    ):
        logger.warning(
            "Gemini citations rejected: scope=summary reason=invalid_or_unlisted_ids "
            "count=%d",
            (
                len(invalid_summary_ids)
                + len(unlisted_summary_ids)
                + len(unreferenced_summary_ids)
            ),
        )
        data["evidence_status"] = "limited"
        data["evidence_ids"] = []
        data["summary"] = _remove_citation_markers(result.summary)

    for index, ingredient in enumerate(result.ingredients):
        expected_ids = set(
            evidence_by_ingredient.get(
                normalize_ingredient(ingredient.name),
                (),
            )
        )
        ingredient_ids = set(ingredient.evidence_ids)
        allowed_ids = expected_ids & set(records)
        text_marker_ids = set(
            re.findall(
                r"\[([^\]]+)\]",
                f"{ingredient.function} {ingredient.explanation}",
            )
        )
        invalid_ids = (ingredient_ids | text_marker_ids) - allowed_ids
        unlisted_text_ids = text_marker_ids - ingredient_ids
        valid_ids = ingredient_ids & allowed_ids
        conflicting_without_sources = (
            ingredient.support_status == "conflicting"
            and len(
                {
                    records[evidence_id].source_id
                    for evidence_id in valid_ids
                }
            ) < 2
        )

        if invalid_ids or unlisted_text_ids or conflicting_without_sources:
            reason = (
                "invalid_or_mismatched_ids"
                if invalid_ids or unlisted_text_ids
                else "insufficient_conflicting_sources"
            )
            logger.warning(
                "Gemini citations rejected: scope=ingredient "
                "reason=%s count=%d",
                reason,
                (
                    len(invalid_ids) + len(unlisted_text_ids)
                    if invalid_ids or unlisted_text_ids
                    else len(valid_ids)
                ),
            )
            data["ingredients"][index]["support_status"] = "limited"
            data["ingredients"][index]["evidence_ids"] = []
            data["ingredients"][index]["supporting_quote"] = None
            data["ingredients"][index]["explanation"] = (
                f"{_remove_citation_markers(ingredient.explanation)} "
                "Citation validation failed; "
                "this finding is not evidence-backed."
            )
            data["ingredients"][index]["function"] = (
                _remove_citation_markers(ingredient.function)
            )

    data["cautions"] = [
        _remove_citation_markers(value)
        for value in result.cautions
    ]
    data["uncertainties"] = [
        _remove_citation_markers(value)
        for value in result.uncertainties
    ]

    return GeminiAnalysisOutput.model_validate(data)


def _apply_evidence_status(
    result: GeminiAnalysisOutput,
    retrieved_evidence: Sequence[RetrievedEvidence],
) -> GeminiAnalysisOutput:
    cautions = list(result.cautions)
    if PRODUCT_CONTEXT_CAUTION not in cautions:
        cautions.append(PRODUCT_CONTEXT_CAUTION)

    evidence_by_id = {
        str(item.chunk_id): item
        for item in retrieved_evidence[:MAX_EVIDENCE_SNIPPETS]
    }
    data = result.model_dump(mode="python")
    for ingredient in data["ingredients"]:
        if ingredient["support_status"] == "limited":
            continue

        cited = [
            evidence_by_id[evidence_id]
            for evidence_id in ingredient["evidence_ids"]
        ]
        if ingredient["support_status"] == "conflicting":
            is_supported = False
        else:
            is_supported = _quote_appears_in_evidence(
                ingredient["supporting_quote"],
                cited,
            )

        if not is_supported:
            ingredient["support_status"] = "limited"
            ingredient["evidence_ids"] = []
            ingredient["supporting_quote"] = None
            ingredient["explanation"] = (
                f"{ingredient['explanation']} Its supporting quote could "
                "not be verified directly against the cited retrieved text "
                "and it is not evidence-backed."
            )

    summary = result.summary
    for evidence_id in result.evidence_ids:
        summary = summary.replace(f"[{evidence_id}]", "")
    cited_summary_evidence = [
        evidence_by_id[evidence_id]
        for evidence_id in result.evidence_ids
    ]
    summary_is_supported = bool(result.evidence_ids) and _directly_supported(
        summary.strip(),
        cited_summary_evidence,
    )

    data["cautions"] = cautions
    data["evidence_status"] = "source_grounded" if summary_is_supported else "limited"
    data["evidence_ids"] = (
        result.evidence_ids if summary_is_supported else []
    )

    if not summary_is_supported:
        limitation = (
            "Limited analysis: the summary could not be verified directly "
            "against cited retrieved text."
            if retrieved_evidence
            else "Limited analysis: no approved matching evidence was retrieved."
        )
        uncertainty = (
            "Summary claims are not evidence-backed because their wording "
            "could not be verified directly against cited retrieved text."
        )
        data["summary"] = f"{limitation} {result.summary}"
        data["uncertainties"] = list(result.uncertainties)
        if uncertainty not in data["uncertainties"]:
            data["uncertainties"].append(uncertainty)

    return GeminiAnalysisOutput.model_validate(data)


def _map_provider_error(exc: Exception) -> GeminiServiceError:
    if isinstance(exc, errors.APIError):
        code = exc.code

        if code in (401, 403):
            return GeminiAuthenticationError(
                "Gemini authentication or access failed."
            )

        if code == 429:
            return GeminiRateLimitError(
                "Gemini request limit exceeded."
            )

        if code in RETRYABLE_STATUS_CODES:
            return GeminiUnavailableError(
                "Gemini provider is temporarily unavailable."
            )

        return GeminiServiceError(
            "Gemini provider rejected the request."
        )

    if isinstance(exc, httpx.TimeoutException):
        return GeminiTimeoutError(
            "Gemini request timed out."
        )

    if isinstance(exc, httpx.TransportError):
        return GeminiUnavailableError(
            "Gemini network connection failed."
        )

    return GeminiServiceError(
        "Gemini analysis failed unexpectedly."
    )


def analyze_skincare_ingredients(
    ingredient_text: str,
    *,
    retrieved_evidence: Sequence[RetrievedEvidence] = (),
    evidence_by_ingredient: Mapping[str, Sequence[str]] | None = None,
) -> GeminiAnalysisOutput:
    """Return a validated skincare analysis from Gemini."""

    validated_text = _validate_input(ingredient_text)
    evidence = tuple(retrieved_evidence[:MAX_EVIDENCE_SNIPPETS])
    evidence_index = evidence_by_ingredient or {
        normalize_ingredient(item.ingredient_name): [str(item.chunk_id)]
        for item in evidence
    }
    settings = get_settings()

    try:
        client = create_gemini_client()
    except GeminiConfigurationError as exc:
        raise GeminiAuthenticationError(
            "Gemini credentials are not configured."
        ) from exc

    try:
        with client:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    logger.info(
                        "Gemini request: prompt=%s attempt=%d",
                        PROMPT_VERSION,
                        attempt,
                    )

                    response = client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_text(
                                        text=_build_model_input(
                                            validated_text,
                                            evidence,
                                        )
                                    )
                                ],
                            )
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=SKINCARE_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            response_json_schema=(
                                GeminiAnalysisOutput.model_json_schema()
                            ),
                            temperature=0,
                            max_output_tokens=4096,
                            http_options=types.HttpOptions(
                                retry_options=types.HttpRetryOptions(
                                    attempts=1,
                                )
                            ),
                        ),
                    )

                    result = _parse_response(response)
                    result = _validate_evidence_references(
                        result,
                        evidence,
                        evidence_index,
                    )
                    result = _apply_evidence_status(result, evidence)

                    logger.info(
                        "Gemini analysis succeeded: prompt=%s",
                        PROMPT_VERSION,
                    )

                    return result

                except (
                    errors.APIError,
                    httpx.TransportError,
                ) as exc:
                    mapped_error = _map_provider_error(exc)

                    retryable = (
                        isinstance(
                            mapped_error,
                            (
                                GeminiRateLimitError,
                                GeminiTimeoutError,
                                GeminiUnavailableError,
                            ),
                        )
                    )

                    logger.warning(
                        "Gemini request failed: type=%s attempt=%d",
                        type(mapped_error).__name__,
                        attempt,
                    )

                    if not retryable or attempt == MAX_ATTEMPTS:
                        raise mapped_error from exc

                    time.sleep(_backoff_seconds(attempt))

    except GeminiServiceError:
        raise
    except Exception as exc:
        logger.exception(
            "Unexpected Gemini service failure"
        )
        raise GeminiServiceError(
            "Gemini analysis could not be completed."
        ) from exc
