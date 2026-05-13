"""Admin settings schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class StudioHours(BaseModel):
    mon_sat: str = "11:30 am - 10 pm"
    sun: str = "12 - 10 pm"


class StudioSettingsResponse(BaseModel):
    studio_name: str
    studio_phone: str
    studio_instagram: str
    studio_address: str = ""
    studio_hours: StudioHours
    default_language: str = "en"
    supported_languages: list[str] = ["en", "hi", "gu"]
    handoff_message_template: str = ""
    rag_similarity_threshold: float = 0.7
    rag_top_k: int = 5
    max_message_length: int = 2000
    updated_at: datetime | None = None


class StudioSettingsUpdate(BaseModel):
    studio_phone: str | None = None
    handoff_message_template: str | None = None
    rag_similarity_threshold: float | None = Field(None, ge=0.0, le=1.0)
    rag_top_k: int | None = Field(None, ge=1, le=20)
    max_message_length: int | None = Field(None, ge=100, le=5000)
