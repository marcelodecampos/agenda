from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from agenda.infrastructure.db import Base
from agenda.models.mixins import AuditVersionMixin


class FederativeUnit(AuditVersionMixin, Base):
    __tablename__ = "federative_unit"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7)
    ibge_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    abbreviation: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
