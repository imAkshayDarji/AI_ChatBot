"""Domain errors and FastAPI handlers. Routes raise domain errors; handlers map to HTTP."""

import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class DomainError(Exception):
    """Base for application domain errors."""

    detail: str

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class InvalidCredentialsError(DomainError):
    pass


class AccountInactiveError(DomainError):
    pass


class TokenExpiredError(DomainError):
    pass


class InvalidTokenError(DomainError):
    pass


class RateLimitExceededError(DomainError):
    retry_after_seconds: int | None
    rate_limit_remaining: int | None
    rate_limit_reset_epoch: int | None

    def __init__(
        self,
        detail: str,
        *,
        retry_after_seconds: int | None = None,
        rate_limit_remaining: int | None = None,
        rate_limit_reset_epoch: int | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset_epoch = rate_limit_reset_epoch
        super().__init__(detail)


class KnowledgeStatusTransitionError(DomainError):
    pass


class ValidationDomainError(DomainError):
    pass


class EmbeddingError(DomainError):
    """Upstream embedding provider failure after retries."""

    upstream_status: int | None
    body_snippet: str | None

    def __init__(
        self,
        detail: str,
        *,
        upstream_status: int | None = None,
        body_snippet: str | None = None,
    ) -> None:
        self.upstream_status = upstream_status
        self.body_snippet = body_snippet
        super().__init__(detail)


class AIProviderError(DomainError):
    """Upstream chat/completions provider failure after retries."""

    upstream_status: int | None
    body_snippet: str | None

    def __init__(
        self,
        detail: str,
        *,
        upstream_status: int | None = None,
        body_snippet: str | None = None,
    ) -> None:
        self.upstream_status = upstream_status
        self.body_snippet = body_snippet
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def pydantic_exc(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    @app.exception_handler(RateLimitExceededError)
    async def rate_lim(request: Request, exc: RateLimitExceededError) -> JSONResponse:
        retry_after = exc.retry_after_seconds
        if retry_after is None and exc.rate_limit_reset_epoch is not None:
            retry_after = max(1, exc.rate_limit_reset_epoch - int(time.time()))
        if retry_after is None:
            retry_after = _retry_after_seconds()
        headers: dict[str, str] = {"Retry-After": str(retry_after)}
        if exc.rate_limit_remaining is not None:
            headers["X-RateLimit-Remaining"] = str(exc.rate_limit_remaining)
        if exc.rate_limit_reset_epoch is not None:
            headers["X-RateLimit-Reset"] = str(exc.rate_limit_reset_epoch)
        return JSONResponse(
            status_code=429,
            content={"detail": exc.detail},
            headers=headers,
        )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.detail})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(
        InvalidCredentialsError,
    )
    async def invalid_creds_handler(
        request: Request,
        exc: InvalidCredentialsError,
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": exc.detail})

    @app.exception_handler(AccountInactiveError)
    async def inactive_handler(request: Request, exc: AccountInactiveError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"detail": exc.detail},
        )

    @app.exception_handler(TokenExpiredError)
    async def token_expired_handler(request: Request, exc: TokenExpiredError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": exc.detail})

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": exc.detail})

    @app.exception_handler(KnowledgeStatusTransitionError)
    async def knowledge_transition_handler(
        request: Request,
        exc: KnowledgeStatusTransitionError,
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.detail})

    @app.exception_handler(ValidationDomainError)
    async def validation_domain_handler(
        request: Request,
        exc: ValidationDomainError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.detail})

    @app.exception_handler(EmbeddingError)
    async def embedding_error_handler(request: Request, exc: EmbeddingError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "detail": exc.detail,
                "upstream_status": exc.upstream_status,
                "body_snippet": exc.body_snippet,
            },
        )

    @app.exception_handler(AIProviderError)
    async def ai_provider_error_handler(request: Request, exc: AIProviderError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={
                "detail": exc.detail,
                "upstream_status": exc.upstream_status,
                "body_snippet": exc.body_snippet,
            },
        )

    @app.exception_handler(DomainError)
    async def domain_fallback(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.detail})

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, str):
            content: dict[str, object] = {"detail": exc.detail}
        elif isinstance(exc.detail, dict):
            content = dict(exc.detail)
        else:
            content = {"detail": str(exc.detail)}
        headers = dict(exc.headers) if exc.headers else None
        return JSONResponse(status_code=exc.status_code, content=content, headers=headers)


def _retry_after_seconds() -> int:
    from app.core.config import get_settings

    return max(1, get_settings().LOGIN_RATE_LIMIT_WINDOW_SECONDS)
