"""Persistence helpers for conversational memory."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.services.ai.provider import AIProvider

_IDLE = timedelta(minutes=30)


class MemoryService:
    MAX_HISTORY_MESSAGES = 12

    def __init__(self, ai_provider: AIProvider | None = None) -> None:
        self._ai = ai_provider

    async def _maybe_mark_idle_ended(self, db: AsyncSession, conversation_id: uuid.UUID) -> None:
        conv = (
            await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        ).scalar_one_or_none()
        if conv is None or conv.status != "active":
            return

        cutoff = datetime.now(tz=UTC) - _IDLE

        stmt_mx = select(func.max(Message.created_at)).where(
            Message.conversation_id == conversation_id,
        )
        last_ts = (await db.execute(stmt_mx)).scalar_one_or_none()

        anchor_dt = last_ts if last_ts is not None else conv.updated_at
        normalized = anchor_dt if anchor_dt.tzinfo else anchor_dt.replace(tzinfo=UTC)
        if normalized < cutoff:
            conv.status = "ended"
            await db.commit()

    async def get_conversation_history(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        limit: int = 12,
    ) -> list[dict[str, str]]:
        stmt: Select[tuple[Message]] = (
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != "system")
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).scalars().all()
        rows = list(reversed(rows))
        return [{"role": m.role, "content": m.content} for m in rows]

    async def get_or_create_conversation(
        self,
        db: AsyncSession,
        session_id: str,
        language: str = "en",
    ) -> Conversation:
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            await self._maybe_mark_idle_ended(db, existing.id)

            refreshed = (
                await db.execute(select(Conversation).where(Conversation.id == existing.id))
            ).scalar_one()
            if refreshed.status == "ended":
                refreshed.status = "active"
                refreshed.language = language
                await db.commit()
                await db.refresh(refreshed)
            return refreshed

        conv = Conversation(session_id=session_id, language=language, status="active")
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    async def store_message(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        intent: str | None = None,
        confidence: float | None = None,
        metadata: dict | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            confidence=confidence,
            metadata_json=metadata,
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    async def summarize_if_needed(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
    ) -> str | None:
        count_stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
            )
        )
        total = int((await db.execute(count_stmt)).scalar_one())
        if total <= 20 or self._ai is None:
            return None

        conv = (
            await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        ).scalar_one_or_none()
        if conv is None:
            return None
        if conv.summary:
            return conv.summary

        history = await self.get_conversation_history(
            db,
            conversation_id,
            limit=min(total, 30),
        )
        lines = [f"{m['role']}: {m['content']}" for m in history]
        system_summary = (
            "Summarize the conversation in 3-5 bullet points for the next assistant turn."
        )
        prompt = [
            {
                "role": "system",
                "content": system_summary,
            },
            {"role": "user", "content": "\n".join(lines)},
        ]
        response = await self._ai.chat(prompt, temperature=0.3, max_tokens=400)
        summary = response.content.strip()
        conv.summary = summary
        await db.commit()
        return summary
