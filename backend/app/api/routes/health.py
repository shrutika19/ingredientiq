
import logging
from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.error import ErrorResponse


router = APIRouter(prefix="/health", tags=["Health"])

logger = logging.getLogger(__name__)


@lru_cache
def _migration_head_revision() -> str | None:
    alembic_ini = Path(__file__).resolve().parents[3] / "alembic.ini"
    config = Config(str(alembic_ini))
    return ScriptDirectory.from_config(config).get_current_head()


@router.get("")
def health_check():
    return {
        "status": "healthy",
        "service": "ingredientiq-api",
        "version": "1.0.0",
    }


@router.get(
    "/ready",
    responses={
        503: {
            "model": ErrorResponse,
            "description": "Database unavailable or migrations are pending",
        }
    },
)
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "DATABASE_UNAVAILABLE",
                "message": "Database readiness check failed.",
            },
        )

    try:
        current_revision = db.scalar(
            text("SELECT version_num FROM alembic_version")
        )
    except SQLAlchemyError:
        logger.exception("Database migration revision check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MIGRATIONS_NOT_AT_HEAD",
                "message": (
                    "Database migration state could not be verified."
                ),
            },
        )

    head_revision = _migration_head_revision()
    if current_revision != head_revision:
        logger.warning(
            "Database migrations are not at head: current=%s head=%s",
            current_revision,
            head_revision,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "MIGRATIONS_NOT_AT_HEAD",
                "message": (
                    "Database migrations are not up to date."
                ),
            },
        )

    return {
        "status": "ready",
        "database": "connected",
        "migrations": "current",
    }
