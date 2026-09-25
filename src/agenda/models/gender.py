from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from agenda.infrastructure.db import Base
from agenda.models.mixins import AuditVersionMixin


class Gender(AuditVersionMixin, Base):
    __tablename__ = "gender"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7)
    description: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
