"""Per-session sliding-window limits for anonymous chat endpoints."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass

from app.core.rate_limit import MAX_RATE_LIMIT_KEYS

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_epoch: int


def _prune(timestamps: list[float], *, window_s: float, now: float) -> None:
    cutoff = now - window_s
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)


class SessionRateLimiter:
    """Sliding-window limit keyed by session_id; LRU eviction of bucket keys."""

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

    def check(self, key: str) -> RateLimitResult:
        now = time.monotonic()
        if key not in self._buckets:
            while len(self._buckets) >= self._max_keys:
                self._buckets.popitem(last=False)
            self._buckets[key] = []
        else:
            self._buckets.move_to_end(key)

        bucket = self._buckets[key]
        _prune(bucket, window_s=self._window, now=now)
        reset_epoch = int(time.time()) + int(self._window)
        if len(bucket) >= self._max:
            preview = key if len(key) <= 128 else key[:125] + "..."
            logger.warning("rate_limit exceeded kind=session key=%s", preview)
            return RateLimitResult(False, 0, reset_epoch)
        bucket.append(now)
        remaining_after = max(0, self._max - len(bucket))
        return RateLimitResult(True, remaining_after, reset_epoch)


CHAT_MESSAGE_LIMITER = SessionRateLimiter(max_events=20, window_seconds=60.0)
CHAT_FEEDBACK_LIMITER = SessionRateLimiter(max_events=10, window_seconds=60.0)


def split_chat_session_budget(session_id: str) -> RateLimitResult:
    """Consume one token from shared chat/message + chat/message/stream quota."""
    return CHAT_MESSAGE_LIMITER.check(session_id)


def reset_session_rate_limiters_for_tests() -> None:
    """Clear buckets; tests only."""
    CHAT_MESSAGE_LIMITER.clear()
    CHAT_FEEDBACK_LIMITER.clear()
