
import argparse
import json
import sys

from sqlalchemy import select

from app.database.session import SessionLocal
from app.knowledge.normalization.resolver import resolve_name
from app.knowledge.normalization.schemas import ResolutionStatus
from app.knowledge.retrieval.service import retrieve_ingredient_evidence
from app.models.knowledge import (
    EvidenceChunk,
    EvidenceDocument,
    IngredientIdentity,
    KnowledgeSource,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingredient", default="Glycerin")
    parser.add_argument("--require-evidence", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        match = resolve_name(db, args.ingredient, 0)

        if match.status != ResolutionStatus.RESOLVED:
            raise SystemExit(
                f"FAIL: ingredient resolution = {match.status}"
            )

        result = retrieve_ingredient_evidence(
            db=db,
            ingredient_name=match.canonical_name,
        )

        checks = {
            "ingredient_resolved": True,
            "retrieval_status": result.status,
            "evidence_count": len(result.evidence),
            "references": [],
        }

        for item in result.evidence:
            chunk = db.get(EvidenceChunk, item.chunk_id)
            document = db.get(
                EvidenceDocument, item.document_id
            )
            source = db.get(
                KnowledgeSource, item.source_id
            )

            assert chunk is not None
            assert document is not None
            assert source is not None

            assert item.ingredient_id == match.ingredient_id
            assert chunk.document_id == document.id
            assert document.source_id == source.id

            assert source.source_key != "TEST_SOURCE"
            assert source.license not in {
                "TEST_ONLY",
                "PERMISSION_REVIEW_REQUIRED",
            }
            assert source.full_text_storage_allowed
            assert chunk.embedding is not None
            assert chunk.is_active
            assert document.is_active
            assert source.is_active

            assert item.source_version == document.source_version
            assert item.content_hash == chunk.content_hash
            assert item.excerpt == chunk.content

            checks["references"].append({
                "chunk_id": str(item.chunk_id),
                "document_id": str(item.document_id),
                "source_id": str(item.source_id),
                "source_version": item.source_version,
                "content_hash": item.content_hash,
                "similarity": item.relevance_score,
            })

        print(json.dumps(checks, indent=2))

        if args.require_evidence and not result.evidence:
            raise SystemExit(
                "FAIL: no approved evidence was retrieved"
            )

        print("PASS: retrieval integrity checks completed")


if __name__ == "__main__":
    main()
