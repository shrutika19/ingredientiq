
from uuid import uuid4

import pytest

from app.knowledge.ingestion.schemas import SeedDocument
from app.knowledge.normalization.parser import parse_ingredient_list
from app.knowledge.retrieval.schemas import RetrievedEvidence
from app.services.skincare_analysis_service import (
    build_evidence_context_records,
    MAX_EVIDENCE_SNIPPETS,
    MAX_EVIDENCE_EXCERPT_CHARACTERS,
)
from app.services.analysis_workflow_service import (
    _evidence_reference_snapshots,
)
from app.schemas.analysis import GeminiAnalysisOutput


def make_evidence():
    return RetrievedEvidence(
        chunk_id=uuid4(),
        source_id=uuid4(),
        source_key="APPROVED_SKINCARE_001",
        document_id=uuid4(),
        ingredient_id=uuid4(),
        ingredient_name="Glycerin",
        relevance_score=0.92,
        distance=0.08,
        excerpt="Glycerin is used as a humectant.",
        content_hash="a" * 64,
        original_url="https://example.org/source",
        document_title="Reviewed ingredient source",
        source_version="v1-reviewed",
    )


def test_parser_preserves_multiword_names():
    assert parse_ingredient_list(
        "Glycerin, Sodium Hyaluronate"
    ) == ["Glycerin", "Sodium Hyaluronate"]


def test_model_context_is_bounded():
    evidence = [make_evidence() for _ in range(12)]

    records = build_evidence_context_records(evidence)

    assert len(records) == MAX_EVIDENCE_SNIPPETS
    assert all(
        len(record["excerpt"])
        <= MAX_EVIDENCE_EXCERPT_CHARACTERS
        for record in records
    )


def test_model_context_preserves_source_metadata():
    evidence = make_evidence()
    record = build_evidence_context_records([evidence])[0]

    assert record["evidence_id"] == str(evidence.chunk_id)
    assert record["source_id"] == str(evidence.source_id)
    assert record["document_id"] == str(evidence.document_id)
    assert record["document_version"] == evidence.source_version
    assert record["content_hash"] == evidence.content_hash


def test_evidence_document_requires_ingredient():
    with pytest.raises(ValueError):
        SeedDocument(
            source_key="APPROVED_SKINCARE_001",
            title="Test",
            original_url="https://example.org/test",
            source_version="v1",
            retrieved_date="2026-10-22",
            license="VERIFIED_LICENSE",
            evidence_type="scientific_literature",
            content="Example content",
            ingredient_names=[],
        )


def test_placeholder_evidence_metadata_is_rejected():
    with pytest.raises(ValueError, match="unresolved placeholder"):
        SeedDocument(
            source_key="APPROVED_SKINCARE_001",
            title="VERIFIED DOCUMENT TITLE",
            original_url="https://example.org/replace-with-real-source",
            source_version="v1-reviewed",
            retrieved_date="2026-10-22",
            license="VERIFIED_LICENSE_OR_PERMISSION_ID",
            evidence_type="scientific_literature",
            content="REPLACE WITH A PERMITTED, VERIFIED SOURCE EXCERPT.",
            ingredient_names=["Glycerin"],
        )
