import time

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import RateLimitExceededError


def _client_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_login_rate_limit(request: Request) -> None:
    settings = get_settings()
    key = _client_host(request)
    now = time.monotonic()
    window = float(settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)
    max_attempts = settings.LOGIN_RATE_LIMIT_ATTEMPTS

    timestamps = _LOGIN_ATTEMPTS.setdefault(key, [])
    cutoff = now - window
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)
    if len(timestamps) >= max_attempts:
        raise RateLimitExceededError("Too many login attempts. Try again later.")
    timestamps.append(now)


_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
