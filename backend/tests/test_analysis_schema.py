
import pytest
from pydantic import ValidationError

from app.schemas.analysis import GeminiAnalysisOutput


@pytest.fixture
def valid_analysis():
    return {
        "overall_assessment": "low_concern",
        "evidence_status": "limited",
        "evidence_ids": [],
        "summary": "Mostly common moisturizing ingredients.",
        "ingredients": [
            {
                "name": "Glycerin",
                "function": "Humectant",
                "concern_level": "low",
                "explanation": "Helps retain moisture.",
                "support_status": "limited",
                "evidence_ids": [],
            }
        ],
        "cautions": [],
        "uncertainties": [],
    }


def test_valid_analysis(valid_analysis):
    result = GeminiAnalysisOutput.model_validate(
        valid_analysis
    )
    assert result.overall_assessment == "low_concern"


def test_whitespace_is_trimmed(valid_analysis):
    valid_analysis["ingredients"][0]["name"] = " Glycerin "
    valid_analysis["ingredients"][0]["supporting_quote"] = (
        "  verbatim quote  "
    )

    result = GeminiAnalysisOutput.model_validate(
        valid_analysis
    )

    assert result.ingredients[0].name == "Glycerin"
    assert result.ingredients[0].supporting_quote == "verbatim quote"


def test_supporting_quote_is_bounded(valid_analysis):
    valid_analysis["ingredients"][0]["supporting_quote"] = "q" * 501

    with pytest.raises(ValidationError):
        GeminiAnalysisOutput.model_validate(valid_analysis)


def test_duplicate_ingredients_rejected(valid_analysis):
    valid_analysis["ingredients"].append({
        "name": " glycerin ",
        "function": "Humectant",
        "concern_level": "low",
        "explanation": "Moisturizing ingredient.",
        "support_status": "limited",
        "evidence_ids": [],
    })

    with pytest.raises(ValidationError):
        GeminiAnalysisOutput.model_validate(valid_analysis)


def test_missing_cautions_rejected(valid_analysis):
    del valid_analysis["cautions"]

    with pytest.raises(ValidationError):
        GeminiAnalysisOutput.model_validate(valid_analysis)


def test_unknown_ingredient(valid_analysis):
    valid_analysis["ingredients"] = [{
        "name": "Unidentified Compound",
        "function": "Unknown",
        "concern_level": "unknown",
        "explanation": "Insufficient evidence is available.",
        "support_status": "limited",
        "evidence_ids": [],
    }]
    valid_analysis["overall_assessment"] = "insufficient_data"

    result = GeminiAnalysisOutput.model_validate(
        valid_analysis
    )

    assert result.ingredients[0].concern_level == "unknown"


@pytest.mark.parametrize(
    "explanation",
    [
        "No established cosmetic use or safety data are available.",
        "There is no widely documented function for this ingredient.",
        "This compound is not well characterized in available evidence.",
        "Its identity or available evidence cannot be established.",
    ],
)
def test_unknown_ingredient_accepts_evidence_limitation_phrasing(
    valid_analysis,
    explanation,
):
    valid_analysis["ingredients"] = [
        {
            "name": "XYZ-928-Unknown",
            "function": "Unknown",
            "concern_level": "unknown",
            "explanation": explanation,
            "support_status": "limited",
            "evidence_ids": [],
        }
    ]
    valid_analysis["overall_assessment"] = "insufficient_data"

    result = GeminiAnalysisOutput.model_validate(valid_analysis)

    assert result.ingredients[0].concern_level == "unknown"


def test_unknown_ingredient_rejects_explanation_without_uncertainty(
    valid_analysis,
):
    valid_analysis["ingredients"] = [
        {
            "name": "XYZ-928-Unknown",
            "function": "Unknown",
            "concern_level": "unknown",
            "explanation": "A moisturizing ingredient used in creams.",
            "support_status": "limited",
            "evidence_ids": [],
        }
    ]
    valid_analysis["overall_assessment"] = "insufficient_data"

    with pytest.raises(ValidationError):
        GeminiAnalysisOutput.model_validate(valid_analysis)


def test_extra_fields_rejected(valid_analysis):
    valid_analysis["score"] = 95

    with pytest.raises(ValidationError):
        GeminiAnalysisOutput.model_validate(valid_analysis)
