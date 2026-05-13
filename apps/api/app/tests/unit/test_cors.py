"""CORS tightened config (Week 6)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_preflight_allows_configured_origin(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    get_settings.cache_clear()
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.options(
                "/api/v1/health",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert "GET" in (resp.headers.get("access-control-allow-methods") or "").upper()
    finally:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        get_settings.cache_clear()


def test_get_health_exposes_rate_limit_related_headers(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    get_settings.cache_clear()
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get(
                "/api/v1/health",
                headers={"Origin": "http://localhost:3000"},
            )
        assert resp.status_code == 200
        exposed = resp.headers.get("access-control-expose-headers", "").lower()
        assert "retry-after" in exposed
        assert "x-ratelimit-remaining" in exposed
        assert "x-request-id" in exposed
    finally:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        get_settings.cache_clear()


def test_unlisted_origin_health_still_returns_body_without_reflect(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    get_settings.cache_clear()
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.get(
                "/api/v1/health",
                headers={"Origin": "https://malicious.example"},
            )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") != "https://malicious.example"
    finally:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        get_settings.cache_clear()
