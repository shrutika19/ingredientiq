from types import SimpleNamespace
from uuid import uuid4

from app.knowledge.retrieval.schemas import (
    IngredientRetrievalResult,
    RetrievedEvidence,
)
from app.knowledge.normalization.schemas import (
    IngredientMatch,
    NormalizationResult,
    ResolutionStatus,
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
        source_key="MOCK_SOURCE",
        document_id=uuid4(),
        ingredient_id=uuid4(),
        ingredient_name="Glycerin",
        relevance_score=0.9,
        distance=0.1,
        excerpt="Glycerin is a Humectant. Supports hydration.",
        content_hash="chunk-sha256",
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
                id=key,
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

    normalization = NormalizationResult(
        submission_id=submission_id,
        original_text="Glycerin",
        ingredients=[
            IngredientMatch(
                position=0,
                original_name="Glycerin",
                normalized_name="glycerin",
                status=ResolutionStatus.RESOLVED,
                ingredient_id=uuid4(),
                canonical_name="Glycerin",
                match_type="canonical",
            )
        ],
    )

    def retrieve(db, normalized_submission_id):
        assert normalized_submission_id == submission_id
        events.append("retrieve")
        return (
            [evidence],
            {"glycerin": [str(evidence_id)]},
            normalization,
        )

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
                "summary": f"Glycerin is a Humectant. [{evidence_id}]",
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
            "source_identifier": "MOCK_SOURCE",
            "document_id": str(evidence.document_id),
            "document_version": "v1",
            "chunk_id": str(evidence_id),
            "ingredient_name": "Glycerin",
            "content_hash": "chunk-sha256",
            "relevance_score": 0.9,
            "document_title": "Glycerin reference",
            "excerpt": "Glycerin is a Humectant. Supports hydration.",
            "location_reference": None,
            "original_url": "https://example.org/glycerin",
        }
    ]


