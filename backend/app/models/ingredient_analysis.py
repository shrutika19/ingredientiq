
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngredientAnalysis(Base):
    __tablename__ = "ingredient_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "ingredient_submissions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(
            AnalysisStatus,
            name="analysis_status",
        ),
        nullable=False,
        default=AnalysisStatus.PENDING,
        server_default="PENDING",
    )

    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    model_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    prompt_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    failure_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index(
            "ix_ingredient_analyses_submission_created",
            "submission_id",
            "created_at",
        ),
        Index(
            "ix_ingredient_analyses_status",
            "status",
        ),
        CheckConstraint(
            """
            status != 'COMPLETED'
            OR (result IS NOT NULL AND completed_at IS NOT NULL)
            """,
            name="ck_analysis_completed_result",
        ),
        CheckConstraint(
            """
            status != 'FAILED'
            OR failure_code IS NOT NULL
            """,
            name="ck_analysis_failed_code",
        ),
    )
