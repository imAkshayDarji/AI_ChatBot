"""Admin authentication routes."""

from fastapi import APIRouter, Request

from app.api.deps import DashboardUser, DBSessionDep
from app.core.errors import InvalidCredentialsError
from app.core.rate_limit import check_login_rate_limit
from app.db.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/admin", tags=["admin-auth"])


@router.post("/auth/login")
async def admin_login(request: Request, body: LoginRequest, db: DBSessionDep) -> TokenResponse:
    check_login_rate_limit(request)
    user = await auth_service.authenticate_user(db, str(body.email), body.password)
    if user is None or not user.is_active:
        raise InvalidCredentialsError("Invalid email or password")

    access, refresh = await auth_service.issue_tokens(db, user.id)
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh")
async def admin_refresh(body: RefreshRequest, db: DBSessionDep) -> TokenResponse:
    access, refresh = await auth_service.rotate_refresh_tokens(db, body.refresh_token.strip())
    await db.commit()
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.get("/me", response_model=UserResponse)
async def admin_me(user: DashboardUser) -> User:
    return user
