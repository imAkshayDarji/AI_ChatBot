"""Add leads.consent_at timestamp for GDPR hygiene.

Revision ID: 004_week6
Revises: 003_week4
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_week6"
down_revision = "003_week4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column(
            "consent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("leads", "consent_at")
