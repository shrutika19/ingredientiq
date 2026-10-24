from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ApiClientUsage(Base):
    __tablename__ = "api_client_usage"

    client_key: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    minute_bucket: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    minute_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    daily_bucket: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    daily_analysis_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    daily_submission_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    daily_image_extraction_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
