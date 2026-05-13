"""Public leads capture schemas."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LeadCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=40)
    preferred_language: Literal["en", "hi", "gu"] = "en"
    service_interest: str | None = Field(None, max_length=200)
    budget_range: str | None = Field(None, max_length=120)
    placement: str | None = Field(None, max_length=200)
    style_preference: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=2000)
    source: str = Field(default="website", max_length=50)
    consent: Literal[True] = Field(..., description="Consent must be true to submit")


class LeadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
    service_interest: str | None = None
    status: str | None = None
    source: str | None = None
