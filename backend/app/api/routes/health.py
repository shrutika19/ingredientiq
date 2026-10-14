
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.dependencies import get_db


router = APIRouter(prefix="/health", tags=["Health"])

logger = logging.getLogger(__name__)


@router.get("")
def health_check():
    return {
        "status": "healthy",
        "service": "ingredientiq-api",
        "version": "1.0.0",
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "ready",
            "database": "connected",
        }

    except SQLAlchemyError:
        logger.exception("Database readiness check failed")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "unavailable",
            },
        )
