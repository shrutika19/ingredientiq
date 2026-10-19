
from uuid import UUID

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.prompts.skincare_v1 import PROMPT_VERSION
from app.schemas.analysis import GeminiAnalysisOutput
from app.services.analysis_persistence_service import (
    create_analysis,
    mark_processing,
    mark_completed,
    mark_failed,
    get_analysis,
)


def main():
    settings = get_settings()

    submission_id = UUID(
        input("Enter existing submission UUID: ").strip()
    )

    with SessionLocal() as db:
        analysis = create_analysis(
            db=db,
            submission_id=submission_id,
            model_id=settings.GEMINI_MODEL,
            prompt_version=PROMPT_VERSION,
        )

        analysis_id = analysis.id
        print("Created analysis:", analysis_id)

        mark_processing(db, analysis_id)

        # Synthetic test result, not a real Gemini response.
        result = GeminiAnalysisOutput.model_validate({
            "overall_assessment": "low_concern",
            "evidence_status": "limited",
            "evidence_ids": [],
            "summary": "Example moisturizing ingredient.",
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
        })

        mark_completed(db, analysis_id, result)

        stored = get_analysis(db, analysis_id)

        print("Status:", stored.status.value)
        print("Stored result:", stored.result)


if __name__ == "__main__":
    main()
