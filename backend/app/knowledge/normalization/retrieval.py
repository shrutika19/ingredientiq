from uuid import UUID

from sqlalchemy.orm import Session

from app.knowledge.normalization.schemas import ResolutionStatus
from app.knowledge.normalization.service import normalize_submission
from app.knowledge.retrieval.service import retrieve_ingredient_evidence


def retrieve_submission_evidence(
    db: Session,
    submission_id: UUID,
    embedding_client,
):
    normalized = normalize_submission(db, submission_id)

    results = []

    for ingredient in normalized.ingredients:
        if ingredient.status != ResolutionStatus.RESOLVED:
            results.append({
                "position": ingredient.position,
                "original_name": ingredient.original_name,
                "status": ingredient.status.value,
                "ingredient_id": None,
                "evidence": [],
            })
            continue

        result = retrieve_ingredient_evidence(
            db=db,
            ingredient_name=ingredient.canonical_name,
            embedding_client=embedding_client,
        )

        # Defense against accidentally attributing results
        # from another resolved identity.
        if any(
            item.ingredient_id != ingredient.ingredient_id
            for item in result.evidence
        ):
            raise ValueError(
                "Retrieved evidence ingredient identity mismatch"
            )

        results.append({
            "position": ingredient.position,
            "original_name": ingredient.original_name,
            "canonical_name": ingredient.canonical_name,
            "ingredient_id": str(ingredient.ingredient_id),
            "status": result.status,
            "evidence": [
                item.model_dump(mode="json")
                for item in result.evidence
            ],
        })

    return {
        "submission_id": str(submission_id),
        "original_text": normalized.original_text,
        "ingredients": results,
    }