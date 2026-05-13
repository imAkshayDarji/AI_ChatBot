"""Per-session sliding-window limits for anonymous chat endpoints."""

from __future__ import annotations

import time
from dataclasses import dataclass


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
    def __init__(self, *, max_events: int, window_seconds: float) -> None:
        self._max = max_events
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> RateLimitResult:
        now = time.monotonic()
        bucket = self._buckets.setdefault(key, [])
        _prune(bucket, window_s=self._window, now=now)
        reset_epoch = int(time.time()) + int(self._window)
        if len(bucket) >= self._max:
            return RateLimitResult(False, 0, reset_epoch)
        bucket.append(now)
        remaining_after = max(0, self._max - len(bucket))
        return RateLimitResult(True, remaining_after, reset_epoch)


CHAT_MESSAGE_LIMITER = SessionRateLimiter(max_events=20, window_seconds=60.0)
CHAT_FEEDBACK_LIMITER = SessionRateLimiter(max_events=10, window_seconds=60.0)


def split_chat_session_budget(session_id: str) -> RateLimitResult:
    """Consume one token from shared chat/message + chat/message/stream quota."""
    return CHAT_MESSAGE_LIMITER.check(session_id)
