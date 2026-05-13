"""Best-effort analytics persistence."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analytics_event import AnalyticsEvent

EVENT_TYPES = (
    "chat_started",
    "language_selected",
    "message_sent",
    "assistant_response",
    "lead_capture_prompted",
    "lead_created",
    "handoff_triggered",
    "rag_no_result",
    "pricing_question",
    "aftercare_question",
    "recommendation_requested",
    "feedback_positive",
    "feedback_negative",
)

_logger = logging.getLogger(__name__)


class AnalyticsTracker:
    async def track_event(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID | None,
        event_type: str,
        event_data: dict[str, Any] | None = None,
    ) -> AnalyticsEvent | None:
        try:
            if event_type not in EVENT_TYPES:
                raise ValueError(f"Unknown analytics event_type={event_type}")
            row = AnalyticsEvent(
                conversation_id=conversation_id,
                event_type=event_type,
                event_data=event_data or {},
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            return row
        except Exception as exc:
            await db.rollback()
            _logger.warning("analytics track_event failed event_type=%s err=%s", event_type, exc)
            return None

    async def track_chat_started(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        language: str,
        *,
        channel: str = "web",
    ) -> None:
        await self.track_event(
            db,
            conversation_id,
            "chat_started",
            {"language": language, "channel": channel},
        )

    async def track_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        intent: str | None,
        *,
        channel: str | None = None,
    ) -> None:
        data: dict[str, object] = {"role": role, "intent": intent}
        if channel is not None:
            data["channel"] = channel
        await self.track_event(db, conversation_id, "message_sent", data)

    async def track_handoff(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        reason: str,
    ) -> None:
        await self.track_event(
            db,
            conversation_id,
            "handoff_triggered",
            {"reason": reason},
        )

    async def track_rag_no_result(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        query: str,
    ) -> None:
        await self.track_event(
            db,
            conversation_id,
            "rag_no_result",
            {"query": query},
        )

    async def track_lead_created(self, db: AsyncSession, lead_id: uuid.UUID, source: str) -> None:
        await self.track_event(
            db,
            None,
            "lead_created",
            {"lead_id": str(lead_id), "source": source},
        )
