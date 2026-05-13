"""Admin conversation management routes."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DashboardUser, DBSessionDep
from app.core.errors import NotFoundError
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.schemas.admin_conversations import (
    ConversationDetail,
    ConversationListItem,
    PaginatedConversationsResponse,
)

router = APIRouter(prefix="/admin/chats", tags=["admin-chats"])


@router.get("", response_model=PaginatedConversationsResponse)
async def list_conversations(
    db: DBSessionDep,
    _user: DashboardUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[str | None, Query()] = None,
    language: Annotated[str | None, Query()] = None,
    has_lead: Annotated[bool | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[str, Query()] = "desc",
) -> PaginatedConversationsResponse:
    base = select(Conversation)
    if status is not None:
        base = base.where(Conversation.status == status)
    if language is not None:
        base = base.where(Conversation.language == language)
    if has_lead is True:
        base = base.where(Conversation.lead_id.isnot(None))
    elif has_lead is False:
        base = base.where(Conversation.lead_id.is_(None))

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    order_col = Conversation.created_at if sort_by == "created_at" else Conversation.updated_at
    order = order_col.desc() if sort_order == "desc" else order_col.asc()

    rows_stmt = base.order_by(order).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(rows_stmt)).scalars().all()

    msg_count_subq = (
        select(func.count(Message.id).label("cnt"))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    items: list[ConversationListItem] = []
    for conv in rows:
        cnt_stmt = select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        msg_count = (await db.execute(cnt_stmt)).scalar_one()
        items.append(
            ConversationListItem(
                id=conv.id,
                session_id=conv.session_id,
                language=conv.language,
                status=conv.status,
                summary=conv.summary,
                lead_id=conv.lead_id,
                message_count=msg_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )

    return PaginatedConversationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: DBSessionDep,
    _user: DashboardUser,
) -> ConversationDetail:
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages) if hasattr(Conversation, "messages") else None)
    )
    conv = (await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )).scalar_one_or_none()

    if conv is None:
        raise NotFoundError("Conversation not found")

    msgs_stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = (await db.execute(msgs_stmt)).scalars().all()

    from app.schemas.admin_conversations import MessageInConversation
    return ConversationDetail(
        id=conv.id,
        session_id=conv.session_id,
        language=conv.language,
        status=conv.status,
        summary=conv.summary,
        lead_id=conv.lead_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageInConversation.model_validate(m) for m in messages],
    )
