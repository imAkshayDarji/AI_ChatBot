"""IP-keyed sliding-window rate limits shared by login, chat start, and leads."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass

from fastapi import Request

from app.core.config import Settings, get_settings
from app.core.errors import RateLimitExceededError

MAX_RATE_LIMIT_KEYS = 10_000

logger = logging.getLogger(__name__)


def _client_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@dataclass(frozen=True)
class IpRateLimitCheckResult:
    allowed: bool
    remaining: int
    reset_epoch: int


def _prune_window(timestamps: list[float], *, window_s: float, now: float) -> None:
    cutoff = now - window_s
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)


class IpSlidingWindowLimiter:
    """Sliding window limiter keyed by string (typically client IP). LRU key eviction."""

    def __init__(
        self,
        *,
        max_events: int,
        window_seconds: float,
        max_keys: int = MAX_RATE_LIMIT_KEYS,
    ) -> None:
        self._max = max_events
        self._window = window_seconds
        self._max_keys = max_keys
        self._buckets: OrderedDict[str, list[float]] = OrderedDict()

    def clear(self) -> None:
        self._buckets.clear()

    def check(self, key: str) -> IpRateLimitCheckResult:
        now = time.monotonic()
        if key not in self._buckets:
            while len(self._buckets) >= self._max_keys:
                self._buckets.popitem(last=False)
            self._buckets[key] = []
        else:
            self._buckets.move_to_end(key)

        bucket = self._buckets[key]
        _prune_window(bucket, window_s=self._window, now=now)
        reset_epoch = int(time.time()) + int(self._window)
        if len(bucket) >= self._max:
            _log_rate_limit_hit(kind="ip", key=key)
            return IpRateLimitCheckResult(False, 0, reset_epoch)
        bucket.append(now)
        remaining_after = max(0, self._max - len(bucket))
        return IpRateLimitCheckResult(True, remaining_after, reset_epoch)


def _log_rate_limit_hit(*, kind: str, key: str) -> None:
    preview = key if len(key) <= 128 else key[:125] + "..."
    logger.warning("rate_limit exceeded kind=%s key=%s", kind, preview)


_LOGIN_LIMITERS: dict[tuple[int, float], IpSlidingWindowLimiter] = {}


def _login_limiter_for(settings: Settings) -> IpSlidingWindowLimiter:
    spec = (
        settings.LOGIN_RATE_LIMIT_ATTEMPTS,
        float(settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS),
    )
    existing = _LOGIN_LIMITERS.get(spec)
    if existing is None:
        existing = IpSlidingWindowLimiter(
            max_events=spec[0],
            window_seconds=spec[1],
        )
        _LOGIN_LIMITERS[spec] = existing
    return existing


_CHAT_START_LIMITER = IpSlidingWindowLimiter(max_events=5, window_seconds=60.0)

_LEADS_LIMITER = IpSlidingWindowLimiter(max_events=3, window_seconds=60.0)


def _retry_after_from_reset(reset_epoch: int) -> int:
    return max(1, reset_epoch - int(time.time()))


def check_login_rate_limit(request: Request) -> None:
    settings = get_settings()
    limiter = _login_limiter_for(settings)
    key = _client_host(request)
    result = limiter.check(key)
    if not result.allowed:
        raise RateLimitExceededError(
            "Too many login attempts. Try again later.",
            retry_after_seconds=_retry_after_from_reset(result.reset_epoch),
            rate_limit_remaining=0,
            rate_limit_reset_epoch=result.reset_epoch,
        )


def check_chat_start_rate_limit(request: Request) -> IpRateLimitCheckResult:
    key = _client_host(request)
    result = _CHAT_START_LIMITER.check(key)
    if not result.allowed:
        raise RateLimitExceededError(
            "Too many new chat sessions from this network. Try again shortly.",
            retry_after_seconds=_retry_after_from_reset(result.reset_epoch),
            rate_limit_remaining=0,
            rate_limit_reset_epoch=result.reset_epoch,
        )
    return result


def check_leads_rate_limit(request: Request) -> IpRateLimitCheckResult:
    key = _client_host(request)
    result = _LEADS_LIMITER.check(key)
    if not result.allowed:
        raise RateLimitExceededError(
            "Too many lead submissions from this network. Try again shortly.",
            retry_after_seconds=_retry_after_from_reset(result.reset_epoch),
            rate_limit_remaining=0,
            rate_limit_reset_epoch=result.reset_epoch,
        )
    return result


def reset_ip_rate_limiters_for_tests() -> None:
    """Clear in-memory buckets; for tests only."""
    for bucket in list(_LOGIN_LIMITERS.values()):
        bucket.clear()
    _CHAT_START_LIMITER.clear()
    _LEADS_LIMITER.clear()
