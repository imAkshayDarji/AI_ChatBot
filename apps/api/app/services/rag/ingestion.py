"""Knowledge document ingestion: clean → chunk → embed → transactional replace."""

from __future__ import annotations

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationDomainError
from app.db.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.rag.chunker import Chunk, Chunker
from app.services.rag.cleaner import clean_text
from app.services.rag.embeddings import SupportsEmbeddings

_VALID_SERVICE_TYPES = frozenset({"tattoo", "piercing", "dreadlock", "general"})


def _service_type_from_document(document: KnowledgeDocument) -> str:
    raw = None
    if document.metadata_json and isinstance(document.metadata_json, dict):
        candidate = document.metadata_json.get("service_type")
        if isinstance(candidate, str):
            raw = candidate
    if raw in _VALID_SERVICE_TYPES:
        return raw
    return "general"


class IngestionService:
    def __init__(
        self,
        db: AsyncSession,
        embedding_service: SupportsEmbeddings,
        *,
        chunker: Chunker | None = None,
    ) -> None:
        self._db = db
        self._embed = embedding_service
        self._chunker = chunker or Chunker()

    async def ingest_document(self, document: KnowledgeDocument) -> list[KnowledgeChunk]:
        if document.content is None or not str(document.content).strip():
            raise ValidationDomainError(
                "Knowledge document content is empty or whitespace-only; refusing to reindex",
            )

        cleaned = clean_text(document.content)
        if not cleaned.strip():
            raise ValidationDomainError("Knowledge document content is empty after cleaning")

        chunk_specs = self._build_chunks(document, cleaned)
        if not chunk_specs:
            raise ValidationDomainError("No searchable chunks produced from document content")

        texts = [c.text for c in chunk_specs]
        embeddings = await self._embed.embed_texts(texts)
        if len(embeddings) != len(texts):
            raise RuntimeError("Embedding provider returned unexpected result count")

        service_type = _service_type_from_document(document)
        language = document.language or "en"

        await self._db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id),
        )

        rows: list[KnowledgeChunk] = []
        for i, (spec, vector) in enumerate(zip(chunk_specs, embeddings, strict=True)):
            row = KnowledgeChunk(
                document_id=document.id,
                chunk_text=spec.text,
                chunk_index=i,
                service_type=service_type,
                language=language,
                embedding=vector,
            )
            self._db.add(row)
            rows.append(row)

        await self._db.flush()
        for row in rows:
            await self._db.refresh(row)
        return rows

    async def delete_document_chunks(self, document_id: uuid.UUID) -> int:
        result = await self._db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id),
        )
        rc = result.rowcount
        if rc is None:
            return 0
        return int(rc)

    def _build_chunks(self, document: KnowledgeDocument, cleaned: str) -> list[Chunk]:
        meta: dict[str, object] = {}
        if document.metadata_json and isinstance(document.metadata_json, dict):
            st = document.metadata_json.get("service_type")
            if isinstance(st, str) and st in _VALID_SERVICE_TYPES:
                meta["service_type"] = st

        if document.source_type == "faq" and document.metadata_json:
            items = document.metadata_json.get("faq_items")
            if isinstance(items, list) and items:
                return self._chunker.chunk_faq(items)

        return self._chunker.chunk_text(cleaned, metadata=meta or None)
