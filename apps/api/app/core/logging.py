"""Logging setup, PII redaction helpers, and formatters."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any, Final

_EMAIL_RE: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
)

_PHONE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:\+\d{1,3}[-\s]?)?(?:\(?\d{3}\)?[-\s]?)\d{3}[-\s]?\d{4}\b",
)

_LOGRECORD_STANDARD_ATTRS: frozenset[str] = frozenset(vars(logging.makeLogRecord({})).keys())


def redact_pii(text: str) -> str:
    """Replace plausible emails and digit-group phone spans for safe logging."""
    if not text:
        return text
    redacted = _EMAIL_RE.sub("***@***.***", text)
    redacted = _PHONE_RE.sub("***-***-****", redacted)
    return redacted


def redact_pii_for_access_log(path: str) -> str:
    return redact_pii(path)


class RequestIdFilter(logging.Filter):
    """Inject request_id from contextvars into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        from app.core.context import request_id_ctx

        record.request_id = request_id_ctx.get("")  # type: ignore[attr-defined]
        return True


class DevTextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = record.getMessage()
        safe = redact_pii(original) if isinstance(original, str) else original
        record.msg = safe
        record.args = ()
        return super().format(record)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        iso_ts = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        extras: dict[str, Any] = {}
        for attr_name, value in record.__dict__.items():
            if attr_name in _LOGRECORD_STANDARD_ATTRS or attr_name.startswith("_"):
                continue
            if isinstance(value, str | int | float | bool | type(None)):
                extras[attr_name] = value

        message = redact_pii(record.getMessage())
        endpoint = extras.get("endpoint")
        if isinstance(endpoint, str):
            extras["endpoint"] = redact_pii_for_access_log(endpoint)

        payload: dict[str, Any] = {
            "timestamp": iso_ts,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            **extras,
        }

        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    level_name = settings.LOG_LEVEL.upper()
    resolved = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    if settings.ENVIRONMENT == "production":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            DevTextFormatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s"
            ),
        )
    handler.setLevel(resolved)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(resolved)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("krystal.access").setLevel(resolved)
