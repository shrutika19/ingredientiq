from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.routes.analysis import to_api_response
from app.models.ingredient_analysis import AnalysisStatus


def test_legacy_analysis_is_returned_as_limited():
    now = datetime.now(timezone.utc)
    analysis = SimpleNamespace(
        id=uuid4(),
        submission_id=uuid4(),
        status=AnalysisStatus.COMPLETED,
        result={
            "overall_assessment": "low_concern",
            "summary": "Common ingredient functions were identified.",
            "ingredients": [
                {
                    "name": "Glycerin",
                    "function": "Humectant",
                    "concern_level": "low",
                    "explanation": "Helps retain moisture.",
                }
            ],
            "cautions": [],
            "uncertainties": [],
        },
        failure_code=None,
        created_at=now,
        completed_at=now,
    )

    response = to_api_response(analysis)

    assert response.result is not None
    assert response.result.evidence_status == "limited"
    assert response.result.ingredients[0].support_status == "limited"
    assert response.result.evidence_ids == []
    assert response.result.summary.startswith("Limited analysis:")
    assert any(
        "full formulation" in caution
        for caution in response.result.cautions
    )
    assert response.evidence_coverage == "unavailable"
    assert response.evidence_references == []


def test_saved_evidence_snapshot_is_returned_by_api():
    now = datetime.now(timezone.utc)
    reference = {
        "evidence_id": uuid4(),
        "source_id": uuid4(),
        "source_identifier": "APPROVED_SOURCE",
        "document_id": uuid4(),
        "document_version": "v7",
        "chunk_id": uuid4(),
        "ingredient_name": "Glycerin",
        "excerpt": "Glycerin supports hydration.",
        "original_url": "https://example.org/glycerin",
        "document_title": "Glycerin reference",
        "location_reference": "section-2",
    }
    analysis = SimpleNamespace(
        id=uuid4(),
        submission_id=uuid4(),
        status=AnalysisStatus.COMPLETED,
        result={
            "overall_assessment": "low_concern",
            "evidence_status": "source_grounded",
            "evidence_ids": [str(reference["evidence_id"])],
            "summary": "Glycerin supports hydration.",
            "ingredients": [
                {
                    "name": "Glycerin",
                    "function": "Humectant",
                    "concern_level": "low",
                    "explanation": "Supports hydration.",
                    "support_status": "supported",
                    "evidence_ids": [str(reference["evidence_id"])],
                }
            ],
            "cautions": [],
            "uncertainties": [],
        },
        evidence_references=[reference],
        evidence_coverage="full",
        prompt_version="skincare-v1.1.0",
        retrieval_config={"version": "retrieval-v1.0.0"},
        failure_code=None,
        created_at=now,
        completed_at=now,
    )

    response = to_api_response(analysis)

    assert response.evidence_coverage == "full"
    assert response.prompt_version == "skincare-v1.1.0"
    assert response.retrieval_config["version"] == "retrieval-v1.0.0"
    assert response.evidence_references[0].document_version == "v7"
    assert response.evidence_references[0].excerpt == (
        "Glycerin supports hydration."
    )
