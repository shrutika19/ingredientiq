import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.request_logging import request_id_context


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(
                record,
                "request_id",
                request_id_context.get(),
            ),
        }

        structured_fields = getattr(record, "structured_fields", None)
        if isinstance(structured_fields, dict):
            payload.update(structured_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    formatter = JsonLogFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
