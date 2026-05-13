"""Admin conversation schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MessageInConversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    intent: str | None = None
    confidence: float | None = None
    created_at: datetime


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: str
    language: str | None = None
    status: str
    summary: str | None = None
    lead_id: UUID | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: str
    language: str | None = None
    status: str
    summary: str | None = None
    lead_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageInConversation] = []


class PaginatedConversationsResponse(BaseModel):
    items: list[ConversationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
