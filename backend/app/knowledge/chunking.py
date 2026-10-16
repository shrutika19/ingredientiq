
from dataclasses import dataclass

from app.knowledge.ingestion.normalizer import (
    content_hash,
    normalize_content,
)


@dataclass(frozen=True)
class ChunkData:
    index: int
    content: str
    content_hash: str
    location_reference: str | None


class ChunkingError(ValueError):
    pass


def chunk_document(
    content: str,
    *,
    location_reference: str | None = None,
    max_words: int = 180,
) -> list[ChunkData]:
    normalized = normalize_content(content)

    if not normalized:
        raise ChunkingError("Document content is empty")

    if max_words < 30:
        raise ChunkingError("max_words must be at least 30")

    paragraphs = [
        paragraph.strip()
        for paragraph in normalized.split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for paragraph in paragraphs:
        word_count = len(paragraph.split())

        # Never cut a paragraph containing a claim
        # and its context.
        if word_count > max_words:
            raise ChunkingError(
                "Paragraph exceeds chunk word limit. "
                "Curate or split at a validated claim boundary."
            )

        if current and current_words + word_count > max_words:
            chunks.append("\n\n".join(current))
            current = []
            current_words = 0

        current.append(paragraph)
        current_words += word_count

    if current:
        chunks.append("\n\n".join(current))

    return [
        ChunkData(
            index=index,
            content=text,
            content_hash=content_hash(text),
            location_reference=location_reference,
        )
        for index, text in enumerate(chunks)
    ]
