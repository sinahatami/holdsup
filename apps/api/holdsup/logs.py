"""JSON logs with a request ID that follows a check from the browser to the backend.

The web app sends `X-Request-ID`; the API keeps it (or makes one), binds it to every log line
written while handling the request, including the check's background task (asyncio copies
context variables into tasks), and returns it in the response header. Library logs from the
standard `logging` module go through the same JSON renderer.
"""

import logging
import re
import sys
from uuid import uuid4

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HEADER = "x-request-id"
_VALID = re.compile(r"[A-Za-z0-9._-]{1,64}")
# A Telegram Bot API address holds the bot's token: https://api.telegram.org/bot<token>/<method>
_BOT_TOKEN = re.compile(r"bot\d+:[A-Za-z0-9_-]+")
REDACTED = "bot<redacted>"


class RedactBotTokens(logging.Filter):
    """Blanks Telegram bot tokens in every log line: httpx logs each request's address at
    INFO, and a Bot API address holds the token. Never drops a line."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            message = record.getMessage()
            redacted = _BOT_TOKEN.sub(REDACTED, message)
            if redacted != message:
                record.msg, record.args = redacted, None
        elif isinstance(record.msg, dict):  # a structlog event
            for key, value in record.msg.items():
                if isinstance(value, str) and _BOT_TOKEN.search(value):
                    record.msg[key] = _BOT_TOKEN.sub(REDACTED, value)
        return True


def configure_logging(level: str = "INFO") -> None:
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RedactBotTokens())
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def request_id_from(value: str | None) -> str:
    """The caller's ID if it is a plain token, else a new one (never log arbitrary input)."""
    if value is not None and _VALID.fullmatch(value):
        return value
    return uuid4().hex


class RequestIdMiddleware:
    """Plain ASGI middleware, so streaming responses (SSE) pass through untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        raw = headers.get(HEADER.encode())
        request_id = request_id_from(raw.decode("latin-1") if raw else None)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    *message.get("headers", []),
                    (HEADER.encode(), request_id.encode()),
                ]
            await send(message)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            await self.app(scope, receive, send_with_id)
        finally:
            structlog.contextvars.clear_contextvars()
