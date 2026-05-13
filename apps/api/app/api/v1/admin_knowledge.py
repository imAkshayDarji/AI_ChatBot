"""Knowledge document admin CRUD and reindex."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import DashboardUser, DBSessionDep, IngestionServiceDep
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
    pagination_params,
)
from app.services import knowledge_document_service
from app.services.audit import append_audit_log

router = APIRouter(prefix="/admin/knowledge", tags=["admin-knowledge"])


@router.get("", response_model=list[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    db: DBSessionDep,
    user: DashboardUser,
    paging: Annotated[tuple[int, int], Depends(pagination_params)],
    status: Annotated[str | None, Query()] = None,
) -> list[KnowledgeDocumentResponse]:
    skip, limit = paging
    rows = await knowledge_document_service.list_documents(
        db, skip=skip, limit=limit, status=status
    )
    return [KnowledgeDocumentResponse.model_validate(row) for row in rows]


@router.post("", response_model=KnowledgeDocumentResponse, status_code=201)
async def create_knowledge_document(
    db: DBSessionDep,
    user: DashboardUser,
    body: KnowledgeDocumentCreate,
    ingestion: IngestionServiceDep,
) -> KnowledgeDocumentResponse:
    doc = await knowledge_document_service.create_document(db, body)
    await append_audit_log(
        db,
        user_id=user.id,
        action="create",
        entity_type="knowledge_document",
        entity_id=doc.id,
        changes_json={"title": doc.title},
    )
    if body.status == "active":
        await ingestion.ingest_document(doc)
    await db.commit()
    await db.refresh(doc)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_knowledge_document(
    document_id: UUID,
    db: DBSessionDep,
    user: DashboardUser,
) -> KnowledgeDocumentResponse:
    doc = await knowledge_document_service.get_document_or_404(db, document_id)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.patch("/{document_id}", response_model=KnowledgeDocumentResponse)
async def update_knowledge_document(
    document_id: UUID,
    db: DBSessionDep,
    user: DashboardUser,
    body: KnowledgeDocumentUpdate,
    ingestion: IngestionServiceDep,
) -> KnowledgeDocumentResponse:
    doc = await knowledge_document_service.update_document(db, document_id, body)
    await append_audit_log(
        db,
        user_id=user.id,
        action="update",
        entity_type="knowledge_document",
        entity_id=document_id,
        changes_json=body.model_dump(exclude_unset=True, mode="json"),
    )
    if doc.status == "active":
        await ingestion.ingest_document(doc)
    await db.commit()
    await db.refresh(doc)
    return KnowledgeDocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=204)
async def delete_knowledge_document(
    document_id: UUID,
    db: DBSessionDep,
    user: DashboardUser,
) -> None:
    await knowledge_document_service.delete_document(db, document_id)
    await append_audit_log(
        db,
        user_id=user.id,
        action="delete",
        entity_type="knowledge_document",
        entity_id=document_id,
        changes_json=None,
    )
    await db.commit()


@router.post("/{document_id}/reindex")
async def reindex_knowledge_document(
    document_id: UUID,
    db: DBSessionDep,
    user: DashboardUser,
    ingestion: IngestionServiceDep,
) -> dict[str, object]:
    document = await knowledge_document_service.get_document_or_404(db, document_id)
    chunks = await ingestion.ingest_document(document)
    await append_audit_log(
        db,
        user_id=user.id,
        action="reindex_completed",
        entity_type="knowledge_document",
        entity_id=document_id,
        changes_json={"chunk_count": len(chunks)},
    )
    await db.commit()
    return {
        "message": f"Indexed {len(chunks)} chunks",
        "document_id": str(document_id),
        "chunk_count": len(chunks),
    }
