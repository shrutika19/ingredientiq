import pytest

from app.knowledge.normalization.parser import (
    normalize_name,
    parse_ingredient_list,
)


def test_comma_separated_ingredients():
    result = parse_ingredient_list(
        "Aqua, Glycerin, Sodium Hyaluronate"
    )

    assert result == [
        "Aqua",
        "Glycerin",
        "Sodium Hyaluronate",
    ]


def test_multiword_inci_name():
    assert parse_ingredient_list(
        "Butyrospermum Parkii Butter"
    ) == ["Butyrospermum Parkii Butter"]


def test_case_and_whitespace():
    assert normalize_name(
        "  SODIUM   HYALURONATE  "
    ) == "sodium hyaluronate"


def test_empty_entry_rejected():
    with pytest.raises(ValueError):
        parse_ingredient_list("Aqua,,Glycerin")


def test_empty_input_rejected():
    with pytest.raises(ValueError):
        parse_ingredient_list("   ")