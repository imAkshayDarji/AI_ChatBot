"""Lead persistence orchestration."""

from __future__ import annotations

import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.lead import Lead
from app.services.leads.extractor import LeadExtractor


class LeadCreate(BaseModel):
    model_config = {"frozen": False}

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    preferred_language: str = "en"
    service_interest: str | None = None
    budget_range: str | None = None
    placement: str | None = None
    style_preference: str | None = None
    notes: str | None = None
    source: str | None = "chat"
    conversation_context: str | None = None


class LeadUpdate(BaseModel):
    model_config = {"frozen": False}

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
    service_interest: str | None = None
    budget_range: str | None = None
    placement: str | None = None
    style_preference: str | None = None
    notes: str | None = None
    status: str | None = None


class LeadService:
    async def create_lead(self, db: AsyncSession, data: LeadCreate) -> Lead:
        lead = Lead(
            name=data.name,
            email=str(data.email) if data.email is not None else None,
            phone=data.phone,
            preferred_language=data.preferred_language,
            service_interest=data.service_interest,
            budget_range=data.budget_range,
            placement=data.placement,
            style_preference=data.style_preference,
            notes=data.notes,
            source=data.source or "chat",
            conversation_context=data.conversation_context,
            status="new",
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead

    async def update_lead(
        self,
        db: AsyncSession,
        lead_id: uuid.UUID,
        data: LeadUpdate,
    ) -> Lead | None:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
        if lead is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "email" and value is not None:
                setattr(lead, field, str(value))
            elif value is not None:
                setattr(lead, field, value)
        await db.commit()
        await db.refresh(lead)
        return lead

    async def get_lead(self, db: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_leads(
        self,
        db: AsyncSession,
        skip: int,
        limit: int,
        status: str | None,
    ) -> list[Lead]:
        stmt = select(Lead).order_by(Lead.created_at.desc()).offset(skip).limit(limit)
        if status:
            stmt = stmt.where(Lead.status == status)
        return list((await db.execute(stmt)).scalars().all())

    async def link_to_conversation(
        self,
        db: AsyncSession,
        lead_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> None:
        conv = (
            await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        ).scalar_one_or_none()
        if conv is None:
            raise ValueError("conversation_missing")
        conv.lead_id = lead_id
        await db.commit()

    async def extract_and_create_lead(
        self,
        db: AsyncSession,
        extractor: LeadExtractor,
        message: str,
        conversation_id: uuid.UUID,
        history: list[dict[str, str]],
    ) -> Lead | None:
        data = await extractor.extract_from_message(message, history)
        if data is None:
            return None
        lead = await self.create_lead(
            db,
            LeadCreate(
                name=data.name,
                email=data.email if data.email else None,
                phone=data.phone,
                service_interest=data.service_interest,
                budget_range=data.budget_range,
                placement=data.placement,
                style_preference=data.style_preference,
                conversation_context=data.conversation_context,
                source="chat",
            ),
        )
        await self.link_to_conversation(db, lead.id, conversation_id)
        return lead
