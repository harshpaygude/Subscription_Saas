"""Structured JSON logging and request correlation ID middleware."""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_HEADER = "X-Request-ID"
_correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")

_SENSITIVE_KEYS = ("authorization", "password", "secret", "token", "api_key", "cookie")


def get_correlation_id() -> str:
    return _correlation_id_ctx.get()


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON without leaking secrets."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }
        corr_id = get_correlation_id()
        if corr_id:
            payload["request_id"] = corr_id
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            for key, value in extra_fields.items():
                if any(s in key.lower() for s in _SENSITIVE_KEYS):
                    payload[key] = "[redacted]"
                else:
                    payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(service_name: str, level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter(service_name))
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads or generates X-Request-ID and binds it to logging context."""

    def __init__(self, app, service_name: str = "unisora-service"):
        super().__init__(app)
        self.logger = get_logger(f"{service_name}.http")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        token = _correlation_id_ctx.set(req_id)
        try:
            response = await call_next(request)
            response.headers[CORRELATION_HEADER] = req_id
            self.logger.info(
                "request.completed",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                    }
                },
            )
            return response
        finally:
            _correlation_id_ctx.reset(token)
