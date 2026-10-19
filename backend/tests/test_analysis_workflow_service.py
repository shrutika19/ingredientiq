from types import SimpleNamespace
from uuid import uuid4

from app.knowledge.retrieval.schemas import (
    IngredientRetrievalResult,
    RetrievedEvidence,
)
from app.models.ingredient_analysis import AnalysisStatus
from app.schemas.analysis import GeminiAnalysisOutput
from app.services import analysis_workflow_service


def test_workflow_retrieves_evidence_before_gemini(monkeypatch):
    submission_id = uuid4()
    analysis_id = uuid4()
    evidence_id = uuid4()
    events = []

    evidence = RetrievedEvidence(
        chunk_id=evidence_id,
        source_id=uuid4(),
        source_key="APPROVED_SOURCE",
        document_id=uuid4(),
        ingredient_id=uuid4(),
        ingredient_name="Glycerin",
        relevance_score=0.9,
        distance=0.1,
        excerpt="Glycerin supports hydration.",
        original_url="https://example.org/glycerin",
        document_title="Glycerin reference",
        source_version="v1",
    )

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class FakeSession:
        def get(self, model, key):
            return SimpleNamespace(
                original_text="Glycerin",
            )

        def query(self, model):
            return FakeQuery()

    monkeypatch.setattr(
        analysis_workflow_service,
        "get_settings",
        lambda: SimpleNamespace(
            GEMINI_MODEL="test-model",
            EMBEDDING_MODEL="test-embedding",
            RETRIEVAL_MIN_SIMILARITY=0.65,
            RETRIEVAL_CANDIDATE_MULTIPLIER=4,
        ),
    )
    monkeypatch.setattr(
        analysis_workflow_service,
        "create_analysis",
        lambda **kwargs: SimpleNamespace(id=analysis_id),
    )
    monkeypatch.setattr(
        analysis_workflow_service,
        "mark_processing",
        lambda *args, **kwargs: None,
    )

    def retrieve(db, ingredient_text):
        assert ingredient_text == "Glycerin"
        events.append("retrieve")
        return [evidence], {"glycerin": [str(evidence_id)]}

    def analyze(ingredient_text, **kwargs):
        assert ingredient_text == "Glycerin"
        assert kwargs["retrieved_evidence"] == [evidence]
        assert kwargs["evidence_by_ingredient"] == {
            "glycerin": [str(evidence_id)]
        }
        events.append("gemini")
        return GeminiAnalysisOutput.model_validate(
            {
                "overall_assessment": "low_concern",
                "evidence_status": "source_grounded",
                "evidence_ids": [str(evidence_id)],
                "summary": f"Supported by [{evidence_id}].",
                "ingredients": [
                    {
                        "name": "Glycerin",
                        "function": "Humectant",
                        "concern_level": "low",
                        "explanation": "Supports hydration.",
                        "support_status": "supported",
                        "evidence_ids": [str(evidence_id)],
                    }
                ],
                "cautions": [],
                "uncertainties": [],
            }
        )

    completed = {}
    monkeypatch.setattr(
        analysis_workflow_service,
        "_retrieve_submission_evidence",
        retrieve,
    )
    monkeypatch.setattr(
        analysis_workflow_service,
        "analyze_skincare_ingredients",
        analyze,
    )
    monkeypatch.setattr(
        analysis_workflow_service,
        "mark_completed",
        lambda **kwargs: completed.update(kwargs) or kwargs["result"],
    )

    result = analysis_workflow_service.start_analysis(
        FakeSession(),
        submission_id,
    )

    assert events == ["retrieve", "gemini"]
    assert result.evidence_status == "source_grounded"
    assert completed["evidence_coverage"] == "full"
    assert completed["retrieval_config"]["version"] == (
        analysis_workflow_service.RETRIEVAL_CONFIG_VERSION
    )
    assert completed["evidence_references"] == [
        {
            "evidence_id": str(evidence_id),
            "source_id": str(evidence.source_id),
            "source_identifier": "APPROVED_SOURCE",
            "document_id": str(evidence.document_id),
            "document_version": "v1",
            "chunk_id": str(evidence_id),
            "ingredient_name": "Glycerin",
            "excerpt": "Glycerin supports hydration.",
            "original_url": "https://example.org/glycerin",
            "document_title": "Glycerin reference",
            "location_reference": None,
        }
    ]


def test_retrieval_context_is_bounded_to_eight_snippets(monkeypatch):
    retrieval_calls = []

    def fake_retrieve(*, db, ingredient_name, top_k):
        retrieval_calls.append((ingredient_name, top_k))
        evidence = [
            RetrievedEvidence(
                chunk_id=uuid4(),
                source_id=uuid4(),
                source_key="APPROVED_SOURCE",
                document_id=uuid4(),
                ingredient_id=uuid4(),
                ingredient_name=ingredient_name,
                relevance_score=0.9,
                distance=0.1,
                excerpt=f"Evidence for {ingredient_name}.",
                original_url="https://example.org/evidence",
                document_title="Evidence",
                source_version="v1",
            )
            for _ in range(top_k)
        ]
        return IngredientRetrievalResult(
            ingredient=ingredient_name,
            normalized_ingredient=ingredient_name.casefold(),
            status="found",
            evidence=evidence,
        )

    monkeypatch.setattr(
        analysis_workflow_service,
        "retrieve_ingredient_evidence",
        fake_retrieve,
    )

    evidence, evidence_by_ingredient = (
        analysis_workflow_service._retrieve_submission_evidence(
            db=object(),
            ingredient_text=(
                "Aqua, Glycerin, Niacinamide, Panthenol, "
                "Tocopherol"
            ),
        )
    )

    assert len(evidence) == 8
    assert len(retrieval_calls) == 4
    assert all(top_k == 2 for _, top_k in retrieval_calls)
    assert evidence_by_ingredient


def test_evidence_coverage_distinguishes_partial_and_unavailable():
    assert analysis_workflow_service._evidence_coverage(
        "Aqua, Glycerin",
        {"glycerin": ["chunk-1"]},
    ) == "partial"

    assert analysis_workflow_service._evidence_coverage(
        "Aqua, Glycerin",
        {},
    ) == "unavailable"

    assert analysis_workflow_service._evidence_coverage(
        "Aqua, Glycerin",
        {
            "aqua": ["chunk-1"],
            "glycerin": ["chunk-2"],
        },
    ) == "full"


def test_get_latest_analysis_preserves_previous_success_after_failed_retry(
    monkeypatch,
):
    completed = SimpleNamespace(status=AnalysisStatus.COMPLETED)
    failed = SimpleNamespace(status=AnalysisStatus.FAILED)

    monkeypatch.setattr(
        analysis_workflow_service,
        "get_submission_analyses",
        lambda **kwargs: [failed, completed],
    )
    db = SimpleNamespace(
        get=lambda model, key: SimpleNamespace(id=key),
    )

    result = analysis_workflow_service.get_latest_analysis(
        db,
        uuid4(),
    )

    assert result is completed
