"""Admin analytics routes."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DashboardUser, DBSessionDep
from app.db.models.conversation import Conversation
from app.db.models.feedback import AIFeedback
from app.db.models.lead import Lead
from app.db.models.message import Message
from app.schemas.admin_analytics import (
    AnalyticsOverview,
    DatePeriod,
    FailedQueryItem,
    IntentStat,
    LanguageCount,
    PaginatedFailedQueries,
    PopularIntentsResponse,
    ServiceCount,
)

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


def _parse_date_range(
    start_date: str | None,
    end_date: str | None,
) -> tuple[datetime, datetime]:
    end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) if end_date else datetime.now(timezone.utc)
    start = (
        datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        if start_date
        else end - timedelta(days=30)
    )
    return start, end


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    db: DBSessionDep,
    _user: DashboardUser,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
) -> AnalyticsOverview:
    start, end = _parse_date_range(start_date, end_date)
    period = DatePeriod(start_date=start.date().isoformat(), end_date=end.date().isoformat())

    total_conv = (await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.created_at >= start, Conversation.created_at <= end
        )
    )).scalar_one()

    total_msgs = (await db.execute(
        select(func.count(Message.id)).where(
            Message.created_at >= start, Message.created_at <= end
        )
    )).scalar_one()

    total_leads = (await db.execute(
        select(func.count(Lead.id)).where(
            Lead.created_at >= start, Lead.created_at <= end
        )
    )).scalar_one()

    handoff_count = (await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.status == "handoff",
            Conversation.created_at >= start,
            Conversation.created_at <= end,
        )
    )).scalar_one()

    avg_rating_row = (await db.execute(
        select(func.avg(AIFeedback.rating)).where(
            AIFeedback.created_at >= start, AIFeedback.created_at <= end
        )
    )).scalar_one_or_none()
    avg_rating = float(avg_rating_row) if avg_rating_row else 0.0

    lead_rate = (total_leads / total_conv) if total_conv > 0 else 0.0
    handoff_rate = (handoff_count / total_conv) if total_conv > 0 else 0.0

    service_rows = (await db.execute(
        select(Lead.service_interest, func.count(Lead.id).label("cnt"))
        .where(Lead.created_at >= start, Lead.created_at <= end, Lead.service_interest.isnot(None))
        .group_by(Lead.service_interest)
        .order_by(func.count(Lead.id).desc())
    )).all()
    popular_services = [ServiceCount(service=r[0], count=r[1]) for r in service_rows]

    lang_rows = (await db.execute(
        select(Conversation.language, func.count(Conversation.id).label("cnt"))
        .where(Conversation.created_at >= start, Conversation.created_at <= end, Conversation.language.isnot(None))
        .group_by(Conversation.language)
        .order_by(func.count(Conversation.id).desc())
    )).all()
    language_dist = [LanguageCount(language=r[0], count=r[1]) for r in lang_rows]

    return AnalyticsOverview(
        period=period,
        total_conversations=total_conv,
        total_messages=total_msgs,
        total_leads=total_leads,
        lead_conversion_rate=round(lead_rate, 2),
        handoff_rate=round(handoff_rate, 2),
        average_feedback_rating=round(avg_rating, 2),
        popular_services=popular_services,
        language_distribution=language_dist,
    )


@router.get("/popular-intents", response_model=PopularIntentsResponse)
async def popular_intents(
    db: DBSessionDep,
    _user: DashboardUser,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PopularIntentsResponse:
    start, end = _parse_date_range(start_date, end_date)
    period = DatePeriod(start_date=start.date().isoformat(), end_date=end.date().isoformat())

    rows = (await db.execute(
        select(Message.intent, func.count(Message.id).label("cnt"))
        .where(
            Message.intent.isnot(None),
            Message.created_at >= start,
            Message.created_at <= end,
        )
        .group_by(Message.intent)
        .order_by(func.count(Message.id).desc())
        .limit(limit)
    )).all()

    total_with_intent = sum(r[1] for r in rows)
    intents = [
        IntentStat(intent=r[0], count=r[1], percentage=round(r[1] / total_with_intent, 2) if total_with_intent else 0.0)
        for r in rows
    ]

    return PopularIntentsResponse(period=period, intents=intents)


@router.get("/failed-queries", response_model=PaginatedFailedQueries)
async def failed_queries(
    db: DBSessionDep,
    _user: DashboardUser,
    start_date: Annotated[str | None, Query()] = None,
    end_date: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedFailedQueries:
    start, end = _parse_date_range(start_date, end_date)

    base = select(Message).where(
        Message.role == "user",
        Message.created_at >= start,
        Message.created_at <= end,
        Message.confidence.isnot(None),
        Message.confidence < 0.5,
    )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    rows_stmt = base.order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(rows_stmt)).scalars().all()

    items: list[FailedQueryItem] = []
    for msg in rows:
        metadata = msg.metadata_json or {}
        items.append(
            FailedQueryItem(
                id=str(msg.id),
                conversation_id=str(msg.conversation_id),
                user_message=msg.content,
                intent=msg.intent,
                confidence=msg.confidence,
                handoff_triggered=metadata.get("handoff_triggered", False),
                handoff_reason=metadata.get("handoff_reason"),
                created_at=msg.created_at.isoformat(),
            )
        )

    return PaginatedFailedQueries(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )
