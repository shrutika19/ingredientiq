
from sqlalchemy import select

from app.database.session import SessionLocal
from app.knowledge.ingredients import INITIAL_INGREDIENTS
from app.models.knowledge import IngredientIdentity


def main():
    with SessionLocal.begin() as db:
        for name in INITIAL_INGREDIENTS:
            normalized = name.strip().casefold()

            existing = db.scalar(
                select(IngredientIdentity).where(
                    IngredientIdentity.normalized_name == normalized
                )
            )

            if existing:
                print(f"EXISTS: {name}")
                continue

            db.add(
                IngredientIdentity(
                    canonical_name=name,
                    normalized_name=normalized,
                    is_active=True,
                )
            )
            print(f"CREATED: {name}")

if __name__ == "__main__":
    main()
