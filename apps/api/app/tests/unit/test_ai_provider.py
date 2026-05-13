"""Unit tests for OpenAI chat provider (mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import AIProviderError
from app.services.ai.model_router import ModelRouter
from app.services.ai.provider import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_chat() -> None:
    fake_choice = MagicMock()
    fake_choice.message.content = "Hi there"
    fake_choice.finish_reason = "stop"
    fake_resp = MagicMock()
    fake_resp.choices = [fake_choice]
    fake_resp.usage = MagicMock(prompt_tokens=5, completion_tokens=2)

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=fake_resp)

    provider = OpenAIProvider(api_key="test-key", client=client)
    response = await provider.chat([{"role": "user", "content": "Hello"}])
    assert response.content == "Hi there"
    assert response.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_model_router_simple() -> None:
    router = ModelRouter()
    model = router.select_model(intent="greeting", complexity="simple")
    assert model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_model_router_complex() -> None:
    router = ModelRouter()
    model = router.select_model(intent="recommendation", complexity="complex")
    assert model == "gpt-4o"


@pytest.mark.asyncio
async def test_provider_error_handling() -> None:
    from openai import APIError

    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(
        side_effect=APIError(
            message="upstream",
            request=MagicMock(),
            body=None,
        ),
    )
    provider = OpenAIProvider(api_key="test-key", client=client)
    with pytest.raises(AIProviderError):
        await provider.chat([{"role": "user", "content": "Hello"}])
