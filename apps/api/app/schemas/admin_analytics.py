"""Admin analytics schemas."""

from __future__ import annotations

from pydantic import BaseModel


class DatePeriod(BaseModel):
    start_date: str
    end_date: str


class ServiceCount(BaseModel):
    service: str
    count: int


class LanguageCount(BaseModel):
    language: str
    count: int


class AnalyticsOverview(BaseModel):
    period: DatePeriod
    total_conversations: int = 0
    total_messages: int = 0
    total_leads: int = 0
    lead_conversion_rate: float = 0.0
    handoff_rate: float = 0.0
    average_feedback_rating: float = 0.0
    popular_services: list[ServiceCount] = []
    language_distribution: list[LanguageCount] = []


class IntentStat(BaseModel):
    intent: str
    count: int
    percentage: float = 0.0


class PopularIntentsResponse(BaseModel):
    period: DatePeriod
    intents: list[IntentStat]


class FailedQueryItem(BaseModel):
    id: str
    conversation_id: str | None = None
    user_message: str
    intent: str | None = None
    confidence: float | None = None
    handoff_triggered: bool = False
    handoff_reason: str | None = None
    created_at: str


class PaginatedFailedQueries(BaseModel):
    items: list[FailedQueryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
