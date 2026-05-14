"""Admin leads management routes."""

from __future__ import annotations

import math
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select

from app.api.deps import DashboardUser, OwnerAdminUser, DBSessionDep
from app.core.errors import NotFoundError, ValidationDomainError
from app.db.models.lead import Lead
from app.schemas.admin_leads import (
    AdminLeadResponse,
    AdminLeadUpdateRequest,
    PaginatedLeadsResponse,
)

router = APIRouter(prefix="/admin/leads", tags=["admin-leads"])

_VALID_STATUSES = frozenset({"new", "contacted", "consultation_booked", "converted", "closed"})


@router.get("", response_model=PaginatedLeadsResponse)
async def list_leads(
    db: DBSessionDep,
    _user: DashboardUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[str | None, Query()] = None,
    service_interest: Annotated[str | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[str, Query()] = "desc",
) -> PaginatedLeadsResponse:
    if status is not None and status not in _VALID_STATUSES:
        raise ValidationDomainError(f"Invalid status filter: {status}")

    base = select(Lead)
    if status is not None:
        base = base.where(Lead.status == status)
    if service_interest is not None:
        base = base.where(Lead.service_interest == service_interest)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    order_col = Lead.created_at if sort_by == "created_at" else Lead.updated_at
    order = order_col.desc() if sort_order == "desc" else order_col.asc()

    stmt = base.order_by(order).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    return PaginatedLeadsResponse(
        items=[AdminLeadResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/{lead_id}", response_model=AdminLeadResponse)
async def get_lead(
    lead_id: UUID,
    db: DBSessionDep,
    _user: DashboardUser,
) -> AdminLeadResponse:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead not found")
    return AdminLeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=AdminLeadResponse)
async def update_lead(
    lead_id: UUID,
    body: AdminLeadUpdateRequest,
    db: DBSessionDep,
    _user: DashboardUser,
) -> AdminLeadResponse:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead not found")

    if body.status is not None:
        if body.status not in _VALID_STATUSES:
            raise ValidationDomainError(f"Invalid status: {body.status}")
        lead.status = body.status
    if body.notes is not None:
        lead.notes = body.notes

    await db.flush()
    await db.refresh(lead)
    return AdminLeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=204, response_class=Response)
async def delete_lead(
    lead_id: UUID,
    db: DBSessionDep,
    _user: OwnerAdminUser,
) -> Response:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError("Lead not found")
    await db.delete(lead)
    await db.flush()
    return Response(status_code=204)
