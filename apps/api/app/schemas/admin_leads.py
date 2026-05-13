"""Admin lead management schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
    service_interest: str | None = None
    budget_range: str | None = None
    placement: str | None = None
    style_preference: str | None = None
    notes: str | None = None
    conversation_context: str | None = None
    status: str
    source: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminLeadUpdateRequest(BaseModel):
    status: str | None = Field(None, pattern=r"^(new|contacted|consultation_booked|converted|closed)$")
    notes: str | None = Field(None, max_length=2000)


class PaginatedLeadsResponse(BaseModel):
    items: list[AdminLeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
