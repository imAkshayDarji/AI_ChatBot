"""CRUD + status transitions for knowledge documents."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import KnowledgeStatusTransitionError, NotFoundError, ValidationDomainError
from app.db.models.knowledge import KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentCreate, KnowledgeDocumentUpdate

_VALID_SOURCE_TYPES = frozenset({"manual", "website", "pdf", "faq"})
_VALID_STATUSES = frozenset({"draft", "active", "archived"})


def _assert_valid_source_type(source_type: str) -> None:
    if source_type not in _VALID_SOURCE_TYPES:
        raise ValidationDomainError(f"Invalid source_type: {source_type}")


def validate_knowledge_status_transition(current: str, target: str) -> None:
    if target not in _VALID_STATUSES:
        raise KnowledgeStatusTransitionError(f"Invalid status: {target}")

    transitions: dict[str, tuple[str, ...]] = {
        "draft": ("active",),
        "active": ("archived",),
        "archived": ("active",),
    }
    allowed = transitions.get(current, ())
    if target == current:
        return
    if target not in allowed:
        raise KnowledgeStatusTransitionError(
            f"Illegal transition from '{current}' to '{target}'. "
            f"Publish via draft→active before archiving.",
        )


async def create_document(
    session: AsyncSession,
    data: KnowledgeDocumentCreate,
) -> KnowledgeDocument:
    if data.status not in _VALID_STATUSES:
        raise ValidationDomainError(f"Invalid initial status: {data.status}")

    _assert_valid_source_type(data.source_type)

    doc = KnowledgeDocument(
        title=data.title,
        source_type=data.source_type,
        language=data.language,
        content=data.content,
        status=data.status,
        source_url=data.source_url,
        metadata_json=data.metadata_json,
    )
    session.add(doc)
    await session.flush()
    await session.refresh(doc)
    return doc


async def get_document_or_404(session: AsyncSession, document_id: uuid.UUID) -> KnowledgeDocument:
    row = await session.get(KnowledgeDocument, document_id)
    if row is None:
        raise NotFoundError("Knowledge document not found")
    return row


async def list_documents(
    session: AsyncSession,
    *,
    skip: int,
    limit: int,
    status: str | None,
) -> list[KnowledgeDocument]:
    clamped_skip = max(0, skip)
    clamped_limit = min(max(1, limit), 100)

    stmt = select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())

    if status is not None:
        stmt = stmt.where(KnowledgeDocument.status == status)

    stmt = stmt.offset(clamped_skip).limit(clamped_limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_documents(session: AsyncSession, *, status: str | None) -> int:
    stmt = select(func.count(KnowledgeDocument.id))
    if status is not None:
        stmt = stmt.where(KnowledgeDocument.status == status)
    row = await session.execute(stmt)
    return int(row.scalar_one())


async def update_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    data: KnowledgeDocumentUpdate,
) -> KnowledgeDocument:
    doc = await get_document_or_404(session, document_id)

    if data.title is not None:
        doc.title = data.title
    if data.source_type is not None:
        _assert_valid_source_type(data.source_type)
        doc.source_type = data.source_type
    if data.language is not None:
        doc.language = data.language
    if data.content is not None:
        doc.content = data.content
    if data.source_url is not None:
        doc.source_url = data.source_url
    if data.metadata_json is not None:
        doc.metadata_json = data.metadata_json
    if data.status is not None:
        validate_knowledge_status_transition(doc.status, data.status)
        doc.status = data.status

    await session.flush()
    await session.refresh(doc)
    return doc


async def delete_document(session: AsyncSession, document_id: uuid.UUID) -> None:
    doc = await get_document_or_404(session, document_id)
    await session.delete(doc)
    await session.flush()
