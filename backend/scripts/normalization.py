import argparse
import json
from uuid import UUID

from app.database.session import SessionLocal
from app.knowledge.normalization.service import normalize_submission


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission-id", required=True)
    args = parser.parse_args()

    with SessionLocal() as db:
        result = normalize_submission(
            db,
            UUID(args.submission_id),
        )

    print(json.dumps(
        result.model_dump(mode="json"),
        indent=2,
    ))


if __name__ == "__main__":
    main()