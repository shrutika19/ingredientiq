from sqlalchemy import select
from sqlalchemy.orm import Session

from app.knowledge.normalization.parser import normalize_name
from app.knowledge.normalization.schemas import (
    IngredientMatch,
    ResolutionStatus,
)
from app.models.knowledge import (
    IngredientAlias,
    IngredientIdentity,
)


def resolve_name(
    db: Session,
    name: str,
    position: int,
) -> IngredientMatch:
    normalized = normalize_name(name)

    canonical_matches = db.scalars(
        select(IngredientIdentity).where(
            IngredientIdentity.normalized_name == normalized,
            IngredientIdentity.is_active.is_(True),
        )
    ).all()

    alias_matches = db.scalars(
        select(IngredientIdentity)
        .join(
            IngredientAlias,
            IngredientAlias.ingredient_id == IngredientIdentity.id,
        )
        .where(
            IngredientAlias.normalized_alias == normalized,
            IngredientIdentity.is_active.is_(True),
        )
    ).all()

    # Collect unique identities from BOTH canonical and alias matches.
    # This catches collisions rather than silently preferring one.
    identities = {
        identity.id: identity
        for identity in canonical_matches + alias_matches
    }

    if not identities:
        return IngredientMatch(
            position=position,
            original_name=name,
            normalized_name=normalized,
            status=ResolutionStatus.UNRECOGNIZED,
        )

    if len(identities) > 1:
        return IngredientMatch(
            position=position,
            original_name=name,
            normalized_name=normalized,
            status=ResolutionStatus.AMBIGUOUS,
            candidate_names=sorted(
                identity.canonical_name
                for identity in identities.values()
            ),
        )

    identity = next(iter(identities.values()))

    is_canonical = any(
        item.id == identity.id
        for item in canonical_matches
    )

    return IngredientMatch(
        position=position,
        original_name=name,
        normalized_name=normalized,
        status=ResolutionStatus.RESOLVED,
        ingredient_id=identity.id,
        canonical_name=identity.canonical_name,
        match_type=(
            "canonical" if is_canonical else "alias"
        ),
    )