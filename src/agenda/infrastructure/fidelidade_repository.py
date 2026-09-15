from __future__ import annotations

import json
import uuid
from decimal import Decimal

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade, RecompensaFidelidade
from agenda.infrastructure.db import Base, criar_session


class RecompensaFidelidadeModel(Base):
    __tablename__ = "recompensas_fidelidade"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[str | None] = mapped_column(String, nullable=True)
    alvo_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, recompensa: RecompensaFidelidade) -> "RecompensaFidelidadeModel":
        return cls(
            id=str(uuid.uuid7()),
            tipo=recompensa.tipo,
            valor=str(recompensa.valor) if recompensa.valor is not None else None,
            alvo_id=str(recompensa.alvo_id) if recompensa.alvo_id is not None else None,
        )

    def to_domain(self) -> RecompensaFidelidade:
        return RecompensaFidelidade(
            tipo=self.tipo,
            valor=Decimal(self.valor) if self.valor is not None else None,
            alvo_id=uuid.UUID(self.alvo_id) if self.alvo_id is not None else None,
        )


class ProgramaFidelidadeModel(Base):
    __tablename__ = "programas_fidelidade"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    alvo_servico_id: Mapped[str | None] = mapped_column(String, nullable=True)
    alvo_pacote_id: Mapped[str | None] = mapped_column(String, nullable=True)
    atendimentos_necessarios: Mapped[int] = mapped_column(nullable=False)
    recompensa: Mapped[str] = mapped_column(String, nullable=False)
    segmento_cliente: Mapped[str | None] = mapped_column(String, nullable=True)
    profissional_id: Mapped[str | None] = mapped_column(String, nullable=True)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, programa: ProgramaFidelidade) -> "ProgramaFidelidadeModel":
        recompensa = programa.recompensa
        return cls(
            id=str(programa.id),
            nome=programa.nome,
            alvo_servico_id=str(programa.alvo_servico_id) if programa.alvo_servico_id else None,
            alvo_pacote_id=str(programa.alvo_pacote_id) if programa.alvo_pacote_id else None,
            atendimentos_necessarios=programa.atendimentos_necessarios,
            recompensa=json.dumps(
                {
                    "tipo": recompensa.tipo,
                    "valor": str(recompensa.valor) if recompensa.valor is not None else None,
                    "alvo_id": str(recompensa.alvo_id) if recompensa.alvo_id is not None else None,
                },
                ensure_ascii=False,
            ),
            segmento_cliente=programa.segmento_cliente,
            profissional_id=str(programa.profissional_id) if programa.profissional_id else None,
            organizacao_id=str(programa.organizacao_id) if programa.organizacao_id else None,
        )

    def to_domain(self) -> ProgramaFidelidade:
        dados = json.loads(self.recompensa or "{}")
        recompensa = RecompensaFidelidade(
            tipo=dados["tipo"],
            valor=Decimal(str(dados["valor"])) if dados.get("valor") is not None else None,
            alvo_id=uuid.UUID(str(dados["alvo_id"])) if dados.get("alvo_id") is not None else None,
        )
        return ProgramaFidelidade(
            id=uuid.UUID(self.id),
            nome=self.nome,
            alvo_servico_id=uuid.UUID(self.alvo_servico_id) if self.alvo_servico_id else None,
            alvo_pacote_id=uuid.UUID(self.alvo_pacote_id) if self.alvo_pacote_id else None,
            atendimentos_necessarios=self.atendimentos_necessarios,
            recompensa=recompensa,
            segmento_cliente=self.segmento_cliente,
            profissional_id=uuid.UUID(self.profissional_id) if self.profissional_id else None,
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
        )


