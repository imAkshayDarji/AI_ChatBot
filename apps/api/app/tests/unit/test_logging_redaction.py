"""PII stripping for log payloads (Week 6)."""

from __future__ import annotations

from app.core.logging import redact_pii


def test_redacts_email() -> None:
    assert "***@***.***" in redact_pii("Contact alice@studio.test today")


def test_redacts_na_phone_digits() -> None:
    raw = "Call +1 (415) 555-0199"
    out = redact_pii(raw)
    assert "***-***-****" in out
    assert "415" not in out
