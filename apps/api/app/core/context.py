"""Request-scoped context variables for correlation across services."""

from __future__ import annotations

import contextvars

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
