from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.servico import ModalidadeAtendimento, Servico
from agenda.infrastructure.db import Base, criar_session


class ModalidadeAtendimentoModel(Base):
    __tablename__ = "modalidades_atendimento"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chave: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    ajuste_preco_fixo: Mapped[str | None] = mapped_column(String, nullable=True)
    ajuste_preco_percentual: Mapped[str | None] = mapped_column(String, nullable=True)
    ajuste_duracao_minutos: Mapped[int] = mapped_column(default=0)

    @classmethod
    def from_domain(cls, modalidade: ModalidadeAtendimento) -> "ModalidadeAtendimentoModel":
        return cls(
            id=f"{modalidade.chave}-{uuid.uuid4()}",
            chave=modalidade.chave,
            nome=modalidade.nome,
            ajuste_preco_fixo=str(modalidade.ajuste_preco_fixo) if modalidade.ajuste_preco_fixo is not None else None,
            ajuste_preco_percentual=str(modalidade.ajuste_preco_percentual) if modalidade.ajuste_preco_percentual is not None else None,
            ajuste_duracao_minutos=modalidade.ajuste_duracao_minutos,
        )

    def to_domain(self) -> ModalidadeAtendimento:
        return ModalidadeAtendimento(
            chave=self.chave,
            nome=self.nome,
            ajuste_preco_fixo=Decimal(self.ajuste_preco_fixo) if self.ajuste_preco_fixo is not None else None,
            ajuste_preco_percentual=Decimal(self.ajuste_preco_percentual) if self.ajuste_preco_percentual is not None else None,
            ajuste_duracao_minutos=self.ajuste_duracao_minutos,
        )


class ServicoModel(Base):
    __tablename__ = "servicos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    categoria: Mapped[str] = mapped_column(String, nullable=False)
    duracao_base_minutos: Mapped[int] = mapped_column(nullable=False)
    preco_base: Mapped[str] = mapped_column(String, nullable=False)
    profissional_id: Mapped[str | None] = mapped_column(String, nullable=True)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo_procedimento_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, servico: Servico) -> "ServicoModel":
        return cls(
            id=str(servico.id),
            nome=servico.nome,
            categoria=servico.categoria,
            duracao_base_minutos=servico.duracao_base_minutos,
            preco_base=str(servico.preco_base),
            profissional_id=str(servico.profissional_id) if servico.profissional_id else None,
            organizacao_id=str(servico.organizacao_id) if servico.organizacao_id else None,
            tipo_procedimento_id=(
                str(servico.tipo_procedimento_id) if servico.tipo_procedimento_id else None
            ),
        )

    def to_domain(self, modalidades: tuple[ModalidadeAtendimento, ...]) -> Servico:
        return Servico(
            id=uuid.UUID(self.id),
            nome=self.nome,
            categoria=self.categoria,
            duracao_base_minutos=self.duracao_base_minutos,
            preco_base=Decimal(self.preco_base),
            profissional_id=uuid.UUID(self.profissional_id) if self.profissional_id else None,
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
            tipo_procedimento_id=(
                uuid.UUID(self.tipo_procedimento_id) if self.tipo_procedimento_id else None
            ),
            modalidades=modalidades,
        )



class ServicoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, servico: Servico) -> Servico:
        with criar_session(self.engine) as session:
            for modalidade in servico.modalidades:
                session.merge(ModalidadeAtendimentoModel.from_domain(modalidade))

            session.add(ServicoModel.from_domain(servico))
            session.commit()
        return servico

    def atualizar(self, servico: Servico) -> Servico:
        with criar_session(self.engine) as session:
            for modalidade in servico.modalidades:
                session.merge(ModalidadeAtendimentoModel.from_domain(modalidade))
            session.merge(ServicoModel.from_domain(servico))
            session.commit()
        return servico

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ServicoModel).where(ServicoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Servico]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(ServicoModel)).scalars().all()
            modalidades = tuple(
                m.to_domain()
                for m in session.execute(select(ModalidadeAtendimentoModel)).scalars().all()
            )
            return [row.to_domain(modalidades) for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Servico | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ServicoModel).where(ServicoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return None
            modalidades = tuple(
                m.to_domain()
                for m in session.execute(select(ModalidadeAtendimentoModel)).scalars().all()
            )
            return row.to_domain(modalidades)
