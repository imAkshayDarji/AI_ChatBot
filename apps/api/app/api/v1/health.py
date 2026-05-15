import asyncio
import logging
import time

from fastapi import APIRouter

router = APIRouter()

logger = logging.getLogger(__name__)

_ai_check_cache: dict[str, object] = {}
_CACHE_TTL = 30.0


async def _check_ai_provider() -> tuple[str, str | None]:
    try:
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.OPENAI_API_KEY.strip():
            return "not_configured", "OPENAI_API_KEY not set"

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            ),
            timeout=10.0,
        )
        if response.choices:
            return "connected", None
        return "error", "No choices in response"
    except asyncio.TimeoutError:
        return "timeout", "AI provider did not respond within 10s"
    except Exception as exc:
        return "error", str(exc)[:200]


@router.get("/health")
async def health_check() -> dict[str, object]:
    db_status = "not_tested"
    try:
        from sqlalchemy import text

        from app.db.session import engine as async_engine

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    now = time.monotonic()
    cached_at = _ai_check_cache.get("ts")
    if cached_at is not None and (now - float(cached_at)) < _CACHE_TTL:
        ai_status = _ai_check_cache.get("status", "unknown")
        ai_detail = _ai_check_cache.get("detail")
    else:
        ai_status, ai_detail = await _check_ai_provider()
        _ai_check_cache["status"] = ai_status
        _ai_check_cache["detail"] = ai_detail
        _ai_check_cache["ts"] = now

    overall = "ok"
    if db_status == "error":
        overall = "unhealthy"
    elif ai_status in ("error", "timeout"):
        overall = "degraded"

    result: dict[str, object] = {
        "status": overall,
        "version": "1.0.0",
        "db": db_status,
        "ai": ai_status,
    }
    if ai_detail:
        result["ai_detail"] = ai_detail
    return result
