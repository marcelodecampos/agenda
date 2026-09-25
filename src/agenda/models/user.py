from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Uuid, and_, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship
from uuid6 import uuid7

from agenda.infrastructure.db import Base
from agenda.models.mixins import AuditVersionMixin

if TYPE_CHECKING:
    from agenda.models.address import Address


class PersonType(StrEnum):
    PERSON = "person"
    COMPANY = "company"


class BaseUser(AuditVersionMixin, Base):
    __tablename__ = "base_user"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid7)
    person_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped["Address | None"] = relationship(
        back_populates="base_user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, object]:
        return {
            "polymorphic_on": cls.person_type,
            "polymorphic_identity": "base_user",
            "version_id_col": cls.version,
        }


class Person(BaseUser):
    __tablename__ = "person"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("base_user.id"), primary_key=True
    )
    cpf: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    responsible_links: Mapped[list["CompanyResponsible"]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
    )
    companies: Mapped[list["Company"]] = relationship(
        "Company",
        secondary="company_responsible",
        primaryjoin=lambda: and_(
            Person.id == CompanyResponsible.person_id,
            CompanyResponsible.end_date.is_(None),
        ),
        secondaryjoin=lambda: Company.id == CompanyResponsible.company_id,
        viewonly=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": PersonType.PERSON.value,
    }


class Company(BaseUser):
    __tablename__ = "company"

    id: Mapped[UUID] = mapped_column(
        ForeignKey("base_user.id"), primary_key=True
    )
    cnpj: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    responsible_links: Mapped[list["CompanyResponsible"]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
    )
    responsibles: Mapped[list["Person"]] = relationship(
        "Person",
        secondary="company_responsible",
        primaryjoin=lambda: and_(
            Company.id == CompanyResponsible.company_id,
            CompanyResponsible.end_date.is_(None),
        ),
        secondaryjoin=lambda: Person.id == CompanyResponsible.person_id,
        viewonly=True,
    )

    __mapper_args__ = {
        "polymorphic_identity": PersonType.COMPANY.value,
    }


class CompanyResponsible(AuditVersionMixin, Base):
    __tablename__ = "company_responsible"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="company_responsible_end_date_check",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("company.id"), primary_key=True
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id"), primary_key=True
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
        default=date.today,
        server_default=func.current_date(),
    )
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    company: Mapped[Company] = relationship(back_populates="responsible_links")
    person: Mapped[Person] = relationship(back_populates="responsible_links")
