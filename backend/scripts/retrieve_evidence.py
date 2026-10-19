import argparse
import json

from app.database.session import SessionLocal
from app.knowledge.embedding.client import GeminiEmbeddingClient
from app.knowledge.retrieval.service import (
    retrieve_ingredient_evidence,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ingredient",
        default="glycerin",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        result = retrieve_ingredient_evidence(
            db=db,
            ingredient_name=args.ingredient,
            embedding_client=GeminiEmbeddingClient(),
        )

    print(
        json.dumps(
            result.model_dump(mode="json"),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()