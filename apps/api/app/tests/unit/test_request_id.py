"""Request ID propagation (Week 6)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_response_includes_stable_request_id_echo() -> None:
    incoming = "client-trace-abc"
    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get("/api/v1/health", headers={"X-Request-Id": incoming})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id") == incoming


def test_generated_request_id_when_header_absent() -> None:
    with TestClient(app, raise_server_exceptions=True) as client:
        resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    rid = resp.headers.get("X-Request-Id")
    assert rid and len(rid) >= 8
