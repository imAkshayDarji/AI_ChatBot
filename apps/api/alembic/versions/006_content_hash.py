"""Add content_hash to knowledge_documents for idempotent reindexing.

Stores SHA-256 hash of document content so ingestion can skip
documents whose content hasn't changed, saving OpenAI embedding costs.

Revision ID: 006_content_hash
Revises: 005_halfvec
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "006_content_hash"
down_revision = "005_halfvec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents",
        sa.Column("content_hash", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "content_hash")
