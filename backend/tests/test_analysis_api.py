from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.routes import analysis as analysis_route
from app.database.dependencies import get_db
from app.main import app
from app.api.routes.analysis import to_api_response
from app.models.ingredient_analysis import AnalysisStatus
from app.services.api_limits import enforce_analysis_limits


def test_analyze_queues_background_work_and_returns_accepted(monkeypatch):
    submission_id = uuid4()
    analysis_id = uuid4()
    now = datetime.now(timezone.utc)
    pending = SimpleNamespace(
        id=analysis_id,
        submission_id=submission_id,
        status=AnalysisStatus.PENDING,
        result=None,
        evidence_references=[],
        evidence_coverage="unavailable",
        prompt_version="skincare-v1",
        retrieval_config={},
        failure_code=None,
        created_at=now,
        completed_at=None,
    )
    tasks = []
    request_db = MagicMock()

    def fake_db():
        yield request_db

    monkeypatch.setattr(
        analysis_route,
        "queue_analysis",
        lambda db, submission_id: pending,
    )
    monkeypatch.setattr(
        analysis_route,
        "run_analysis_background",
        lambda submission_id, analysis_id: tasks.append(
            (submission_id, analysis_id)
        ),
    )
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[enforce_analysis_limits] = lambda: None

    try:
        with TestClient(
            app,
            client=("127.0.0.1", 50000),
        ) as client:
            response = client.post(
                f"/api/v1/submissions/{submission_id}/analyze"
            )

        assert response.status_code == 202
        assert response.json()["status"] == "PENDING"
        assert response.json()["analysis_id"] == str(analysis_id)
        assert response.headers["location"] == (
            f"/api/v1/submissions/{submission_id}/analysis"
        )
        assert tasks == [(submission_id, analysis_id)]
        request_db.close.assert_called_once()
    finally:
        app.dependency_overrides.clear()


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
    assert response.result.ingredients[0].supporting_quote is None
    assert response.evidence_coverage == "unavailable"
    assert response.evidence_references == []


def test_saved_evidence_snapshot_is_returned_by_api():
    now = datetime.now(timezone.utc)
    reference = {
        "evidence_id": uuid4(),
        "source_id": uuid4(),
        "source_identifier": "APPROVED_SOURCE",
        "source_organization": "Example Research Institute",
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
    assert response.evidence_references[0].source_organization == (
        "Example Research Institute"
    )
