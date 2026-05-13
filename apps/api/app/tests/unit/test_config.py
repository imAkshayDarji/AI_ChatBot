from app.core.config import get_settings


def test_settings_loads_from_env():
    settings = get_settings()
    assert settings.STUDIO_NAME == "Krystal Tattoo Studio"
    assert settings.ENVIRONMENT in ("development", "production")