def test_retrieval_context_is_bounded_to_eight_snippets(monkeypatch):
    retrieval_calls = []
    submission_id = uuid4()
    normalization = NormalizationResult(
        submission_id=submission_id,
        original_text="Aqua, Glycerin, Niacinamide, Panthenol, Tocopherol",
        ingredients=[
            IngredientMatch(
                position=index,
                original_name=name,
                normalized_name=name.casefold(),
                status=ResolutionStatus.RESOLVED,
                ingredient_id=uuid4(),
                canonical_name=name,
                match_type="canonical",
            )
            for index, name in enumerate(
                ("Aqua", "Glycerin", "Niacinamide", "Panthenol", "Tocopherol")
            )
        ],
    )
    ingredient_ids = {
        match.original_name: match.ingredient_id
        for match in normalization.ingredients
        if match.ingredient_id is not None
    }

    monkeypatch.setattr(
        analysis_workflow_service,
        "normalize_submission",
        lambda db, requested_id: normalization,
    )

    def fake_retrieve(*, db, ingredient_name, top_k):
        retrieval_calls.append((ingredient_name, top_k))
        evidence = [
            RetrievedEvidence(
                chunk_id=uuid4(),
                source_id=uuid4(),
                source_key="MOCK_SOURCE",
                document_id=uuid4(),
                ingredient_id=ingredient_ids[ingredient_name],
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

    evidence, evidence_by_ingredient, _ = (
        analysis_workflow_service._retrieve_submission_evidence(
            db=object(),
            submission_id=submission_id,
        )
    )

    assert len(evidence) == 8
    assert len(retrieval_calls) == 4
    assert all(top_k == 2 for _, top_k in retrieval_calls)
    assert evidence_by_ingredient


def test_only_uniquely_resolved_ingredients_are_retrieved(monkeypatch):
    submission_id = uuid4()
    glycerin_id = uuid4()
    calls = []
    normalization = NormalizationResult(
        submission_id=submission_id,
        original_text="Glycerin, Water, Mystery Compound",
        ingredients=[
            IngredientMatch(
                position=0,
                original_name="Glycerin",
                normalized_name="glycerin",
                status=ResolutionStatus.RESOLVED,
                ingredient_id=glycerin_id,
                canonical_name="Glycerin",
                match_type="canonical",
            ),
            IngredientMatch(
                position=1,
                original_name="Water",
                normalized_name="water",
                status=ResolutionStatus.AMBIGUOUS,
                candidate_names=["Aqua", "Other Water"],
            ),
            IngredientMatch(
                position=2,
                original_name="Mystery Compound",
                normalized_name="mystery compound",
                status=ResolutionStatus.UNRECOGNIZED,
            ),
        ],
    )
    retrieved = RetrievedEvidence(
        chunk_id=uuid4(),
        source_id=uuid4(),
        source_key="MOCK_SOURCE",
        document_id=uuid4(),
        ingredient_id=glycerin_id,
        ingredient_name="Glycerin",
        relevance_score=0.9,
        distance=0.1,
        excerpt="Glycerin is a humectant.",
        original_url="https://example.org/glycerin",
        document_title="Glycerin",
        source_version="v1",
    )

    monkeypatch.setattr(
        analysis_workflow_service,
        "normalize_submission",
        lambda db, requested_id: normalization,
    )

    def retrieve(*, db, ingredient_name, top_k):
        calls.append(ingredient_name)
        return IngredientRetrievalResult(
            ingredient=ingredient_name,
            normalized_ingredient=ingredient_name.casefold(),
            status="found",
            evidence=[retrieved],
        )

    monkeypatch.setattr(
        analysis_workflow_service,
        "retrieve_ingredient_evidence",
        retrieve,
    )

    evidence, evidence_map, actual_normalization = (
        analysis_workflow_service._retrieve_submission_evidence(
            object(),
            submission_id,
        )
    )

    assert calls == ["Glycerin"]
    assert evidence == [retrieved]
    assert set(evidence_map) == {"glycerin"}
    assert actual_normalization is normalization


def test_retrieved_evidence_for_wrong_ingredient_is_excluded(monkeypatch):
    submission_id = uuid4()
    ingredient_id = uuid4()
    wrong_ingredient_id = uuid4()
    normalization = NormalizationResult(
        submission_id=submission_id,
        original_text="Glycerin",
        ingredients=[
            IngredientMatch(
                position=0,
                original_name="Glycerin",
                normalized_name="glycerin",
                status=ResolutionStatus.RESOLVED,
                ingredient_id=ingredient_id,
                canonical_name="Glycerin",
                match_type="canonical",
            )
        ],
    )
    mismatched_evidence = RetrievedEvidence(
        chunk_id=uuid4(),
        source_id=uuid4(),
        source_key="MOCK_SOURCE",
        document_id=uuid4(),
        ingredient_id=wrong_ingredient_id,
        ingredient_name="Other Ingredient",
        relevance_score=0.9,
        distance=0.1,
        excerpt="Evidence for another ingredient.",
        original_url="https://example.org/evidence",
        document_title="Evidence",
        source_version="v1",
    )

    monkeypatch.setattr(
        analysis_workflow_service,
        "normalize_submission",
        lambda db, requested_id: normalization,
    )
    monkeypatch.setattr(
        analysis_workflow_service,
        "retrieve_ingredient_evidence",
        lambda **kwargs: IngredientRetrievalResult(
            ingredient="Glycerin",
            normalized_ingredient="glycerin",
            status="found",
            evidence=[mismatched_evidence],
        ),
    )

    evidence, evidence_by_ingredient, _ = (
        analysis_workflow_service._retrieve_submission_evidence(
            object(),
            submission_id,
        )
    )

    assert evidence == []
    assert evidence_by_ingredient == {"glycerin": []}


def test_evidence_coverage_distinguishes_partial_and_unavailable():
    normalization = NormalizationResult(
        submission_id=uuid4(),
        original_text="Aqua, Glycerin",
        ingredients=[
            IngredientMatch(
                position=0,
                original_name="Aqua",
                normalized_name="aqua",
                status=ResolutionStatus.RESOLVED,
                ingredient_id=uuid4(),
                canonical_name="Aqua",
                match_type="canonical",
            ),
            IngredientMatch(
                position=1,
                original_name="Glycerin",
                normalized_name="glycerin",
                status=ResolutionStatus.RESOLVED,
                ingredient_id=uuid4(),
                canonical_name="Glycerin",
                match_type="canonical",
            ),
            IngredientMatch(
                position=2,
                original_name="Water",
                normalized_name="water",
                status=ResolutionStatus.AMBIGUOUS,
                candidate_names=["Aqua", "Water"],
            ),
        ],
    )

    def result(supported_names):
        return GeminiAnalysisOutput.model_validate(
            {
                "overall_assessment": "low_concern",
                "evidence_status": "limited",
                "evidence_ids": [],
                "summary": "Limited findings.",
                "ingredients": [
                    {
                        "name": name,
                        "function": "Function",
                        "concern_level": "low",
                        "explanation": "Limited explanation.",
                        "support_status": (
                            "supported"
                            if name in supported_names
                            else "limited"
                        ),
                        "evidence_ids": (
                            [f"chunk-{name}"]
                            if name in supported_names
                            else []
                        ),
                    }
                    for name in ("Aqua", "Glycerin")
                ],
                "cautions": [],
                "uncertainties": [],
            }
        )

    retrieved_ids = {
        "aqua": ["chunk-Aqua"],
        "glycerin": ["chunk-Glycerin"],
    }

    assert analysis_workflow_service._evidence_coverage(
        normalization,
        retrieved_ids,
        result({"Glycerin"}),
    ) == "partial"

    assert analysis_workflow_service._evidence_coverage(
        normalization,
        retrieved_ids,
        result(set()),
    ) == "unavailable"

    assert analysis_workflow_service._evidence_coverage(
        normalization,
        retrieved_ids,
        result({"Aqua", "Glycerin"}),
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
