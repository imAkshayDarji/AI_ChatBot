import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"

    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'consultation_booked', 'converted', 'closed')",
            name="leads_status_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        server_default=text("'en'"),
    )
    service_interest: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    placement: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_preference: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'new'"),
        index=True,
    )
    source: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        server_default=text("'chat'"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
        onupdate=func.now(),
    )
