from uuid import UUID

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid6 import uuid7

from agenda.infrastructure.db import Base
from agenda.models.federative_unit import FederativeUnit
from agenda.models.mixins import AuditVersionMixin


class Municipality(AuditVersionMixin, Base):
    __tablename__ = "municipality"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7)
    ibge_code: Mapped[str] = mapped_column(String(7), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    search_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    federative_unit_id: Mapped[UUID] = mapped_column(
        ForeignKey("federative_unit.id"), nullable=False
    )

    federative_unit: Mapped[FederativeUnit] = relationship()
