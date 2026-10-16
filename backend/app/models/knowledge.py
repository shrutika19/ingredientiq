
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime,
    ForeignKey, ForeignKeyConstraint, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    source_key: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    organization: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    original_url: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    quality_tier: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    license: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    full_text_storage_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    redistribution_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class IngredientIdentity(Base):
    __tablename__ = "ingredient_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    canonical_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    normalized_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )


class IngredientAlias(Base):
    __tablename__ = "ingredient_aliases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredient_identities.id"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    normalized_alias: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    __table_args__ = (
        UniqueConstraint(
            "ingredient_id", "normalized_alias",
            name="uq_ingredient_alias_identity_name",
        ),
    )


class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_sources.id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    original_url: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    source_version: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    publication_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
    )
    retrieved_date: Mapped[date] = mapped_column(
        Date, nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
    )
    license: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )
    __table_args__ = (
        UniqueConstraint(
            "source_id", "original_url",
            "source_version", "content_hash",
            name="uq_evidence_document_version",
        ),
        UniqueConstraint(
            "id", "source_id",
            name="uq_evidence_document_id_source",
        ),
    )


class EvidenceDocumentIngredient(Base):
    __tablename__ = "evidence_document_ingredients"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_documents.id"),
        primary_key=True,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredient_identities.id"),
        primary_key=True,
    )


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
    )
    location_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(768), nullable=True,
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "source_id"],
            ["evidence_documents.id",
             "evidence_documents.source_id"],
            name="fk_chunk_document_source",
        ),
        UniqueConstraint(
            "document_id", "chunk_index",
            name="uq_evidence_chunk_position",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_evidence_chunk_index",
        ),
        CheckConstraint(
            "(embedding IS NULL AND embedding_model IS NULL) "
            "OR (embedding IS NOT NULL AND embedding_model IS NOT NULL)",
            name="ck_evidence_chunk_embedding_model",
        ),
    )
