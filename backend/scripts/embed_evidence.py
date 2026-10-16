import argparse
import json
import logging
from collections import Counter

from google.genai.errors import ClientError, ServerError
from sqlalchemy import or_, select

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if args.limit < 1:
        parser.error("--limit must be positive")

    settings = get_settings()
    counts = Counter()

    with SessionLocal() as db:
        chunk_ids = db.scalars(
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
                KnowledgeSource.source_key != "TEST_SOURCE",
                or_(
                    EvidenceChunk.embedding.is_(None),
                    EvidenceChunk.embedding_model
                    != settings.EMBEDDING_MODEL,
                ),
            )
            .order_by(
                EvidenceChunk.document_id,
                EvidenceChunk.chunk_index,
            )
            .limit(args.limit)
        ).all()

    if chunk_ids:
        client = GeminiEmbeddingClient()

        for chunk_id in chunk_ids:
            try:
                with SessionLocal() as db:
                    with db.begin():
                        result = process_chunk(db, chunk_id, client)

                counts[result.status] += 1

            except ClientError as exc:
                counts["failed"] += 1
                logger.error(
                    "Gemini client error for chunk %s: %s",
                    chunk_id, exc,
                )

                if exc.code == 429:
                    logger.error(
                        "Embedding quota exceeded; stopping batch"
                    )
                    break

            except (ServerError, EmbeddingError, ValueError) as exc:
                counts["failed"] += 1
                logger.error(
                    "Embedding failed for chunk %s: %s",
                    chunk_id, exc,
                )

    print(json.dumps({
        "embedded": counts["embedded"],
        "skipped": counts["skipped"],
        "failed": counts["failed"],
    }, indent=2))

    if counts["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
