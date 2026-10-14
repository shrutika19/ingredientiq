
from app.services.skincare_analysis_service import (
    analyze_skincare_ingredients,
)


def main():
    ingredient_text = (
        "Aqua, Glycerin, Niacinamide, "
        "Salicylic Acid, Fragrance"
    )

    analysis = analyze_skincare_ingredients(
        ingredient_text
    )

    print(
        analysis.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()
