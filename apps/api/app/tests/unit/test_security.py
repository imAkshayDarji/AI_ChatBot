import uuid

import pytest

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_and_verify_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_encode_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-key-for-jwt---------")
    get_settings.cache_clear()
    try:
        uid = uuid.uuid4()
        token = create_access_token(subject=uid)
        payload = decode_access_token(token)
        assert payload["sub"] == str(uid)
    finally:
        get_settings.cache_clear()


def test_generate_refresh_token_shape() -> None:
    raw, digest = generate_refresh_token()
    assert len(raw) > 30
    assert len(digest) == 64


def test_hash_refresh_token_deterministic() -> None:
    assert hash_refresh_token("abc123") == hash_refresh_token("abc123")
