
from dataclasses import dataclass
from datetime import date
from enum import Enum


UNVERIFIED_LICENSE_VALUES = frozenset(
    {
        "PERMISSION_REVIEW_REQUIRED",
        "TEST_ONLY",
        "VERIFIED_LICENSE_OR_PERMISSION_ID",
        "Not verified for proposed reuse",
        "Verify per opinion",
        "Varies by article",
    }
)
_UNVERIFIED_LICENSE_VALUES_NORMALIZED = frozenset(
    value.casefold() for value in UNVERIFIED_LICENSE_VALUES
)


def is_known_unverified_license(value: str) -> bool:
    return value.strip().casefold() in _UNVERIFIED_LICENSE_VALUES_NORMALIZED


class EvidenceTier(str, Enum):
    OFFICIAL = "official_regulatory_assessment"
    SCIENTIFIC = "scientific_review"
    SUPPORTING = "supporting_material"


class EvidenceType(str, Enum):
    INGREDIENT_REFERENCE = "ingredient_reference"
    SAFETY_OPINION = "safety_opinion"
    SCIENTIFIC_LITERATURE = "scientific_literature"


class ReuseStatus(str, Enum):
    VERIFIED = "verified"
    REVIEW_REQUIRED = "review_required"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class EvidenceSource:
    source_id: str
    title: str
    original_url: str
    organization: str
    publication_date: date | None
    retrieved_date: date | None
    license: str
    evidence_type: EvidenceType
    quality_tier: EvidenceTier
    reuse_status: ReuseStatus
    full_text_storage_allowed: bool
    redistribution_allowed: bool


EVIDENCE_SOURCES = (
    EvidenceSource(
        source_id="EU_COSING",
        title="Cosmetic Ingredient Database",
        original_url=(
            "https://single-market-economy.ec.europa.eu/"
            "sectors/cosmetics/cosmetic-ingredient-database_en"
        ),
        organization="European Commission",
        publication_date=None,
        retrieved_date=None,
        license="Not verified for proposed reuse",
        evidence_type=EvidenceType.INGREDIENT_REFERENCE,
        quality_tier=EvidenceTier.OFFICIAL,
        reuse_status=ReuseStatus.REVIEW_REQUIRED,
        full_text_storage_allowed=False,
        redistribution_allowed=False,
    ),
    EvidenceSource(
        source_id="EU_SCCS",
        title="SCCS Scientific Opinions",
        original_url=(
            "https://health.ec.europa.eu/"
            "scientific-committees/"
            "scientific-committee-consumer-safety-sccs/"
            "sccs-opinions_en"
        ),
        organization="European Commission SCCS",
        publication_date=None,
        retrieved_date=None,
        license="Verify per opinion",
        evidence_type=EvidenceType.SAFETY_OPINION,
        quality_tier=EvidenceTier.OFFICIAL,
        reuse_status=ReuseStatus.REVIEW_REQUIRED,
        full_text_storage_allowed=False,
        redistribution_allowed=False,
    ),
    EvidenceSource(
        source_id="EUROPE_PMC",
        title="Europe PMC Scientific Literature",
        original_url="https://europepmc.org/",
        organization="EMBL-EBI / Europe PMC",
        publication_date=None,
        retrieved_date=None,
        license="Varies by article",
        evidence_type=EvidenceType.SCIENTIFIC_LITERATURE,
        quality_tier=EvidenceTier.SCIENTIFIC,
        reuse_status=ReuseStatus.REVIEW_REQUIRED,
        full_text_storage_allowed=False,
        redistribution_allowed=False,
    ),
)


def get_evidence_sources() -> tuple[EvidenceSource, ...]:
    return EVIDENCE_SOURCES
