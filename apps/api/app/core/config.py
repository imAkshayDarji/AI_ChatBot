from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    STUDIO_NAME: str = "Krystal Tattoo Studio"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""
    DATABASE_URL: str = (
        "postgresql+asyncpg://krystal:krystal_dev_password@localhost:5432/krystal_studio"
    )
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    CHAT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    CORS_ORIGINS: str = "http://localhost:3000"
    STUDIO_PHONE: str = "+91-XXXX-XXXXXX"
    STUDIO_INSTAGRAM_URL: str = "https://www.instagram.com/krystaltattoostudio"
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
