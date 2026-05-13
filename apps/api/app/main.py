from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware.request_context import RequestIdMiddleware, RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    is_production = settings.ENVIRONMENT == "production"
    placeholder = settings.JWT_SECRET.strip() == "change-me-in-production"
    if is_production and placeholder:
        raise RuntimeError(
            "Refusing to start in production with default JWT_SECRET. Set a strong JWT_SECRET."
        )

    if settings.SENTRY_DSN:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.1,
        )

    yield


app = FastAPI(
    title="Krystal Studio AI Chatbot",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=[
        "Retry-After",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-Request-Id",
    ],
)

register_exception_handlers(app)
app.include_router(v1_router)
