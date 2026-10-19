
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
MAX_EVIDENCE_SNIPPETS = 8
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


def _parse_response(response) -> GeminiAnalysisOutput:
    try:
        if not response.text:
            raise GeminiInvalidResponseError(
                "Gemini returned an empty response."
            )

        return GeminiAnalysisOutput.model_validate_json(
            response.text
        )

    except (ValidationError, ValueError, TypeError) as exc:
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


def _validate_evidence_references(
    result: GeminiAnalysisOutput,
    retrieved_evidence: Sequence[RetrievedEvidence],
    evidence_by_ingredient: Mapping[str, Sequence[str]],
) -> None:
    records = {
        str(item.chunk_id): item
        for item in retrieved_evidence[:MAX_EVIDENCE_SNIPPETS]
    }
    cited_ids = set(result.evidence_ids)

    for ingredient in result.ingredients:
        cited_ids.update(ingredient.evidence_ids)

    if not cited_ids.issubset(records):
        raise GeminiInvalidResponseError(
            "Gemini returned an evidence identifier that was not retrieved."
        )

    for ingredient in result.ingredients:
        expected_ids = set(
            evidence_by_ingredient.get(
                normalize_ingredient(ingredient.name),
                (),
            )
        )
        ingredient_ids = set(ingredient.evidence_ids)

        if ingredient_ids and not ingredient_ids.issubset(expected_ids):
            raise GeminiInvalidResponseError(
                "Gemini cited evidence for a different ingredient."
            )

        if ingredient.support_status == "conflicting":
            source_ids = {
                records[evidence_id].source_id
                for evidence_id in ingredient_ids
            }
            if len(source_ids) < 2:
                raise GeminiInvalidResponseError(
                    "Conflicting findings require evidence from "
                    "multiple retrieved sources."
                )


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
        claim_texts = (
            ingredient["function"],
            ingredient["explanation"],
        )

        if ingredient["support_status"] == "conflicting":
            is_supported = False
        else:
            is_supported = all(
                _directly_supported(claim, cited)
                for claim in claim_texts
            )

        if not is_supported:
            ingredient["support_status"] = "limited"
            ingredient["evidence_ids"] = []
            ingredient["explanation"] = (
                f"{ingredient['explanation']} This finding could not be "
                "verified directly against the retrieved text and is not "
                "evidence-backed."
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
                    _validate_evidence_references(
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
