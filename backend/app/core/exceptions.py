
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    detail = exc.detail
    if isinstance(detail, dict):
        error = detail.get("error")
        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message")
        elif isinstance(error, str):
            code = error
            message = detail.get("message")
        else:
            code = detail.get("code")
            message = detail.get("message")
    else:
        code = None
        message = detail if isinstance(detail, str) else None

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code if isinstance(code, str) else "HTTP_ERROR",
                "message": (
                    message
                    if isinstance(message, str)
                    else "The request could not be completed."
                ),
            }
        },
        headers=exc.headers,
    )


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
