from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.knowledge.ingestion.schemas import SeedDocument
from app.knowledge.ingestion.service import (
    IngestionRejected,
    ingest_document,
)
from app.knowledge.ingestion.normalizer import (
    content_hash,
    normalize_content,
)
from app.models.knowledge import (
    EvidenceChunk,
    EvidenceDocument,
    EvidenceDocumentIngredient,
)


class EmptyResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, source, existing=None, chunk_count=None):
        self._scalar_results = [source, existing, chunk_count]
        self._scalars_results = [
            [
                SimpleNamespace(
                    id=uuid4(),
                    normalized_name="glycerin",
                )
            ],
            [],
        ]
        self.added = []

    def scalar(self, statement):
        return self._scalar_results.pop(0)

    def scalars(self, statement):
        return EmptyResult(self._scalars_results.pop(0))

    def add(self, instance):
        self.added.append(instance)

    def flush(self):
        pass


def make_source(
    *,
    full_text_storage_allowed=False,
    license="Not verified for proposed reuse",
):
    return SimpleNamespace(
        id=uuid4(),
        source_key="EU_COSING",
        is_active=True,
        full_text_storage_allowed=full_text_storage_allowed,
        license=license,
    )


def make_item(
    *,
    content=None,
    license="Not verified for proposed reuse",
):
    return SeedDocument(
        source_key="EU_COSING",
        title="Glycerin — Cosmetic Ingredient Reference",
        original_url=(
            "https://single-market-economy.ec.europa.eu/"
            "sectors/cosmetics/cosmetic-ingredient-database_en"
        ),
        source_version="2026-10-16-metadata",
        publication_date=None,
        retrieved_date=date(2026, 10, 16),
        license=license,
        evidence_type="ingredient_reference",
        content=content,
        ingredient_names=["glycerin"],
    )


def test_metadata_only_document_is_ingested_without_content_chunks():
    db = FakeSession(make_source())

    result = ingest_document(db, make_item())

    assert result.status == "ingested"
    document = next(
        item for item in db.added
        if isinstance(item, EvidenceDocument)
    )
    assert document.content_hash is None
    assert not any(
        isinstance(item, EvidenceChunk)
        for item in db.added
    )
    assert any(
        isinstance(item, EvidenceDocumentIngredient)
        for item in db.added
    )


def test_unchanged_metadata_only_document_is_skipped_without_chunks():
    existing = SimpleNamespace(
        id=uuid4(),
        content_hash=None,
    )
    db = FakeSession(
        make_source(),
        existing=existing,
        chunk_count=0,
    )

    result = ingest_document(db, make_item())

    assert result.status == "skipped"
    assert result.document_id == existing.id


def test_unapproved_source_rejects_content_storage():
    db = FakeSession(make_source())

    with pytest.raises(
        IngestionRejected,
        match="not approved for content storage",
    ):
        ingest_document(db, make_item(content="Glycerin evidence text"))

    assert db.added == []


def test_approved_source_requires_document_content():
    db = FakeSession(make_source(full_text_storage_allowed=True))

    with pytest.raises(
        IngestionRejected,
        match="Content is required",
    ):
        ingest_document(db, make_item())

    assert db.added == []


def test_unverified_license_rejects_content_even_if_storage_is_enabled():
    license = "PERMISSION_REVIEW_REQUIRED"
    db = FakeSession(
        make_source(
            full_text_storage_allowed=True,
            license=license,
        )
    )

    with pytest.raises(
        IngestionRejected,
        match="Cannot store content while source permission is unverified",
    ):
        ingest_document(
            db,
            make_item(
                content="Glycerin evidence text",
                license=license,
            ),
        )

    assert db.added == []


def test_existing_document_with_incomplete_chunks_is_rejected():
    item = make_item(content="Glycerin evidence text")
    existing = SimpleNamespace(
        id=uuid4(),
        content_hash="",
    )
    existing.content_hash = content_hash(normalize_content(item.content))
    db = FakeSession(
        make_source(full_text_storage_allowed=True),
        existing=existing,
        chunk_count=0,
    )

    with pytest.raises(
        IngestionRejected,
        match="Existing document has incomplete chunks",
    ):
        ingest_document(db, item)
