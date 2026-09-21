from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Numeric, String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.endereco import Endereco
from agenda.infrastructure.db import Base


class CadastroModel(Base):
    __tablename__ = "cadastros"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)


class EnderecoModel(Base):
    __tablename__ = "enderecos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cadastro_id: Mapped[str] = mapped_column(String, nullable=False)
    logradouro: Mapped[str] = mapped_column(String, nullable=False)
    numero: Mapped[str] = mapped_column(String, nullable=False)
    complemento: Mapped[str | None] = mapped_column(String, nullable=True)
    bairro: Mapped[str | None] = mapped_column(String, nullable=True)
    cep: Mapped[str] = mapped_column(String, nullable=False)
    cidade: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String(2), nullable=False)
    municipio_id: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    def to_domain(self) -> Endereco:
        return Endereco(
            logradouro=self.logradouro,
            numero=self.numero,
            cidade=self.cidade,
            estado=self.estado,
            cep=self.cep,
            bairro=self.bairro,
            latitude=self.latitude,
            longitude=self.longitude,
        )


class CadastroEnderecoModel(Base):
    __tablename__ = "cadastro_enderecos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cadastro_id: Mapped[str] = mapped_column(String, nullable=False)
    endereco_id: Mapped[str] = mapped_column(String, nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False, default="principal")
    descricao: Mapped[str] = mapped_column(String(40), nullable=False, default="Matriz")
    principal: Mapped[bool] = mapped_column(default=True)
    ativo: Mapped[bool] = mapped_column(default=True)


def _id(endereco: EnderecoModel) -> str:
    return endereco.id


def obter_endereco(session, cadastro_id: str) -> EnderecoModel | None:
    return session.scalar(
        select(EnderecoModel)
        .join(CadastroEnderecoModel, CadastroEnderecoModel.endereco_id == EnderecoModel.id)
        .where(CadastroEnderecoModel.cadastro_id == cadastro_id, CadastroEnderecoModel.ativo.is_(True))
        .order_by(CadastroEnderecoModel.principal.desc(), EnderecoModel.id)
    )


def listar_enderecos(session, cadastro_id: str) -> list[EnderecoModel]:
    return list(session.scalars(
        select(EnderecoModel)
        .join(CadastroEnderecoModel, CadastroEnderecoModel.endereco_id == EnderecoModel.id)
        .where(CadastroEnderecoModel.cadastro_id == cadastro_id, CadastroEnderecoModel.ativo.is_(True))
        .order_by(CadastroEnderecoModel.principal.desc(), EnderecoModel.id)
    ).all())


def criar_endereco(session, cadastro_id: str, endereco: Endereco, *, tipo: str = "principal", descricao: str = "Matriz", principal: bool = False, municipio_id: str | None = None) -> EnderecoModel:
    if principal:
        session.query(CadastroEnderecoModel).filter(CadastroEnderecoModel.cadastro_id == cadastro_id).update({"principal": False})
    modelo = EnderecoModel(
        id=str(uuid.uuid7()),
        cadastro_id=cadastro_id,
        logradouro=endereco.logradouro,
        numero=endereco.numero,
        cep=endereco.cep,
        bairro=endereco.bairro,
        cidade=endereco.cidade,
        estado=endereco.estado,
    )
    session.add(modelo)
    session.flush()
    session.add(CadastroEnderecoModel(id=str(uuid.uuid7()), cadastro_id=cadastro_id, endereco_id=modelo.id, tipo=tipo, descricao=descricao, principal=principal))
    modelo.municipio_id = municipio_id
    modelo.latitude = endereco.latitude
    modelo.longitude = endereco.longitude
    return modelo


def salvar_endereco(session, cadastro_id: str, endereco: Endereco, *, municipio_id: str | None = None) -> EnderecoModel:
    modelo = obter_endereco(session, cadastro_id)
    if modelo is None:
        modelo = EnderecoModel(
            id=str(uuid.uuid7()),
            cadastro_id=cadastro_id,
            logradouro=endereco.logradouro,
            numero=endereco.numero,
            cep=endereco.cep,
            bairro=endereco.bairro,
            cidade=endereco.cidade,
            estado=endereco.estado,
        )
        session.add(modelo)
        session.flush()
        session.add(CadastroEnderecoModel(id=str(uuid.uuid7()), cadastro_id=cadastro_id, endereco_id=modelo.id, tipo="principal", principal=True, ativo=True))
    modelo.logradouro = endereco.logradouro
    modelo.numero = endereco.numero
    modelo.cep = endereco.cep
    modelo.bairro = endereco.bairro
    modelo.cidade = endereco.cidade
    modelo.estado = endereco.estado
    modelo.municipio_id = municipio_id
    modelo.latitude = endereco.latitude
    modelo.longitude = endereco.longitude
    return modelo
