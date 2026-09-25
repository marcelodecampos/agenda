from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agenda.infrastructure.db import Base
from agenda.models.mixins import AuditVersionMixin
from agenda.models.municipality import Municipality

if TYPE_CHECKING:
    from agenda.models.user import BaseUser


class Address(AuditVersionMixin, Base):
    __tablename__ = "address"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("base_user.id"), primary_key=True
    )
    postal_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    street_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    street_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    street_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    municipality_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("municipality.id"), nullable=True
    )
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6), nullable=True
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6), nullable=True
    )

    base_user: Mapped["BaseUser"] = relationship(back_populates="address")
    municipality: Mapped[Municipality | None] = relationship()
