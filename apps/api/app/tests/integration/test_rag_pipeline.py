"""RAG ingestion and retrieval against PostgreSQL + pgvector."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.core.errors import ValidationDomainError
from app.db.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.rag.ingestion import IngestionService
from app.services.rag.retriever import RetrieverService

pytestmark = pytest.mark.integration


class _StubEmbeddings:
    dimensions = 3072

    async def embed_text(self, text: str) -> list[float]:
        return [0.01] * self.dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.01] * self.dimensions for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return await self.embed_text(query)


class _OrthogonalQueryEmbeddings:
    """Chunk vectors align with axis 0; query vectors align with axis 1 → cosine similarity 0."""

    dimensions = 3072

    async def embed_text(self, text: str) -> list[float]:
        return self._chunk_vector()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._chunk_vector() for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._query_vector()

    @staticmethod
    def _chunk_vector() -> list[float]:
        v = [0.0] * 3072
        v[0] = 1.0
        return v

    @staticmethod
    def _query_vector() -> list[float]:
        v = [0.0] * 3072
        v[1] = 1.0
        return v


@pytest.mark.asyncio
async def test_ingest_creates_chunks(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Tattoo Pricing",
            source_type="manual",
            language="en",
            content="Tattoo pricing guidance starts at ₹2000. " * 30,
            status="active",
            metadata_json={"service_type": "tattoo"},
        )
        session.add(doc)
        await session.flush()
        service = IngestionService(session, _StubEmbeddings())
        chunks = await service.ingest_document(doc)
        await session.commit()
        assert len(chunks) > 0
        for c in chunks:
            assert c.embedding is not None
            assert len(c.embedding) == 3072
            assert c.document_id == doc.id


@pytest.mark.asyncio
async def test_reingest_replaces_chunks(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Policy",
            source_type="manual",
            language="en",
            content="Original content " * 40,
            status="active",
        )
        session.add(doc)
        await session.flush()
        service = IngestionService(session, _StubEmbeddings())
        chunks_v1 = await service.ingest_document(doc)
        await session.commit()
        assert len(chunks_v1) > 0

    async with session_factory() as session:
        doc2 = await session.get(KnowledgeDocument, doc.id)
        assert doc2 is not None
        doc2.content = "Updated content " * 40
        service = IngestionService(session, _StubEmbeddings())
        chunks_v2 = await service.ingest_document(doc2)
        await session.commit()
        assert len(chunks_v2) > 0

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == doc.id),
        )
        assert count == len(chunks_v2)


@pytest.mark.asyncio
async def test_empty_content_raises(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Empty",
            source_type="manual",
            language="en",
            content="Will change",
            status="active",
        )
        session.add(doc)
        await session.flush()
        doc.content = "   "
        service = IngestionService(session, _StubEmbeddings())
        with pytest.raises(ValidationDomainError):
            await service.ingest_document(doc)


@pytest.mark.asyncio
async def test_knowledge_chunk_accepts_3072_embedding(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Vector smoke",
            source_type="manual",
            language="en",
            content="content",
            status="active",
        )
        session.add(doc)
        await session.flush()
        row = KnowledgeChunk(
            document_id=doc.id,
            chunk_text="smoke",
            chunk_index=0,
            service_type="general",
            language="en",
            embedding=[0.001] * 3072,
        )
        session.add(row)
        await session.commit()


@pytest.mark.asyncio
async def test_retrieve_tattoo_query(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Ink",
            source_type="manual",
            language="en",
            content="tattoo sleeve pricing and flash designs " * 20,
            status="active",
            metadata_json={"service_type": "tattoo"},
        )
        session.add(doc)
        await session.flush()
        await IngestionService(session, _StubEmbeddings()).ingest_document(doc)
        await session.commit()

    async with session_factory() as session:
        results = await RetrieverService(session, _StubEmbeddings()).retrieve(
            "How much for a small tattoo?",
            similarity_threshold=0.0,
            top_k=5,
        )
        assert len(results) > 0
        blob = " ".join(r.chunk_text.lower() for r in results)
        assert "tattoo" in blob


@pytest.mark.asyncio
async def test_retrieve_dreadlock_query(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Dreadlock care",
            source_type="manual",
            language="en",
            content="dreadlock maintenance retwist and washing tips " * 20,
            status="active",
            metadata_json={"service_type": "dreadlock"},
        )
        session.add(doc)
        await session.flush()
        await IngestionService(session, _StubEmbeddings()).ingest_document(doc)
        await session.commit()

    async with session_factory() as session:
        results = await RetrieverService(session, _StubEmbeddings()).retrieve(
            "How often should I retwist my locs?",
            similarity_threshold=0.0,
            top_k=5,
        )
        assert len(results) > 0
        blob = " ".join(r.chunk_text.lower() for r in results)
        assert "dreadlock" in blob or "retwist" in blob


@pytest.mark.asyncio
async def test_retrieve_hindi_query_english_chunks(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Aftercare EN",
            source_type="manual",
            language="en",
            content="tattoo aftercare keep the bandage on overnight " * 20,
            status="active",
            metadata_json={"service_type": "tattoo"},
        )
        session.add(doc)
        await session.flush()
        await IngestionService(session, _StubEmbeddings()).ingest_document(doc)
        await session.commit()

    async with session_factory() as session:
        results = await RetrieverService(session, _StubEmbeddings()).retrieve(
            "टैटू की देखभाल कैसे करें?",
            language="hi",
            similarity_threshold=0.0,
            top_k=5,
        )
        assert len(results) > 0
        blob = " ".join(r.chunk_text.lower() for r in results)
        assert "aftercare" in blob or "tattoo" in blob


@pytest.mark.asyncio
async def test_retrieve_high_similarity_threshold_returns_empty(session_factory) -> None:
    ortho = _OrthogonalQueryEmbeddings()
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Ortho doc",
            source_type="manual",
            language="en",
            content="any content " * 30,
            status="active",
        )
        session.add(doc)
        await session.flush()
        await IngestionService(session, ortho).ingest_document(doc)
        await session.commit()

    async with session_factory() as session:
        results = await RetrieverService(session, ortho).retrieve(
            "unrelated query text",
            similarity_threshold=0.99,
            top_k=5,
        )
        assert results == []


@pytest.mark.asyncio
async def test_retrieve_empty_corpus_returns_empty(session_factory) -> None:
    async with session_factory() as session:
        results = await RetrieverService(session, _StubEmbeddings()).retrieve(
            "quantum physics and black holes",
            similarity_threshold=0.0,
            top_k=5,
        )
        assert results == []


@pytest.mark.asyncio
async def test_retrieve_returns_chunks(session_factory) -> None:
    async with session_factory() as session:
        doc = KnowledgeDocument(
            title="Aftercare",
            source_type="manual",
            language="en",
            content="piercing aftercare: clean with saline daily " * 20,
            status="active",
            metadata_json={"service_type": "piercing"},
        )
        session.add(doc)
        await session.flush()
        await IngestionService(session, _StubEmbeddings()).ingest_document(doc)
        await session.commit()

    async with session_factory() as session:
        results = await RetrieverService(session, _StubEmbeddings()).retrieve(
            "How do I clean my new piercing?",
            similarity_threshold=0.0,
            top_k=5,
        )
        assert len(results) > 0
        joined = " ".join(r.chunk_text.lower() for r in results)
        assert "piercing" in joined or "clean" in joined


@pytest.mark.asyncio
async def test_retrieve_empty_query(session_factory) -> None:
    async with session_factory() as session:
        results = await RetrieverService(session, _StubEmbeddings()).retrieve("", top_k=5)
        assert results == []
        results_ws = await RetrieverService(session, _StubEmbeddings()).retrieve("  \n", top_k=5)
        assert results_ws == []
