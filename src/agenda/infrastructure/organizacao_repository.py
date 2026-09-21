from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.endereco import Endereco
from agenda.domain.especialidade import Especialidade
from agenda.domain.organizacao import Organizacao
from agenda.infrastructure.db import Base, criar_session
from agenda.infrastructure.endereco_repository import CadastroModel, obter_endereco, salvar_endereco
from agenda.infrastructure.especialidade_repository import EspecialidadeModel


class OrganizacaoEspecialidadeModel(Base):
    __tablename__ = "organizacao_especialidades"
    __table_args__ = (
        UniqueConstraint("organizacao_id", "especialidade_id", name="uq_organizacao_especialidade"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organizacao_id: Mapped[str] = mapped_column(String, nullable=False)
    especialidade_id: Mapped[str] = mapped_column(String, nullable=False)


class OrganizacaoModel(Base):
    __tablename__ = "organizacoes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    nome_fantasia: Mapped[str | None] = mapped_column(String, nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True, unique=True)
    unipessoal: Mapped[bool] = mapped_column(default=False)
    endereco_logradouro: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_estado: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_cep: Mapped[str | None] = mapped_column(String, nullable=True)
    endereco_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, organizacao: Organizacao) -> "OrganizacaoModel":
        endereco = organizacao.endereco
        return cls(
            id=str(organizacao.id),
            nome=organizacao.nome,
            nome_fantasia=organizacao.nome_fantasia,
            cnpj=organizacao.cnpj,
            unipessoal=organizacao.unipessoal,
            endereco_logradouro=endereco.logradouro if endereco else None,
            endereco_numero=endereco.numero if endereco else None,
            endereco_cidade=endereco.cidade if endereco else None,
            endereco_estado=endereco.estado if endereco else None,
            endereco_cep=endereco.cep if endereco else None,
            endereco_id=str(organizacao.id) if endereco else None,
        )

    def to_domain(self, especialidades: list[Especialidade]) -> Organizacao:
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
            nome_fantasia=self.nome_fantasia,
            cnpj=self.cnpj,
            unipessoal=self.unipessoal,
            endereco=endereco,
            especialidades=tuple(especialidades),
        )


class OrganizacaoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def _substituir_especialidades(self, session, organizacao_id: str, especialidade_ids: list[uuid.UUID]) -> None:
        ids = [str(especialidade_id) for especialidade_id in dict.fromkeys(especialidade_ids)]
        especialidades = session.execute(
            select(EspecialidadeModel).where(EspecialidadeModel.id.in_(ids))
        ).scalars().all()
        if len(especialidades) != len(ids):
            raise ValueError("uma ou mais especialidades não foram encontradas")
        session.execute(
            OrganizacaoEspecialidadeModel.__table__.delete().where(
                OrganizacaoEspecialidadeModel.organizacao_id == organizacao_id
            )
        )
        for especialidade_id in ids:
            session.add(
                OrganizacaoEspecialidadeModel(
                    id=str(uuid.uuid7()),
                    organizacao_id=organizacao_id,
                    especialidade_id=especialidade_id,
                )
            )

    def _listar_especialidades(self, session, organizacao_id: str) -> list[Especialidade]:
        rows = session.execute(
            select(OrganizacaoEspecialidadeModel.especialidade_id).where(
                OrganizacaoEspecialidadeModel.organizacao_id == organizacao_id
            )
        ).scalars().all()
        if not rows:
            return []
        especialidades = session.execute(
            select(EspecialidadeModel).where(EspecialidadeModel.id.in_(rows)).order_by(EspecialidadeModel.nome)
        ).scalars().all()
        return [item.to_domain() for item in especialidades]

    def salvar(self, organizacao: Organizacao, especialidade_ids: list[uuid.UUID] | None = None) -> Organizacao:
        with criar_session(self.engine) as session:
            session.add(OrganizacaoModel.from_domain(organizacao))
            session.merge(CadastroModel(id=str(organizacao.id), tipo="organizacao"))
            if organizacao.endereco:
                salvar_endereco(session, str(organizacao.id), organizacao.endereco, municipio_id=str(organizacao.endereco.municipio_id) if organizacao.endereco.municipio_id else None)
            session.flush()
            if especialidade_ids is not None:
                self._substituir_especialidades(session, str(organizacao.id), especialidade_ids)
            session.commit()
        return self.buscar_por_id(organizacao.id) or organizacao

    def atualizar(self, organizacao: Organizacao, especialidade_ids: list[uuid.UUID] | None = None) -> Organizacao:
        with criar_session(self.engine) as session:
            session.merge(OrganizacaoModel.from_domain(organizacao))
            session.merge(CadastroModel(id=str(organizacao.id), tipo="organizacao"))
            if organizacao.endereco:
                salvar_endereco(session, str(organizacao.id), organizacao.endereco, municipio_id=str(organizacao.endereco.municipio_id) if organizacao.endereco.municipio_id else None)
            if especialidade_ids is not None:
                self._substituir_especialidades(session, str(organizacao.id), especialidade_ids)
            session.commit()
        return self.buscar_por_id(organizacao.id) or organizacao

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(OrganizacaoModel).where(OrganizacaoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.execute(
                    OrganizacaoEspecialidadeModel.__table__.delete().where(
                        OrganizacaoEspecialidadeModel.organizacao_id == str(id_)
                    )
                )
                session.delete(row)
                session.commit()

    def listar(self) -> list[Organizacao]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(OrganizacaoModel).order_by(OrganizacaoModel.nome)).scalars().all()
            resultado = []
            for row in rows:
                endereco = obter_endereco(session, row.id)
                if endereco is not None:
                    row.endereco_logradouro = endereco.logradouro
                    row.endereco_numero = endereco.numero
                    row.endereco_cidade = endereco.cidade
                    row.endereco_estado = endereco.estado
                    row.endereco_cep = endereco.cep
                resultado.append(row.to_domain(self._listar_especialidades(session, row.id)))
            return resultado

    def buscar_por_id(self, id_: uuid.UUID) -> Organizacao | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(OrganizacaoModel).where(OrganizacaoModel.id == str(id_))
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
            return row.to_domain(self._listar_especialidades(session, row.id))
