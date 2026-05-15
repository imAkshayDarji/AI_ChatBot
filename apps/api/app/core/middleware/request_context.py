"""Request ID propagation and bounded access logging."""

from __future__ import annotations

import logging
import os
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.context import request_id_ctx
from app.core.logging import redact_pii_for_access_log

ACCESS_LOGGER_NAME = "krystal.access"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        header_id = request.headers.get("x-request-id")
        request_id = header_id.strip() if header_id and header_id.strip() else str(uuid.uuid4())
        request.state.request_id = request_id
        request_id_ctx.set(request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        settings = get_settings()
        if os.environ.get("PYTEST_CURRENT_TEST") is not None:
            return await call_next(request)

        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", "")
        endpoint = redact_pii_for_access_log(request.url.path)

        logger = logging.getLogger(ACCESS_LOGGER_NAME)
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            if settings.ENVIRONMENT == "production":
                logger.warning(
                    "request_error",
                    extra={
                        "request_id": request_id,
                        "endpoint": endpoint,
                        "status_code": 500,
                        "latency_ms": duration_ms,
                        "error_type": type(exc).__name__,
                        "msg_type": "unhandled_exception",
                    },
                )
            else:
                logger.exception(
                    "request_failed",
                    extra={
                        "request_id": request_id,
                        "endpoint": endpoint,
                        "latency_ms": duration_ms,
                        "error_type": type(exc).__name__,
                    },
                )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        if settings.ENVIRONMENT == "production":
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "latency_ms": duration_ms,
                    "msg_type": "ok",
                },
            )
        else:
            logger.info(
                "%s %s %s %sms",
                request_id,
                endpoint,
                response.status_code,
                duration_ms,
            )
        return response
