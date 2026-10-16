
from urllib.parse import urlparse

from app.knowledge.sources import (
    EvidenceType,
    get_evidence_sources,
)


def test_three_sources_are_registered():
    sources = get_evidence_sources()

    assert len(sources) == 3


def test_source_ids_are_unique():
    sources = get_evidence_sources()

    ids = [source.source_id for source in sources]

    assert len(ids) == len(set(ids))


def test_source_urls_use_https():
    for source in get_evidence_sources():
        parsed = urlparse(source.original_url)

        assert parsed.scheme == "https"
        assert parsed.hostname


def test_required_evidence_types_are_present():
    evidence_types = {
        source.evidence_type
        for source in get_evidence_sources()
    }

    assert evidence_types == {
        EvidenceType.INGREDIENT_REFERENCE,
        EvidenceType.SAFETY_OPINION,
        EvidenceType.SCIENTIFIC_LITERATURE,
    }
