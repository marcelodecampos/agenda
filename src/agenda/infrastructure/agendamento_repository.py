from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.agendamento import Agendamento, ItemAgendamento, RegistroStatus
from agenda.infrastructure.db import Base, criar_session


def _item_para_dict(item: ItemAgendamento) -> dict[str, object]:
    return {
        "servico_id": str(item.servico_id) if item.servico_id else None,
        "pacote_id": str(item.pacote_id) if item.pacote_id else None,
        "duracao_minutos": item.duracao_minutos,
        "preco": str(item.preco),
    }


def _item_de_dict(dados: dict[str, object]) -> ItemAgendamento:
    return ItemAgendamento(
        servico_id=uuid.UUID(str(dados["servico_id"])) if dados.get("servico_id") else None,
        pacote_id=uuid.UUID(str(dados["pacote_id"])) if dados.get("pacote_id") else None,
        duracao_minutos=int(dados["duracao_minutos"]),
        preco=__import__("decimal").Decimal(str(dados["preco"])),
    )


def _historico_para_dict(registro: RegistroStatus) -> dict[str, str]:
    return {
        "status": registro.status,
        "ator": registro.ator,
        "ocorrido_em": registro.ocorrido_em.isoformat(),
    }


def _historico_de_dict(dados: dict[str, str]) -> RegistroStatus:
    return RegistroStatus(
        status=dados["status"],
        ator=dados["ator"],
        ocorrido_em=datetime.fromisoformat(dados["ocorrido_em"]),
    )


class AgendamentoModel(Base):
    __tablename__ = "agendamentos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    cliente_id: Mapped[str] = mapped_column(String, nullable=False)
    profissional_id: Mapped[str] = mapped_column(String, nullable=False)
    inicio: Mapped[str] = mapped_column(String, nullable=False)
    itens: Mapped[str] = mapped_column(String, nullable=False)
    status_atual: Mapped[str] = mapped_column(String, nullable=False)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)
    historico: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, agendamento: Agendamento) -> "AgendamentoModel":
        return cls(
            id=str(agendamento.id),
            cliente_id=str(agendamento.cliente_id),
            profissional_id=str(agendamento.profissional_id),
            inicio=agendamento.inicio.isoformat(),
            itens=json.dumps(
                [_item_para_dict(item) for item in agendamento.itens],
                ensure_ascii=False,
            ),
            status_atual=agendamento.status_atual,
            organizacao_id=str(agendamento.organizacao_id) if agendamento.organizacao_id else None,
            historico=json.dumps(
                [_historico_para_dict(registro) for registro in agendamento.historico],
                ensure_ascii=False,
            ),
        )

    def to_domain(self) -> Agendamento:
        itens = tuple(
            _item_de_dict(item) for item in json.loads(self.itens or "[]")
        )
        historico = [
            _historico_de_dict(registro)
            for registro in json.loads(self.historico or "[]")
        ]
        return Agendamento(
            id=uuid.UUID(self.id),
            cliente_id=uuid.UUID(self.cliente_id),
            profissional_id=uuid.UUID(self.profissional_id),
            inicio=datetime.fromisoformat(self.inicio),
            itens=itens,
            status_atual=self.status_atual,
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
            historico=historico,
        )


class AgendamentoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, agendamento: Agendamento) -> Agendamento:
        with criar_session(self.engine) as session:
            session.merge(AgendamentoModel.from_domain(agendamento))
            session.commit()
        return agendamento

    def atualizar(self, agendamento: Agendamento) -> Agendamento:
        with criar_session(self.engine) as session:
            session.merge(AgendamentoModel.from_domain(agendamento))
            session.commit()
        return agendamento

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(AgendamentoModel).where(AgendamentoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Agendamento]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(AgendamentoModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Agendamento | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(AgendamentoModel).where(AgendamentoModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None
