"""Auth and knowledge flows against PostgreSQL."""

import pytest
from httpx import AsyncClient

from app.db.models.user import User

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_login_refresh_and_me(integration_client: AsyncClient, owner_user: User) -> None:
    login = await integration_client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_user.email, "password": "password123"},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert "access_token" in body and "refresh_token" in body

    me = await integration_client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == owner_user.email

    refresh = await integration_client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert refresh.status_code == 200, refresh.text
    new_body = refresh.json()
    assert "access_token" in new_body
    assert "refresh_token" in new_body
    assert new_body["refresh_token"] != body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_old_token_invalid_after_rotation(
    integration_client: AsyncClient,
    owner_user: User,
) -> None:
    login = await integration_client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_user.email, "password": "password123"},
    )
    first = login.json()["refresh_token"]
    rotated = await integration_client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": first},
    )
    assert rotated.status_code == 200
    again = await integration_client.post(
        "/api/v1/admin/auth/refresh",
        json={"refresh_token": first},
    )
    assert again.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limit(integration_client: AsyncClient, owner_user: User) -> None:
    from app.core import rate_limit as rl

    rl._LOGIN_ATTEMPTS.clear()
    for _ in range(5):
        r = await integration_client.post(
            "/api/v1/admin/auth/login",
            json={"email": owner_user.email, "password": "wrong-password"},
        )
        assert r.status_code == 401
    blocked = await integration_client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_user.email, "password": "wrong-password"},
    )
    assert blocked.status_code == 429
    assert "retry-after" in {k.lower() for k in blocked.headers.keys()}


@pytest.mark.asyncio
async def test_knowledge_crud_and_status(integration_client: AsyncClient, owner_user: User) -> None:
    from app.core import rate_limit as rl

    rl._LOGIN_ATTEMPTS.clear()

    login = await integration_client.post(
        "/api/v1/admin/auth/login",
        json={"email": owner_user.email, "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = await integration_client.post(
        "/api/v1/admin/knowledge",
        headers=headers,
        json={
            "title": "Policy",
            "source_type": "manual",
            "language": "en",
            "content": "Studio policy text",
            "status": "draft",
        },
    )
    assert create.status_code == 201, create.text
    doc_id = create.json()["id"]

    bad = await integration_client.patch(
        f"/api/v1/admin/knowledge/{doc_id}",
        headers=headers,
        json={"status": "archived"},
    )
    assert bad.status_code == 409

    pub = await integration_client.patch(
        f"/api/v1/admin/knowledge/{doc_id}",
        headers=headers,
        json={"status": "active"},
    )
    assert pub.status_code == 200

    listed = await integration_client.get("/api/v1/admin/knowledge?limit=200", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) <= 100

    rin = await integration_client.post(
        f"/api/v1/admin/knowledge/{doc_id}/reindex",
        headers=headers,
    )
    assert rin.status_code == 202
