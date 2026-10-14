
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid ingredient submission payload.",
            }
        },
    )


def database_exception_handler(
    request: Request,
    exc: SQLAlchemyError,
):
    logger.error(
        "Database operation failed",
        exc_info=True,
    )

    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "DATABASE_UNAVAILABLE",
                "message": "Database service is temporarily unavailable.",
            }
        },
    )


def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.error(
        "Unexpected application error",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            }
        },
    )
