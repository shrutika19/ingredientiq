from types import SimpleNamespace

from app.schemas.analysis import GeminiAnalysisOutput
from app.services import skincare_analysis_service


def test_analysis_uses_json_schema_response_config(monkeypatch):
    response_data = {
        "overall_assessment": "low_concern",
        "summary": "Mostly common moisturizing ingredients.",
        "ingredients": [
            {
                "name": "Glycerin",
                "function": "Humectant",
                "concern_level": "low",
                "explanation": "Helps retain moisture.",
            }
        ],
        "cautions": [],
        "uncertainties": [],
    }
    captured = {}

    class FakeModels:
        def generate_content(self, *, model, contents, config):
            captured["config"] = config
            return SimpleNamespace(
                text=GeminiAnalysisOutput(**response_data).model_dump_json()
            )

    class FakeClient:
        models = FakeModels()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        skincare_analysis_service,
        "get_settings",
        lambda: SimpleNamespace(GEMINI_MODEL="test-model"),
    )
    monkeypatch.setattr(
        skincare_analysis_service,
        "create_gemini_client",
        FakeClient,
    )

    result = skincare_analysis_service.analyze_skincare_ingredients(
        "Aqua, Glycerin"
    )

    assert result.overall_assessment == "low_concern"
    config = captured["config"]
    assert config.response_schema is None
    assert config.response_json_schema == (
        GeminiAnalysisOutput.model_json_schema()
    )
