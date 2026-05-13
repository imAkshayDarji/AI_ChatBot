"""OpenAI embedding client with retries and batch limits."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.errors import EmbeddingError

logger = logging.getLogger(__name__)

MAX_BATCH = 100
_MAX_ATTEMPTS = 3
_INITIAL_BACKOFF_SECONDS = 0.75


@runtime_checkable
class SupportsEmbeddings(Protocol):
    async def embed_text(self, text: str) -> list[float]: ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, query: str) -> list[float]: ...


class EmbeddingService:
    """All embedding calls for RAG go through this service (PLAN.md §1.5)."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-large",
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._model = model
        self._client = client if client is not None else AsyncOpenAI(api_key=api_key)

    async def embed_text(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if len(texts) > MAX_BATCH:
            raise ValueError(f"embed_texts batch exceeds {MAX_BATCH} strings")

        async def call() -> tuple[list[list[float]], int | None]:
            response = await self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            ordered = sorted(response.data, key=lambda d: d.index)
            vectors = [list(item.embedding) for item in ordered]
            total = getattr(response.usage, "total_tokens", None) if response.usage else None
            return vectors, total

        vectors, total_tokens = await self._retry(call)
        if total_tokens is not None:
            logger.info(
                "embedding_tokens_total=%s model=%s batch=%s",
                total_tokens,
                self._model,
                len(texts),
            )
        return vectors

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query)

    async def _retry(
        self,
        factory: Callable[[], Awaitable[tuple[list[list[float]], int | None]]],
    ) -> tuple[list[list[float]], int | None]:
        last: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await factory()
            except RateLimitError as exc:
                last = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    break
                wait = _INITIAL_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "embedding_rate_limited attempt=%s wait_s=%s",
                    attempt + 1,
                    wait,
                )
                await asyncio.sleep(wait)
            except (APIError, APITimeoutError) as exc:
                last = exc
                status = getattr(exc, "status_code", None)
                if status is not None and status < 500 and status != 429:
                    break
                if attempt == _MAX_ATTEMPTS - 1:
                    break
                wait = _INITIAL_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "embedding_transient_error attempt=%s wait_s=%s err=%s",
                    attempt + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
        assert last is not None
        raise _to_embedding_error(last)


def _to_embedding_error(exc: Exception) -> EmbeddingError:
    status = getattr(exc, "status_code", None)
    body_raw = getattr(exc, "body", None)
    message = str(exc)
    snippet = ""
    if body_raw is not None:
        snippet = str(body_raw)[:400]
    if snippet and snippet not in message:
        detail = f"{message} body_snippet={snippet!r}"
    else:
        detail = message
    up = status if isinstance(status, int) else None
    return EmbeddingError(detail, upstream_status=up, body_snippet=snippet or None)
