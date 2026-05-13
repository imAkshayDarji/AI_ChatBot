"""Public lead submissions."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import DBSessionDep
from app.schemas.leads import LeadCreateRequest, LeadResponse
from app.services.analytics.tracker import AnalyticsTracker
from app.services.leads.service import LeadCreate, LeadService

router = APIRouter(prefix="/leads", tags=["leads"])

_lead_svc = LeadService()


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_public_lead(body: LeadCreateRequest, db: DBSessionDep) -> LeadResponse:
    lead = await _lead_svc.create_lead(
        db,
        LeadCreate(
            name=body.name,
            email=str(body.email),
            phone=body.phone,
            preferred_language=body.preferred_language,
            service_interest=body.service_interest,
            budget_range=body.budget_range,
            placement=body.placement,
            style_preference=body.style_preference,
            notes=body.notes,
            source=body.source or "website",
            conversation_context=None,
        ),
    )

    tracker = AnalyticsTracker()
    await tracker.track_lead_created(db, lead.id, lead.source or "website")

    return LeadResponse.model_validate(lead)


__all__ = ["router"]
