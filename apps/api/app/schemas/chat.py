"""Pydantic models for chat API."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatStartRequest(BaseModel):
    language: Literal["en", "hi", "gu"] = "en"
    channel: Literal["web", "whatsapp", "instagram"] = "web"


class ChatStartResponse(BaseModel):
    session_id: str
    message: str
    quick_replies: list[str]


class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., max_length=1000)
    language: Literal["en", "hi", "gu"] = "en"
    channel: Literal["web", "whatsapp", "instagram"] = "web"

    @field_validator("message")
    @classmethod
    def nonempty_stripped(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be whitespace-only")
        return value


class HandoffInfo(BaseModel):
    should_handoff: bool
    reason: str | None = None
    message: str = ""
    contact_phone: str | None = None
    contact_instagram: str | None = None


class SourceReference(BaseModel):
    document_title: str
    chunk_text: str
    score: float


class ChatMessageResponse(BaseModel):
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    content: str
    intent: str | None = None
    sources: list[SourceReference]
    handoff: HandoffInfo
    lead_capture_suggested: bool = False
    suggested_replies: list[str] = Field(default_factory=list)


class ChatStreamChunk(BaseModel):
    content: str


class ChatStreamDone(BaseModel):
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    content: str
    intent: str | None = None
    sources: list[SourceReference]
    suggested_replies: list[str]
    handoff: HandoffInfo
    lead_capture_suggested: bool = False


class ChatFeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)
