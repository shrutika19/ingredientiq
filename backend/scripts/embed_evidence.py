
import argparse
import json
import logging
from collections import Counter

from google.genai.errors import ClientError, ServerError
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.knowledge.embedding.client import (
    EmbeddingError,
    GeminiEmbeddingClient,
)
from app.knowledge.embedding.service import process_chunk
from app.models.knowledge import (
    EvidenceChunk,
    EvidenceDocument,
    KnowledgeSource,
)


logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Generate embeddings for eligible evidence chunks."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum chunks to process (default: 20)",
    )

    parser.add_argument(
        "--include-test-source",
        action="store_true",
        help="Process only TEST_SOURCE chunks in development/testing",
    )

    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be positive")

    if args.include_test_source and settings.APP_ENV not in (
        "development",
        "testing",
    ):
        parser.error(
            "--include-test-source is forbidden outside "
            "development/testing"
        )

    counts = Counter()

    # STEP 1: Fetch eligible chunk IDs.
    try:
        with SessionLocal() as db:
            query = (
                select(EvidenceChunk.id)
                .join(
                    EvidenceDocument,
                    EvidenceChunk.document_id == EvidenceDocument.id,
                )
                .join(
                    KnowledgeSource,
                    EvidenceDocument.source_id == KnowledgeSource.id,
                )
                .where(
                    EvidenceChunk.is_active.is_(True),
                    EvidenceDocument.is_active.is_(True),
                    KnowledgeSource.is_active.is_(True),
                    KnowledgeSource.full_text_storage_allowed.is_(True),
                    or_(
                        EvidenceChunk.embedding.is_(None),
                        EvidenceChunk.embedding_model
                        != settings.EMBEDDING_MODEL,
                    ),
                )
            )

            if args.include_test_source:
                query = query.where(
                    KnowledgeSource.source_key == "TEST_SOURCE"
                )
            else:
                query = query.where(
                    KnowledgeSource.source_key != "TEST_SOURCE",
                    KnowledgeSource.license
                    != "PERMISSION_REVIEW_REQUIRED",
                )

            query = (
                query.order_by(
                    EvidenceChunk.document_id,
                    EvidenceChunk.chunk_index,
                )
                .limit(args.limit)
            )

            chunk_ids = list(db.scalars(query).all())

    except SQLAlchemyError:
        logger.exception("Failed to fetch evidence chunks")
        raise SystemExit(1)

    logger.info(
        "Found %s eligible evidence chunks",
        len(chunk_ids),
    )

    if not chunk_ids:
        logger.info("No eligible chunks found for embedding")

        print(
            json.dumps(
                {
                    "embedded": 0,
                    "skipped": 0,
                    "failed": 0,
                },
                indent=2,
            )
        )
        return

    # STEP 2: Initialize embedding client.
    try:
        client = GeminiEmbeddingClient()
    except (EmbeddingError, ValueError) as exc:
        logger.error(
            "Failed to initialize embedding client: %s",
            exc,
        )
        raise SystemExit(1)

    # STEP 3: Process each chunk in its own transaction.
    for chunk_id in chunk_ids:
        try:
            with SessionLocal() as db:
                with db.begin():
                    result = process_chunk(
                        db,
                        chunk_id,
                        client,
                        allow_test_source=args.include_test_source,
                    )

            counts[result.status] += 1

            logger.info(
                "Chunk %s: %s",
                chunk_id,
                result.status,
            )

        except ClientError as exc:
            counts["failed"] += 1

            logger.error(
                "Gemini client error for chunk %s: %s",
                chunk_id,
                exc,
            )

            if exc.code == 429:
                logger.error(
                    "Embedding quota exceeded; stopping batch"
                )
                break

        except (
            ServerError,
            EmbeddingError,
            ValueError,
            SQLAlchemyError,
        ) as exc:
            counts["failed"] += 1

            logger.error(
                "Embedding failed for chunk %s: %s",
                chunk_id,
                exc,
            )

        except Exception:
            counts["failed"] += 1
            logger.exception(
                "Unexpected error while embedding chunk %s",
                chunk_id,
            )

    # STEP 4: Print batch summary.
    summary = {
        "embedded": counts["embedded"],
        "skipped": counts["skipped"],
        "failed": counts["failed"],
    }

    print(json.dumps(summary, indent=2))

    if counts["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
