"""Vector similarity retrieval over knowledge_chunks (pgvector cosine)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.rag.embeddings import SupportsEmbeddings


@dataclass
class RetrievalResult:
    chunk_id: UUID
    document_id: UUID
    chunk_text: str
    score: float
    service_type: str
    language: str
    source_title: str


def _vector_literal(values: list[float]) -> str:
    inner = ",".join(f"{float(v):.8g}" for v in values)
    return f"[{inner}]"


class RetrieverService:
    """All RAG retrieval MUST go through this service (PLAN.md §1.5)."""

    def __init__(self, db: AsyncSession, embedding_service: SupportsEmbeddings) -> None:
        self._db = db
        self._embed = embedding_service

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        language: str = "en",
        service_type: str | None = None,
        similarity_threshold: float = 0.15,
    ) -> list[RetrievalResult]:
        if not query or not query.strip():
            return []

        query_embedding = await self._embed.embed_query(query.strip())
        emb = _vector_literal(query_embedding)
        has_stype = service_type is not None
        stype = service_type or ""

        fetch_cap = max(top_k * 8, top_k + 16, 32)

        sql = text(
            """
            WITH vector_scores AS (
                SELECT kc.id AS chunk_id,
                       kc.document_id AS document_id,
                       kc.chunk_text AS chunk_text,
                       kc.service_type AS service_type,
                       coalesce(kc.language, 'en') AS language,
                       kd.title AS source_title,
                       (1 - (kc.embedding <=> CAST(:emb AS halfvec))) AS vec_score
                FROM knowledge_chunks kc
                INNER JOIN knowledge_documents kd ON kc.document_id = kd.id
                WHERE kd.status = 'active'
                  AND kc.embedding IS NOT NULL
                  AND (
                    coalesce(kc.language, 'en') = :lang
                    OR coalesce(kc.language, 'en') = 'en'
                  )
                  AND (NOT :has_stype OR kc.service_type = :stype)
            ),
            ranked AS (
                SELECT vs.*,
                       coalesce(ts_rank_cd(
                           to_tsvector('english', vs.chunk_text),
                           plainto_tsquery('english', :query_text)
                       ), 0) AS fts_score
                FROM vector_scores vs
            )
            SELECT chunk_id,
                   document_id,
                   chunk_text,
                   service_type,
                   language,
                   source_title,
                   (0.7 * vec_score + 0.3 * fts_score) AS score
            FROM ranked
            ORDER BY score DESC
            LIMIT :lim_p
            """
        )

        rows = (
            (
                await self._db.execute(
                    sql,
                    {
                        "emb": emb,
                        "lang": language,
                        "has_stype": has_stype,
                        "stype": stype,
                        "lim_p": fetch_cap,
                        "query_text": query.strip(),
                    },
                )
            )
            .mappings()
            .all()
        )

        results: list[RetrievalResult] = []
        for row in rows:
            score = float(row["score"])
            if score < similarity_threshold:
                continue
            results.append(
                RetrievalResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    chunk_text=str(row["chunk_text"]),
                    score=score,
                    service_type=str(row["service_type"]),
                    language=str(row["language"]),
                    source_title=str(row["source_title"]),
                ),
            )
            if len(results) >= top_k:
                break
        return results
