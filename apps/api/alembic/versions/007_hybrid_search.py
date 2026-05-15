"""Add search_tsvector column to knowledge_chunks for hybrid search.

Stores a tsvector representation of chunk_text for PostgreSQL full-text
search, enabling combined vector + keyword (BM25-style) retrieval.

Revision ID: 007_hybrid_search
Revises: 006_content_hash
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007_hybrid_search"
down_revision = "006_content_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_chunks",
        sa.Column("search_tsvector", sa.Text, nullable=True),
    )
    op.execute(
        """
        UPDATE knowledge_chunks
        SET search_tsvector = to_tsvector('english', chunk_text)
        WHERE chunk_text IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("knowledge_chunks", "search_tsvector")
