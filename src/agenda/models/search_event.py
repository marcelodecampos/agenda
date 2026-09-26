from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from agenda.infrastructure.db import Base


class SearchEvent(Base):
    __tablename__ = "search_event"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7, server_default=text("uuidv7()"))
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    # INSERT, UPDATE ou DELETE
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, server_default=func.now())
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
