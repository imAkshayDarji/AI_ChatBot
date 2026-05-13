import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_placeholder_jwt_blocked_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    get_settings.cache_clear()
    try:
        from app.main import app, lifespan

        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            async with lifespan(app):
                pass
    finally:
        get_settings.cache_clear()
