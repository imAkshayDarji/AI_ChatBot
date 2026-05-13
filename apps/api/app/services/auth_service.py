"""Auth flows: login and refresh-token rotation."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AccountInactiveError, InvalidCredentialsError, InvalidTokenError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User | None:
    normalized = email.strip().lower()
    stmt = select(User).where(User.email == normalized)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def issue_tokens(session: AsyncSession, user_id: uuid.UUID) -> tuple[str, str]:
    raw_refresh, digest = generate_refresh_token()
    settings = get_settings()
    expires_at = datetime.now(tz=UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    rt = RefreshToken(
        user_id=user_id,
        token_hash=digest,
        expires_at=expires_at,
    )
    session.add(rt)
    await session.flush()

    access = create_access_token(subject=user_id)
    return access, raw_refresh


async def rotate_refresh_tokens(
    session: AsyncSession,
    raw_refresh_token: str,
) -> tuple[str, str]:
    digest = hash_refresh_token(raw_refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == digest,
        RefreshToken.revoked_at.is_(None),
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    now = datetime.now(tz=UTC)
    if row is None:
        raise InvalidCredentialsError("Refresh token is invalid")

    if row.expires_at < now:
        raise InvalidTokenError("Refresh token has expired")

    user_stmt = select(User).where(User.id == row.user_id)
    ures = await session.execute(user_stmt)
    user = ures.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AccountInactiveError("Account is inactive or deleted")

    row.revoked_at = now

    raw_new, digest_new = generate_refresh_token()
    new_row = RefreshToken(
        user_id=row.user_id,
        token_hash=digest_new,
        expires_at=now + timedelta(days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(new_row)
    await session.flush()

    access = create_access_token(subject=row.user_id)
    return access, raw_new
