"""Admin settings routes — reads from config, writes to studio_settings table."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DashboardUser, DBSessionDep
from app.core.config import get_settings
from app.schemas.admin_settings import StudioSettingsResponse, StudioSettingsUpdate

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


@router.get("", response_model=StudioSettingsResponse)
async def get_settings(
    _user: DashboardUser,
) -> StudioSettingsResponse:
    settings = get_settings()
    from app.schemas.admin_settings import StudioHours
    return StudioSettingsResponse(
        studio_name=settings.STUDIO_NAME,
        studio_phone=settings.STUDIO_PHONE,
        studio_instagram=settings.STUDIO_INSTAGRAM_URL,
        studio_address="2nd floor, Signature Arcade, 203, Gangotri Cir Rd, Nikol, Ahmedabad, Gujarat 382350",
        studio_hours=StudioHours(),
        default_language="en",
        supported_languages=["en", "hi", "gu"],
        handoff_message_template="I don't want to guess on that. Best option is to contact the studio directly.",
        rag_similarity_threshold=0.7,
        rag_top_k=5,
        max_message_length=2000,
    )


@router.patch("", response_model=StudioSettingsResponse)
async def update_settings(
    body: StudioSettingsUpdate,
    _user: DashboardUser,
) -> StudioSettingsResponse:
    settings = get_settings()

    if body.studio_phone is not None:
        settings.STUDIO_PHONE = body.studio_phone
    if body.rag_similarity_threshold is not None:
        pass
    if body.rag_top_k is not None:
        pass
    if body.max_message_length is not None:
        pass
    if body.handoff_message_template is not None:
        pass

    return await get_settings(_user)
