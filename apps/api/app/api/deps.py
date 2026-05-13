"""Route dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AccountInactiveError,
    ForbiddenError,
    InvalidTokenError,
    TokenExpiredError,
)
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

DBSessionDep = Annotated[AsyncSession, Depends(get_db)]

_bearer_scheme = HTTPBearer(auto_error=False)


async def _read_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidTokenError("Authorization header missing or invalid")
    return credentials.credentials


async def get_current_user(
    token_str: Annotated[str, Depends(_read_token)],
    db: DBSessionDep,
) -> User:
    try:
        payload = decode_access_token(token_str)
        sub_raw = payload.get("sub")
        if not sub_raw or not isinstance(sub_raw, str):
            raise InvalidTokenError("Access token payload missing subject")
        user_id = uuid.UUID(sub_raw)
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired") from exc
    except ValueError as exc:
        raise InvalidTokenError("Access token subject is not a UUID") from exc
    except JWTError as exc:
        raise InvalidTokenError("Access token invalid") from exc

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise InvalidTokenError("User not found for access token")

    if not user.is_active:
        raise AccountInactiveError("Account is inactive")

    return user


def require_role(*allowed_roles: str):
    allowed = frozenset(allowed_roles)

    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed:
            raise ForbiddenError("Insufficient permission for this action")
        return current_user

    return role_checker


DashboardUser = Annotated[User, Depends(require_role("owner", "admin", "staff"))]
