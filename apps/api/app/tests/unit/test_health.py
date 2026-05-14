import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "db" in data
    assert data["db"] in ("not_configured", "error", "ok")
