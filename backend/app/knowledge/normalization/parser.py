import re


def normalize_name(name: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        name.strip(),
    ).casefold()


def parse_ingredient_list(text: str) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Ingredient text cannot be empty")

    if len(text) > 20000:
        raise ValueError("Ingredient text is too long")

    # Commas are the MVP list delimiter.
    # Do not split on spaces, hyphens, or parentheses.
    items = [
        re.sub(r"\s+", " ", item).strip()
        for item in text.split(",")
    ]

    if any(not item for item in items):
        raise ValueError(
            "Ingredient list contains an empty comma-separated entry"
        )

    if len(items) > 100:
        raise ValueError("Too many ingredients")

    return items