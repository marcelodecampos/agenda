from __future__ import annotations

import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.endereco import Cliente, Endereco
from agenda.infrastructure.db import Base, criar_session
from agenda.infrastructure.endereco_repository import CadastroModel, obter_endereco, salvar_endereco


class ClienteModel(Base):
    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    usuario_id: Mapped[str | None] = mapped_column(String, nullable=True)
    segmento: Mapped[str | None] = mapped_column(String, nullable=True)
    telefone: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(11), nullable=True)
    endereco_logradouro: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_estado: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_cep: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, cliente: Cliente) -> "ClienteModel":
        endereco = cliente.endereco
        return cls(
            id=str(cliente.id),
            nome=cliente.nome,
            usuario_id=str(cliente.usuario_id) if cliente.usuario_id else None,
            segmento=cliente.segmento,
            telefone=cliente.telefone,
            email=cliente.email,
            cpf=cliente.cpf,
            endereco_logradouro=endereco.logradouro if endereco else None,
            endereco_numero=endereco.numero if endereco else None,
            endereco_cidade=endereco.cidade if endereco else None,
            endereco_estado=endereco.estado if endereco else None,
            endereco_cep=endereco.cep if endereco else None,
            endereco_id=str(cliente.id) if endereco else None,
        )

    def to_domain(self) -> Cliente:
        endereco = None
        if self.endereco_logradouro is not None:
            endereco = Endereco(
                self.endereco_logradouro,
                self.endereco_numero or "",
                self.endereco_cidade or "",
                self.endereco_estado or "",
                self.endereco_cep or "",
            )
        return Cliente(
            id=uuid.UUID(self.id),
            nome=self.nome,
            usuario_id=uuid.UUID(self.usuario_id) if self.usuario_id else None,
            segmento=self.segmento,
            telefone=self.telefone,
            email=self.email,
            cpf=self.cpf,
            endereco=endereco,
        )


class ClienteRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, cliente: Cliente) -> Cliente:
        with criar_session(self.engine) as session:
            session.add(ClienteModel.from_domain(cliente))
            session.merge(CadastroModel(id=str(cliente.id), tipo="cliente"))
            if cliente.endereco:
                salvar_endereco(session, str(cliente.id), cliente.endereco, municipio_id=str(cliente.endereco.municipio_id) if cliente.endereco.municipio_id else None)
            session.commit()
        return cliente

    def atualizar(self, cliente: Cliente) -> Cliente:
        with criar_session(self.engine) as session:
            session.merge(ClienteModel.from_domain(cliente))
            session.merge(CadastroModel(id=str(cliente.id), tipo="cliente"))
            if cliente.endereco:
                salvar_endereco(session, str(cliente.id), cliente.endereco, municipio_id=str(cliente.endereco.municipio_id) if cliente.endereco.municipio_id else None)
            session.commit()
        return cliente

    def anonimizar(self, id_: uuid.UUID) -> Cliente | None:
        cliente = self.buscar_por_id(id_)
        if cliente is None:
            return None
        anonimizado = Cliente(
            id=cliente.id,
            nome="Cliente anonimizado",
            usuario_id=cliente.usuario_id,
        )
        return self.atualizar(anonimizado)

    def buscar_por_id(self, id_: uuid.UUID) -> Cliente | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ClienteModel).where(ClienteModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return None
            endereco = obter_endereco(session, row.id)
            if endereco is not None:
                row.endereco_logradouro = endereco.logradouro
                row.endereco_numero = endereco.numero
                row.endereco_cidade = endereco.cidade
                row.endereco_estado = endereco.estado
                row.endereco_cep = endereco.cep
            return row.to_domain()

    def listar(self) -> list[Cliente]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(ClienteModel)).scalars().all()
            return [row.to_domain() for row in rows]