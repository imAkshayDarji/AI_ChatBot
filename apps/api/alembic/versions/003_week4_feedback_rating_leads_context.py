"""Widen ai_feedback rating 1-5; add leads.conversation_context.

Revision ID: 003_week4
Revises: 002_embedding_3072
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_week4"
down_revision = "002_embedding_3072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ai_feedback_rating_check", "ai_feedback", type_="check")
    op.create_check_constraint(
        "ai_feedback_rating_check",
        "ai_feedback",
        "rating IN (1, 2, 3, 4, 5)",
    )
    op.add_column("leads", sa.Column("conversation_context", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "conversation_context")
    op.drop_constraint("ai_feedback_rating_check", "ai_feedback", type_="check")
    op.create_check_constraint(
        "ai_feedback_rating_check",
        "ai_feedback",
        "rating IN (1, 2)",
    )
