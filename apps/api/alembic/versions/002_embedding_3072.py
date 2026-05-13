"""Align knowledge_chunks.embedding with text-embedding-3-large (3072 dims).

Revision ID: 002_embedding_3072
Revises: 001_week2
Create Date: 2026-05-13

Destructive: deletes all rows in knowledge_chunks so the column type can change.
Existing 1536-dim vectors cannot be cast to 3072; reindex documents after migrating.
"""

from __future__ import annotations

from alembic import op

revision = "002_embedding_3072"
down_revision = "001_week2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("DELETE FROM knowledge_chunks")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(3072)")
    # HNSW index supports at most 2000 dimensions in current pgvector builds.
    # Add IVFFlat or another index after backfilling chunks, or rely on sequential scans for MVP scale.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_ivfflat")
    op.execute("DELETE FROM knowledge_chunks")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(1536)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw
        ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
        """
    )
