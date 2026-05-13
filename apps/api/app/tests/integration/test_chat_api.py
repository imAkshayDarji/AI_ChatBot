"""Chat + leads happy-path coverage (PostgreSQL-backed)."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api import deps as api_deps
from app.db.session import get_db
from app.main import app
from app.services.ai.provider import AIResponse

pytestmark = pytest.mark.integration


class _StubEmbeddings:
    dimensions = 3072

    async def embed_text(self, text: str) -> list[float]:
        return [0.01] * self.dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * self.dimensions for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query)


def _stub_emb() -> _StubEmbeddings:
    return _StubEmbeddings()


class _DeterministicChatProvider:
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AIResponse:
        _ = messages, model, temperature, max_tokens
        content = (
            "We customise tattoos and piercings and book by consultation.\n"
            'SUGGESTED_REPLIES_JSON: ["Typical pricing?", "Book consultation?"]'
        )
        return AIResponse(
            content=content,
            model="stub-mini",
            input_tokens=0,
            output_tokens=0,
            finish_reason="stop",
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        _ = messages, model, temperature
        yield "stub "


@pytest_asyncio.fixture
async def integration_chat_stub_client(_engine_and_session):  # type: ignore[no-untyped-def]
    _eng, factory = _engine_and_session

    async def override_get_db() -> AsyncGenerator:
        async with factory() as session:
            yield session

    stub = _DeterministicChatProvider()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[api_deps.get_embedding_service] = _stub_emb
    app.dependency_overrides[api_deps.get_openai_chat_provider] = lambda: stub

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_start_ok(integration_chat_stub_client: AsyncClient) -> None:
    response = await integration_chat_stub_client.post(
        "/api/v1/chat/start",
        json={"language": "en", "channel": "web"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"]
    assert data["quick_replies"]


@pytest.mark.asyncio
async def test_chat_message_whitespace_only_422(integration_chat_stub_client: AsyncClient) -> None:
    started = await integration_chat_stub_client.post("/api/v1/chat/start", json={"language": "en"})
    session_id = started.json()["session_id"]

    response = await integration_chat_stub_client.post(
        "/api/v1/chat/message",
        json={"session_id": session_id, "message": "   \t  ", "language": "en"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_message_flow_headers(integration_chat_stub_client: AsyncClient) -> None:
    started = await integration_chat_stub_client.post("/api/v1/chat/start", json={"language": "en"})
    session_id = started.json()["session_id"]

    response = await integration_chat_stub_client.post(
        "/api/v1/chat/message",
        json={"session_id": session_id, "message": "How much is a small tattoo?", "language": "en"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"]
    assert body["content"]
    lower_keys = {k.lower() for k in response.headers.keys()}
    assert "x-ratelimit-remaining" in lower_keys


@pytest.mark.asyncio
async def test_feedback_rating_five_allowed(integration_chat_stub_client: AsyncClient) -> None:
    started = await integration_chat_stub_client.post("/api/v1/chat/start", json={"language": "en"})
    session_id = started.json()["session_id"]

    msg = await integration_chat_stub_client.post(
        "/api/v1/chat/message",
        json={"session_id": session_id, "message": "Tell me pricing", "language": "en"},
    )
    message_id = msg.json()["message_id"]

    fb = await integration_chat_stub_client.post(
        "/api/v1/chat/feedback",
        json={"session_id": session_id, "message_id": message_id, "rating": 5},
    )
    assert fb.status_code == 201


@pytest.mark.asyncio
async def test_feedback_wrong_session_forbidden(integration_chat_stub_client: AsyncClient) -> None:
    started = await integration_chat_stub_client.post("/api/v1/chat/start", json={"language": "en"})
    session_id = started.json()["session_id"]

    msg = await integration_chat_stub_client.post(
        "/api/v1/chat/message",
        json={"session_id": session_id, "message": "Tell me pricing", "language": "en"},
    )
    message_id = msg.json()["message_id"]

    fb = await integration_chat_stub_client.post(
        "/api/v1/chat/feedback",
        json={"session_id": "other-session-not-yours", "message_id": message_id, "rating": 5},
    )
    assert fb.status_code == 403


@pytest.mark.asyncio
async def test_create_lead_success(integration_chat_stub_client: AsyncClient) -> None:
    response = await integration_chat_stub_client.post(
        "/api/v1/leads",
        json={
            "name": "Akshay",
            "email": "akshay@test.com",
            "phone": "9876543210",
            "service_interest": "tattoo",
            "consent": True,
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_lead_without_consent_422(integration_chat_stub_client: AsyncClient) -> None:
    response = await integration_chat_stub_client.post(
        "/api/v1/leads",
        json={
            "name": "Akshay",
            "email": "akshay@test.com",
            "consent": False,
        },
    )
    assert response.status_code == 422
