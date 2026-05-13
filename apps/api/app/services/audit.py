"""Append-only audit log helper for optional admin auditing."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog


async def append_audit_log(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    changes_json: dict[str, Any] | None,
) -> None:
    session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes_json=changes_json,
        )
    )
    await session.flush()
