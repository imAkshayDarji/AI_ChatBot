"""OpenAI-backed chat with a narrow protocol surface."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.core.errors import AIProviderError

logger = logging.getLogger(__name__)

_CHAT_ATTEMPTS = 3
_CHAT_BACKOFF_S = 0.75


@dataclass
class AIResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


@runtime_checkable
class AIProvider(Protocol):
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AIResponse: ...

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]: ...


class OpenAIProvider:
    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._default_model = default_model
        self._client = client if client is not None else AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> AIResponse:
        use_model = model or self._default_model

        async def call() -> AIResponse:
            response = await self._client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            finish = choice.finish_reason or ""
            in_tok = 0
            out_tok = 0
            if response.usage:
                in_tok = int(response.usage.prompt_tokens or 0)
                out_tok = int(response.usage.completion_tokens or 0)
            logger.info(
                "chat_tokens in=%s out=%s model=%s",
                in_tok,
                out_tok,
                use_model,
            )
            return AIResponse(
                content=content,
                model=use_model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                finish_reason=str(finish),
            )

        return await _retry_chat(call)

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        use_model = model or self._default_model

        async def iterate() -> AsyncIterator[str]:
            stream = await self._client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=1000,
                stream=True,
            )
            async for event in stream:
                if not event.choices:
                    continue
                delta = event.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        try:
            async for piece in iterate():
                yield piece
        except (RateLimitError, APIError, APITimeoutError) as exc:
            raise _to_ai_error(exc) from exc


async def _retry_chat(factory: Callable[[], Awaitable[AIResponse]]) -> AIResponse:
    last: Exception | None = None
    for attempt in range(_CHAT_ATTEMPTS):
        try:
            return await factory()
        except RateLimitError as exc:
            last = exc
            if attempt == _CHAT_ATTEMPTS - 1:
                break
            wait = _CHAT_BACKOFF_S * (2**attempt)
            logger.warning("chat_rate_limited attempt=%s wait_s=%s", attempt + 1, wait)
            await asyncio.sleep(wait)
        except (APIError, APITimeoutError) as exc:
            last = exc
            status = getattr(exc, "status_code", None)
            if status is not None and status < 500 and status != 429:
                break
            if attempt == _CHAT_ATTEMPTS - 1:
                break
            wait = _CHAT_BACKOFF_S * (2**attempt)
            logger.warning(
                "chat_transient_error attempt=%s wait_s=%s err=%s",
                attempt + 1,
                wait,
                exc,
            )
            await asyncio.sleep(wait)
    assert last is not None
    raise _to_ai_error(last)


def _to_ai_error(exc: Exception) -> AIProviderError:
    status = getattr(exc, "status_code", None)
    body_raw = getattr(exc, "body", None)
    message = str(exc)
    snippet = str(body_raw)[:400] if body_raw is not None else ""
    detail = f"{message} body_snippet={snippet!r}" if snippet else message
    return AIProviderError(
        detail,
        upstream_status=status if isinstance(status, int) else None,
        body_snippet=snippet or None,
    )
