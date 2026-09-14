from __future__ import annotations

import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.pacote import Pacote
from agenda.infrastructure.db import Base, criar_session


class PacoteModel(Base):
    __tablename__ = "pacotes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    servico_ids: Mapped[str] = mapped_column(String, nullable=False)
    duracao_total_minutos: Mapped[int] = mapped_column(nullable=False)
    preco: Mapped[str] = mapped_column(String, nullable=False)
    profissional_id: Mapped[str | None] = mapped_column(String, nullable=True)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, pacote: Pacote) -> "PacoteModel":
        return cls(
            id=str(pacote.id),
            nome=pacote.nome,
            servico_ids="|".join(str(item) for item in pacote.servico_ids),
            duracao_total_minutos=pacote.duracao_total_minutos,
            preco=str(pacote.preco),
            profissional_id=str(pacote.profissional_id) if pacote.profissional_id else None,
            organizacao_id=str(pacote.organizacao_id) if pacote.organizacao_id else None,
        )

    def to_domain(self) -> Pacote:
        servico_ids = tuple(
            uuid.UUID(item)
            for item in filter(None, self.servico_ids.split("|"))
        )
        return Pacote(
            id=uuid.UUID(self.id),
            nome=self.nome,
            servico_ids=servico_ids,
            duracao_total_minutos=self.duracao_total_minutos,
            preco=__import__("decimal").Decimal(self.preco),
            profissional_id=uuid.UUID(self.profissional_id) if self.profissional_id else None,
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
        )


class PacoteRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, pacote: Pacote) -> Pacote:
        with criar_session(self.engine) as session:
            session.add(PacoteModel.from_domain(pacote))
            session.commit()
        return pacote

    def atualizar(self, pacote: Pacote) -> Pacote:
        with criar_session(self.engine) as session:
            session.merge(PacoteModel.from_domain(pacote))
            session.commit()
        return pacote

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(PacoteModel).where(PacoteModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Pacote]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(PacoteModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Pacote | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(PacoteModel).where(PacoteModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None
