"""Integration tests for Week 5 admin routes: leads, conversations, analytics, settings."""

from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.models.conversation import Conversation
from app.db.models.lead import Lead
from app.db.models.message import Message
from app.db.models.user import User


@pytest_asyncio.fixture
async def staff_user(session_factory):  # type: ignore[no-untyped-def]
    async with session_factory() as session:
        user = User(
            email="staff-test@example.com",
            password_hash=hash_password("password123"),
            role="staff",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def seeded_lead(session_factory):  # type: ignore[no-untyped-def]
    async with session_factory() as session:
        lead = Lead(
            name="Test Lead",
            email="test@example.com",
            phone="+91-99999-00000",
            status="new",
            source="chat",
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead


@pytest_asyncio.fixture
async def seeded_conversation(session_factory, seeded_lead):  # type: ignore[no-untyped-def]
    async with session_factory() as session:
        conv = Conversation(
            session_id="test-session-123",
            lead_id=seeded_lead.id,
            language="en",
            status="ended",
        )
        session.add(conv)
        await session.commit()
        await session.refresh(conv)

        msg = Message(
            conversation_id=conv.id,
            role="user",
            content="How much does a tattoo cost?",
            intent="pricing_guidance",
            confidence=0.3,
        )
        session.add(msg)
        await session.commit()
        return conv


async def _login(client: AsyncClient, email: str, password: str = "password123") -> str:
    resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Unauthenticated access ──


class TestAdminRoutesUnauthenticated:
    async def test_leads_requires_auth(self, integration_client: AsyncClient) -> None:
        resp = await integration_client.get("/api/v1/admin/leads")
        assert resp.status_code in (401, 403)

    async def test_chats_requires_auth(self, integration_client: AsyncClient) -> None:
        resp = await integration_client.get("/api/v1/admin/chats")
        assert resp.status_code in (401, 403)

    async def test_analytics_requires_auth(self, integration_client: AsyncClient) -> None:
        resp = await integration_client.get("/api/v1/admin/analytics/overview")
        assert resp.status_code in (401, 403)

    async def test_settings_requires_auth(self, integration_client: AsyncClient) -> None:
        resp = await integration_client.get("/api/v1/admin/settings")
        assert resp.status_code in (401, 403)


# ── Admin Leads ──


class TestAdminLeads:
    async def test_list_leads(
        self, integration_client: AsyncClient, owner_user: User, seeded_lead: Lead
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/leads", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    async def test_get_lead(
        self, integration_client: AsyncClient, owner_user: User, seeded_lead: Lead
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            f"/api/v1/admin/leads/{seeded_lead.id}", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(seeded_lead.id)
        assert data["status"] == "new"

    async def test_update_lead_status(
        self, integration_client: AsyncClient, owner_user: User, seeded_lead: Lead
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.patch(
            f"/api/v1/admin/leads/{seeded_lead.id}",
            json={"status": "contacted"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "contacted"

    async def test_list_leads_filter_status(
        self, integration_client: AsyncClient, owner_user: User, seeded_lead: Lead
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/leads?status=new", headers=_auth_header(token)
        )
        assert resp.status_code == 200

    async def test_get_lead_not_found(
        self, integration_client: AsyncClient, owner_user: User
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/leads/00000000-0000-0000-0000-000000000000",
            headers=_auth_header(token),
        )
        assert resp.status_code == 404


# ── Admin Conversations ──


class TestAdminConversations:
    async def test_list_conversations(
        self,
        integration_client: AsyncClient,
        owner_user: User,
        seeded_conversation: Conversation,
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/chats", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)

    async def test_get_conversation_detail(
        self,
        integration_client: AsyncClient,
        owner_user: User,
        seeded_conversation: Conversation,
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            f"/api/v1/admin/chats/{seeded_conversation.id}",
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(seeded_conversation.id)
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1


# ── Admin Analytics ──


class TestAdminAnalytics:
    async def test_overview(
        self,
        integration_client: AsyncClient,
        owner_user: User,
        seeded_conversation: Conversation,
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/analytics/overview", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_conversations" in data
        assert "total_leads" in data
        assert "popular_services" in data

    async def test_popular_intents(
        self, integration_client: AsyncClient, owner_user: User
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/analytics/popular-intents", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "intents" in data

    async def test_failed_queries(
        self,
        integration_client: AsyncClient,
        owner_user: User,
        seeded_conversation: Conversation,
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/analytics/failed-queries", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


# ── Admin Settings ──


class TestAdminSettings:
    async def test_get_settings(
        self, integration_client: AsyncClient, owner_user: User
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.get(
            "/api/v1/admin/settings", headers=_auth_header(token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["studio_name"] == "Krystal Tattoo Studio"
        assert "rag_similarity_threshold" in data

    async def test_update_settings(
        self, integration_client: AsyncClient, owner_user: User
    ) -> None:
        token = await _login(integration_client, owner_user.email)
        resp = await integration_client.patch(
            "/api/v1/admin/settings",
            json={"rag_top_k": 7},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
