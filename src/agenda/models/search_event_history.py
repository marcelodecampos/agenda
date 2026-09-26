from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from agenda.infrastructure.db import Base


class SearchEventHistory(Base):
    __tablename__ = "search_event_history"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7)
    event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
