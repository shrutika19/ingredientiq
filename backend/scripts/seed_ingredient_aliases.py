from sqlalchemy import select

from app.database.session import SessionLocal
from app.knowledge.ingredients import INITIAL_INGREDIENTS
from app.knowledge.normalization.parser import normalize_name
from app.models.knowledge import IngredientAlias, IngredientIdentity


ALIASES = {
    "Glycerin": ["Glycerine"],
    "Aqua": ["Water"],
    "Niacinamide": ["Vitamin B3"],
    "Tocopherol": ["Vitamin E"],
    "Panthenol": ["Provitamin B5"],
}


def main():
    initial_ingredients = {
        normalize_name(name): name
        for name in INITIAL_INGREDIENTS
    }

    with SessionLocal.begin() as db:
        for canonical_name, aliases in ALIASES.items():
            normalized_canonical = normalize_name(canonical_name)
            identity = db.scalar(
                select(IngredientIdentity).where(
                    IngredientIdentity.normalized_name
                    == normalized_canonical,
                )
            )

            if identity is None:
                seeded_name = initial_ingredients.get(
                    normalized_canonical
                )
                if seeded_name is None:
                    raise ValueError(
                        "Canonical identity is not in the initial "
                        f"ingredient dataset: {canonical_name}"
                    )

                identity = IngredientIdentity(
                    canonical_name=seeded_name,
                    normalized_name=normalized_canonical,
                    is_active=True,
                )
                db.add(identity)
                db.flush()

            elif not identity.is_active:
                raise ValueError(
                    f"Inactive canonical identity: {canonical_name}"
                )

            for alias in aliases:
                normalized = normalize_name(alias)

                existing = db.scalars(
                    select(IngredientAlias).where(
                        IngredientAlias.normalized_alias == normalized
                    )
                ).all()

                if any(
                    item.ingredient_id == identity.id
                    for item in existing
                ):
                    continue

                if existing:
                    raise ValueError(
                        f"Alias collision requires review: {alias}"
                    )

                canonical_collision = db.scalar(
                    select(IngredientIdentity).where(
                        IngredientIdentity.normalized_name == normalized
                    )
                )

                if (
                    canonical_collision is not None
                    and canonical_collision.id != identity.id
                ):
                    raise ValueError(
                        f"Canonical name collision: {alias}"
                    )

                db.add(
                    IngredientAlias(
                        ingredient_id=identity.id,
                        alias=alias,
                        normalized_alias=normalized,
                    )
                )

    print("Ingredient aliases seeded successfully")


if __name__ == "__main__":
    main()