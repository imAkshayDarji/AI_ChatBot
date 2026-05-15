"""Switch embedding column to halfvec(3072) and create HNSW index.

pgvector's HNSW index supports at most 2000 dimensions on the `vector` type,
but the `halfvec` type (16-bit float) supports up to 4000 dimensions.

This migration:
1. Drops any existing index on the embedding column
2. Deletes all knowledge_chunks rows (can't cast vector to halfvec in-place)
3. Changes the column type from vector(3072) to halfvec(3072)
4. Creates an HNSW index with halfvec_cosine_ops

Reindex all knowledge documents after running this migration.

Revision ID: 005_halfvec
Revises: 004_week6
Create Date: 2026-05-15
"""

from __future__ import annotations

from alembic import op

revision = "005_halfvec"
down_revision = "004_week6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_ivfflat")
    op.execute("DELETE FROM knowledge_chunks")
    op.execute(
        "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE halfvec(3072)"
    )
    op.execute(
        """
        CREATE INDEX ix_knowledge_chunks_embedding_hnsw
        ON knowledge_chunks USING hnsw (embedding halfvec_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("DELETE FROM knowledge_chunks")
    op.execute(
        "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE vector(3072)"
    )
