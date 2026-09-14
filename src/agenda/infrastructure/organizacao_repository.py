from __future__ import annotations

import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.endereco import Endereco
from agenda.domain.organizacao import Organizacao
from agenda.infrastructure.db import Base, criar_session


class OrganizacaoModel(Base):
    __tablename__ = "organizacoes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    unipessoal: Mapped[bool] = mapped_column(default=False)
    endereco_logradouro: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_estado: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_cep: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, organizacao: Organizacao) -> "OrganizacaoModel":
        endereco = organizacao.endereco
        return cls(
            id=str(organizacao.id),
            nome=organizacao.nome,
            unipessoal=organizacao.unipessoal,
            endereco_logradouro=endereco.logradouro if endereco else None,
            endereco_numero=endereco.numero if endereco else None,
            endereco_cidade=endereco.cidade if endereco else None,
            endereco_estado=endereco.estado if endereco else None,
            endereco_cep=endereco.cep if endereco else None,
        )

    def to_domain(self) -> Organizacao:
        if self.endereco_logradouro is None:
            endereco = None
        else:
            endereco = Endereco(
                logradouro=self.endereco_logradouro,
                numero=self.endereco_numero or "",
                cidade=self.endereco_cidade or "",
                estado=self.endereco_estado or "",
                cep=self.endereco_cep or "",
            )
        return Organizacao(
            id=uuid.UUID(self.id),
            nome=self.nome,
            unipessoal=self.unipessoal,
            endereco=endereco,
        )


class OrganizacaoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, organizacao: Organizacao) -> Organizacao:
        with criar_session(self.engine) as session:
            session.add(OrganizacaoModel.from_domain(organizacao))
            session.commit()
        return organizacao

    def atualizar(self, organizacao: Organizacao) -> Organizacao:
        with criar_session(self.engine) as session:
            session.merge(OrganizacaoModel.from_domain(organizacao))
            session.commit()
        return organizacao

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(OrganizacaoModel).where(OrganizacaoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Organizacao]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(OrganizacaoModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Organizacao | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(OrganizacaoModel).where(OrganizacaoModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None
