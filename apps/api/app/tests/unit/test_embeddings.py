"""Unit tests for embedding service (mocked OpenAI)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.errors import EmbeddingError
from app.services.rag.embeddings import EmbeddingService


@pytest.mark.asyncio
async def test_embed_text_returns_vector() -> None:
    fake = MagicMock()
    fake.data = [MagicMock(index=0, embedding=[0.1] * 3072)]
    fake.usage = MagicMock(total_tokens=3)
    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock(return_value=fake)

    service = EmbeddingService(api_key="test-key", client=client)
    embedding = await service.embed_text("Hello world")
    assert isinstance(embedding, list)
    assert len(embedding) == 3072


@pytest.mark.asyncio
async def test_embed_texts_batch() -> None:
    fake = MagicMock()
    fake.data = [
        MagicMock(index=0, embedding=[0.2] * 3072),
        MagicMock(index=1, embedding=[0.3] * 3072),
    ]
    fake.usage = MagicMock(total_tokens=6)
    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock(return_value=fake)

    service = EmbeddingService(api_key="test-key", client=client)
    embeddings = await service.embed_texts(["Hello", "World"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 3072


@pytest.mark.asyncio
async def test_embed_error_handling() -> None:
    from openai import APIError

    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock(
        side_effect=APIError(
            message="bad",
            request=MagicMock(),
            body=None,
        ),
    )

    service = EmbeddingService(api_key="test-key", client=client)
    with pytest.raises(EmbeddingError):
        await service.embed_text("test")
