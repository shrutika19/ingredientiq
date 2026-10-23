import logging
import time
from contextvars import ContextVar
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


request_id_context: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)

logger = logging.getLogger(__name__)


def _request_id_from_scope(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name.lower() == b"x-request-id" and len(value) <= 128:
            try:
                return str(UUID(value.decode("ascii")))
            except (UnicodeDecodeError, ValueError):
                break
    return str(uuid4())


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id_from_scope(scope)
        context_token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            logger.info(
                "http_request_completed",
                extra={
                    "request_id": request_id,
                    "structured_fields": {
                        "http_method": scope["method"],
                        "http_path": scope["path"],
                        "http_status_code": status_code,
                        "duration_ms": round(
                            (time.perf_counter() - started_at) * 1000,
                            2,
                        ),
                    }
                },
            )
            request_id_context.reset(context_token)
