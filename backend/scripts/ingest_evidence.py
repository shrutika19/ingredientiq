
import argparse
import json
import logging
from collections import Counter
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import SessionLocal
from app.knowledge.ingestion.audit import write_audit_record
from app.knowledge.ingestion.schemas import SeedDocument
from app.knowledge.ingestion.service import (
    IngestionRejected,
    ingest_document,
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=Path("ingestion_logs/evidence.jsonl"),
    )
    args = parser.parse_args()

    payload = json.loads(
        args.file.read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict) or not isinstance(
        payload.get("documents"), list
    ):
        raise ValueError(
            "Dataset must contain a documents array"
        )

    run_id = str(uuid4())
    counts = Counter()
    seen = set()

    for index, raw in enumerate(payload["documents"]):
        status = "rejected"
        reason = ""
        document_id = None

        try:
            item = SeedDocument.model_validate(raw)

            key = (
                item.source_key,
                str(item.original_url),
                item.source_version,
            )

            if key in seen:
                raise IngestionRejected(
                    "Duplicate document entry in dataset"
                )

            seen.add(key)

            with SessionLocal() as db:
                with db.begin():
                    result = ingest_document(db, item)

            status = result.status
            reason = result.reason
            document_id = result.document_id

        except (
            ValidationError,
            IngestionRejected,
            SQLAlchemyError,
            ValueError,
        ) as exc:
            reason = str(exc)
            logger.warning(
                "Rejected dataset entry %s: %s",
                index, reason,
            )

        counts[status] += 1

        write_audit_record(
            args.audit_log,
            {
                "run_id": run_id,
                "entry_index": index,
                "status": status,
                "reason": reason,
                "document_id": (
                    str(document_id) if document_id else None
                ),
            },
        )

    summary = {
        "run_id": run_id,
        "ingested": counts["ingested"],
        "skipped": counts["skipped"],
        "rejected": counts["rejected"],
    }

    print(json.dumps(summary, indent=2))

    if counts["rejected"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
