from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from agenda.infrastructure.db import Base
from agenda.models.mixins import AuditVersionMixin


class PostalCodeCache(AuditVersionMixin, Base):
    __tablename__ = "postal_code_cache"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7)
    postal_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    street_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(150), nullable=True)
    federative_unit: Mapped[str | None] = mapped_column(String(2), nullable=True)
    ibge_code: Mapped[str | None] = mapped_column(String(7), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
