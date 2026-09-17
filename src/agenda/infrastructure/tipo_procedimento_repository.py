from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.tipo_procedimento import TipoProcedimento
from agenda.infrastructure.db import Base, criar_session


class TipoProcedimentoModel(Base):
    __tablename__ = "tipos_procedimento"
    __table_args__ = (UniqueConstraint("chave", name="uq_tipos_procedimento_chave"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chave: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, tipo: TipoProcedimento) -> "TipoProcedimentoModel":
        return cls(id=str(tipo.id), chave=tipo.chave, nome=tipo.nome)

    def to_domain(self) -> TipoProcedimento:
        return TipoProcedimento(id=uuid.UUID(self.id), chave=self.chave, nome=self.nome)


class TipoProcedimentoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, tipo: TipoProcedimento) -> TipoProcedimento:
        with criar_session(self.engine) as session:
            session.add(TipoProcedimentoModel.from_domain(tipo))
            session.commit()
        return tipo

    def atualizar(self, tipo: TipoProcedimento) -> TipoProcedimento:
        with criar_session(self.engine) as session:
            session.merge(TipoProcedimentoModel.from_domain(tipo))
            session.commit()
        return tipo

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(TipoProcedimentoModel).where(TipoProcedimentoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[TipoProcedimento]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(TipoProcedimentoModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> TipoProcedimento | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(TipoProcedimentoModel).where(TipoProcedimentoModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_chave(self, chave: str) -> TipoProcedimento | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(TipoProcedimentoModel).where(TipoProcedimentoModel.chave == chave)
            ).scalar_one_or_none()
            return row.to_domain() if row else None
