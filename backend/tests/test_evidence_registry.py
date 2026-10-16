
from app.knowledge.ingredients import INITIAL_INGREDIENTS
from app.knowledge.sources import (
    EVIDENCE_SOURCES,
    EvidenceTier,
    ReuseStatus,
)


def test_source_count():
    assert len(EVIDENCE_SOURCES) == 3


def test_source_metadata():
    for source in EVIDENCE_SOURCES:
        assert source.source_id
        assert source.title
        assert source.organization
        assert source.original_url.startswith("https://")
        assert source.license
        assert source.evidence_type
        assert source.quality_tier


def test_unique_source_ids():
    ids = [source.source_id for source in EVIDENCE_SOURCES]
    assert len(ids) == len(set(ids))


def test_unverified_sources_are_not_ingestable():
    for source in EVIDENCE_SOURCES:
        if source.reuse_status != ReuseStatus.VERIFIED:
            assert not source.full_text_storage_allowed
            assert not source.redistribution_allowed


def test_source_quality_tiers():
    assert EVIDENCE_SOURCES[0].quality_tier == EvidenceTier.OFFICIAL
    assert EVIDENCE_SOURCES[1].quality_tier == EvidenceTier.OFFICIAL
    assert EVIDENCE_SOURCES[2].quality_tier == EvidenceTier.SCIENTIFIC


def test_initial_ingredient_dataset():
    assert 20 <= len(INITIAL_INGREDIENTS) <= 30
    assert len(INITIAL_INGREDIENTS) == len(
        {name.casefold() for name in INITIAL_INGREDIENTS}
    )
