from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.comissao import RegraComissao
from agenda.infrastructure.db import Base, criar_session


class RegraComissaoModel(Base):
    __tablename__ = "regras_comissao"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[str] = mapped_column(String, nullable=False)
    membership_id: Mapped[str | None] = mapped_column(String, nullable=True)
    servico_id: Mapped[str | None] = mapped_column(String, nullable=True)

    def to_domain(self) -> RegraComissao:
        return RegraComissao(
            id=uuid.UUID(self.id),
            tipo=self.tipo,
            valor=Decimal(self.valor),
            membership_id=uuid.UUID(self.membership_id) if self.membership_id else None,
            servico_id=uuid.UUID(self.servico_id) if self.servico_id else None,
        )


class RegraComissaoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, regra: RegraComissao) -> RegraComissao:
        with criar_session(self.engine) as session:
            session.merge(
                RegraComissaoModel(
                    id=str(regra.id),
                    tipo=regra.tipo,
                    valor=str(regra.valor),
                    membership_id=str(regra.membership_id) if regra.membership_id else None,
                    servico_id=str(regra.servico_id) if regra.servico_id else None,
                )
            )
            session.commit()
        return regra

    def listar(self) -> list[RegraComissao]:
        with criar_session(self.engine) as session:
            return [
                row.to_domain()
                for row in session.execute(select(RegraComissaoModel)).scalars().all()
            ]

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(RegraComissaoModel).where(RegraComissaoModel.id == str(id_))
            ).scalar_one_or_none()
            if row:
                session.delete(row)
                session.commit()