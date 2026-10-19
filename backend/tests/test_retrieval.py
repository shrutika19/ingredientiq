from uuid import uuid4

from app.knowledge.retrieval.service import (
    is_near_duplicate,
    normalize_claim,
    normalize_ingredient,
)


def test_ingredient_normalization():
    assert normalize_ingredient("  GLYCERIN  ") == "glycerin"


def test_claim_normalization():
    assert normalize_claim("  Skin   hydration  ") == "skin hydration"


def test_near_duplicate_same_source():
    source_id = uuid4()

    accepted = [
        (
            source_id,
            normalize_claim(
                "Glycerin helps maintain skin hydration."
            ),
        )
    ]

    assert is_near_duplicate(
        source_id,
        "Glycerin helps maintain skin hydration.",
        accepted,
    )


def test_same_claim_different_source_is_retained():
    accepted = [
        (
            uuid4(),
            normalize_claim("Glycerin supports hydration."),
        )
    ]

    assert not is_near_duplicate(
        uuid4(),
        "Glycerin supports hydration.",
        accepted,
    )