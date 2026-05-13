"""Unit tests for in-memory sliding-window rate limiters (Week 6)."""

from __future__ import annotations

from app.core.chat_rate_limit import SessionRateLimiter
from app.core.rate_limit import IpSlidingWindowLimiter


def test_ip_sliding_window_blocks_nth_request() -> None:
    lim = IpSlidingWindowLimiter(max_events=3, window_seconds=60.0)
    assert lim.check("1.2.3.4").allowed
    assert lim.check("1.2.3.4").allowed
    r = lim.check("1.2.3.4")
    assert r.allowed
    assert lim.check("1.2.3.4").allowed is False


def test_ip_limiter_evicts_under_max_keys_pressure() -> None:
    lim = IpSlidingWindowLimiter(max_events=5, window_seconds=60.0, max_keys=2)
    assert lim.check("ip-one").allowed
    assert lim.check("ip-two").allowed
    assert lim.check("ip-three").allowed


def test_session_limiter_matches_message_budget_contract() -> None:
    sess = SessionRateLimiter(max_events=20, window_seconds=60.0, max_keys=100)
    key = "session-aaa"
    for _ in range(19):
        assert sess.check(key).allowed
    r20 = sess.check(key)
    assert r20.allowed
    assert sess.check(key).allowed is False
