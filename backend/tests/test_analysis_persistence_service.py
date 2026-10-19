from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.ingredient_analysis import AnalysisStatus
from app.schemas.analysis import GeminiAnalysisOutput
from app.services.analysis_persistence_service import (
    InvalidAnalysisStateError,
    mark_completed,
    mark_failed,
)


def _analysis_result():
    return GeminiAnalysisOutput.model_validate(
        {
            "overall_assessment": "low_concern",
            "evidence_status": "source_grounded",
            "evidence_ids": ["chunk-1"],
            "summary": "Glycerin supports hydration.",
            "ingredients": [
                {
                    "name": "Glycerin",
                    "function": "Humectant",
                    "concern_level": "low",
                    "explanation": "Supports hydration.",
                    "support_status": "supported",
                    "evidence_ids": ["chunk-1"],
                }
            ],
            "cautions": [],
            "uncertainties": [],
        }
    )


def test_mark_completed_persists_snapshot_and_versions():
    analysis = SimpleNamespace(
        status=AnalysisStatus.PROCESSING,
        result=None,
        completed_at=None,
        failure_code=None,
        failure_message=None,
    )

    class FakeDb:
        def get(self, model, key):
            return analysis

        def commit(self):
            pass

        def refresh(self, record):
            pass

    references = [{"evidence_id": "chunk-1", "document_version": "v2"}]
    config = {"version": "retrieval-v1.0.0"}

    persisted = mark_completed(
        FakeDb(),
        uuid4(),
        _analysis_result(),
        evidence_references=references,
        evidence_coverage="full",
        retrieval_config=config,
    )

    assert persisted.evidence_references == references
    assert persisted.evidence_coverage == "full"
    assert persisted.retrieval_config == config
    assert persisted.result["evidence_ids"] == ["chunk-1"]
    assert persisted.status == AnalysisStatus.COMPLETED


def test_failed_rerun_does_not_change_previous_completed_result():
    previous_result = {"summary": "Previously completed evidence-backed result."}
    previous = SimpleNamespace(
        status=AnalysisStatus.COMPLETED,
        result=previous_result,
        completed_at=datetime.now(timezone.utc),
        evidence_references=[{"evidence_id": "saved-chunk"}],
    )
    failed_rerun = SimpleNamespace(
        status=AnalysisStatus.PROCESSING,
        result=None,
        completed_at=None,
        evidence_references=[],
        evidence_coverage="unavailable",
        retrieval_config={},
        failure_code=None,
        failure_message=None,
    )

    class FakeDb:
        def get(self, model, key):
            return failed_rerun

        def commit(self):
            pass

        def refresh(self, record):
            pass

    mark_failed(FakeDb(), uuid4(), "GEMINI_UNAVAILABLE")

    assert previous.result == previous_result
    assert previous.evidence_references == [
        {"evidence_id": "saved-chunk"}
    ]
    assert failed_rerun.result is None
    assert failed_rerun.status == AnalysisStatus.FAILED


def test_completed_analysis_cannot_be_overwritten_by_failure():
    completed = SimpleNamespace(
        status=AnalysisStatus.COMPLETED,
        result={"summary": "Saved result."},
        completed_at=datetime.now(timezone.utc),
    )

    class FakeDb:
        def get(self, model, key):
            return completed

    with pytest.raises(InvalidAnalysisStateError):
        mark_failed(FakeDb(), uuid4(), "GEMINI_UNAVAILABLE")

    assert completed.result == {"summary": "Saved result."}
