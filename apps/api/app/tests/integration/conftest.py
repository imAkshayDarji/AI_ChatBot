"""PostgreSQL-backed fixtures for integration tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.api import deps as api_deps
from app.core.security import hash_password
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


class _StubEmbeddings:
    """Deterministic 3072-d vectors for CI (no OpenAI calls)."""

    dimensions = 3072

    async def embed_text(self, text: str) -> list[float]:
        return [0.01] * self.dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * self.dimensions for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query)


def _stub_embeddings() -> _StubEmbeddings:
    return _StubEmbeddings()


TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://krystal:krystal_dev_password@localhost:5432/krystal_studio",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("SKIP_INTEGRATION") == "1":
        skip_int = pytest.mark.skip(reason="SKIP_INTEGRATION=1")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_int)


@pytest_asyncio.fixture
async def _engine_and_session() -> AsyncGenerator:
    """Create engine + sessionmaker on the SAME event loop as the test.

    Uses NullPool to avoid cross-loop connection reuse with asyncpg.
    """
    eng = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield eng, factory

    async with eng.begin() as conn:
        for tbl in reversed(Base.metadata.sorted_tables):
            await conn.execute(delete(tbl))

    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(_engine_and_session):
    _eng, factory = _engine_and_session
    return factory


@pytest_asyncio.fixture(autouse=True)
async def _truncate(_engine_and_session) -> AsyncGenerator[None, None]:
    from app.core import chat_rate_limit as chat_rl
    from app.core import rate_limit as ip_rl

    ip_rl.reset_ip_rate_limiters_for_tests()
    chat_rl.reset_session_rate_limiters_for_tests()

    _eng, factory = _engine_and_session
    async with factory() as session:
        for tbl in reversed(Base.metadata.sorted_tables):
            await session.execute(delete(tbl))
        await session.commit()
    yield
    async with factory() as session:
        for tbl in reversed(Base.metadata.sorted_tables):
            await session.execute(delete(tbl))
        await session.commit()


@pytest_asyncio.fixture
async def integration_client(
    _engine_and_session,
) -> AsyncGenerator[AsyncClient, None]:
    _eng, factory = _engine_and_session

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[api_deps.get_embedding_service] = _stub_embeddings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def owner_user(session_factory):  # type: ignore[no-untyped-def]
    async with session_factory() as session:
        user = User(
            email="owner-test@example.com",
            password_hash=hash_password("password123"),
            role="owner",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