class ProgressoFidelidadeModel(Base):
    __tablename__ = "progressos_fidelidade"

    programa_id: Mapped[str] = mapped_column(String, primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String, primary_key=True)
    atendimentos_concluidos: Mapped[int] = mapped_column(default=0, nullable=False)

    @classmethod
    def from_domain(cls, progresso: ProgressoFidelidade) -> "ProgressoFidelidadeModel":
        return cls(
            programa_id=str(progresso.programa_id),
            cliente_id=str(progresso.cliente_id),
            atendimentos_concluidos=progresso.atendimentos_concluidos,
        )

    def to_domain(self) -> ProgressoFidelidade:
        return ProgressoFidelidade(
            programa_id=uuid.UUID(self.programa_id),
            cliente_id=uuid.UUID(self.cliente_id),
            atendimentos_concluidos=self.atendimentos_concluidos,
        )


class ResgateFidelidadeModel(Base):
    __tablename__ = "resgates_fidelidade"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    programa_id: Mapped[str] = mapped_column(String, nullable=False)
    cliente_id: Mapped[str] = mapped_column(String, nullable=False)
    agendamento_id: Mapped[str | None] = mapped_column(String, nullable=True)
    preco_original: Mapped[str] = mapped_column(String, nullable=False)
    desconto: Mapped[str] = mapped_column(String, nullable=False)
    preco_final: Mapped[str] = mapped_column(String, nullable=False)
    gratuito: Mapped[bool] = mapped_column(default=False, nullable=False)


class ProgramaFidelidadeRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, programa: ProgramaFidelidade) -> ProgramaFidelidade:
        with criar_session(self.engine) as session:
            session.merge(ProgramaFidelidadeModel.from_domain(programa))
            session.commit()
        return programa

    def atualizar(self, programa: ProgramaFidelidade) -> ProgramaFidelidade:
        with criar_session(self.engine) as session:
            session.merge(ProgramaFidelidadeModel.from_domain(programa))
            session.commit()
        return programa

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ProgramaFidelidadeModel).where(ProgramaFidelidadeModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[ProgramaFidelidade]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(ProgramaFidelidadeModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> ProgramaFidelidade | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ProgramaFidelidadeModel).where(ProgramaFidelidadeModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None


class ProgressoFidelidadeRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, progresso: ProgressoFidelidade) -> ProgressoFidelidade:
        with criar_session(self.engine) as session:
            session.merge(ProgressoFidelidadeModel.from_domain(progresso))
            session.commit()
        return progresso

    def atualizar(self, progresso: ProgressoFidelidade) -> ProgressoFidelidade:
        with criar_session(self.engine) as session:
            session.merge(ProgressoFidelidadeModel.from_domain(progresso))
            session.commit()
        return progresso

    def remover(self, programa_id: uuid.UUID, cliente_id: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ProgressoFidelidadeModel).where(
                    ProgressoFidelidadeModel.programa_id == str(programa_id),
                    ProgressoFidelidadeModel.cliente_id == str(cliente_id),
                )
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[ProgressoFidelidade]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(ProgressoFidelidadeModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, programa_id: uuid.UUID, cliente_id: uuid.UUID) -> ProgressoFidelidade | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ProgressoFidelidadeModel).where(
                    ProgressoFidelidadeModel.programa_id == str(programa_id),
                    ProgressoFidelidadeModel.cliente_id == str(cliente_id),
                )
            ).scalar_one_or_none()
            return row.to_domain() if row else None


class ResgateFidelidadeRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, *, programa_id: uuid.UUID, cliente_id: uuid.UUID, aplicacao: object, agendamento_id: uuid.UUID | None = None) -> uuid.UUID:
        resgate_id = uuid.uuid7()
        with criar_session(self.engine) as session:
            session.add(ResgateFidelidadeModel(
                id=str(resgate_id),
                programa_id=str(programa_id),
                cliente_id=str(cliente_id),
                agendamento_id=str(agendamento_id) if agendamento_id else None,
                preco_original=str(aplicacao.preco_original),
                desconto=str(aplicacao.desconto),
                preco_final=str(aplicacao.preco_final),
                gratuito=aplicacao.gratuito,
            ))
            session.commit()
        return resgate_id
