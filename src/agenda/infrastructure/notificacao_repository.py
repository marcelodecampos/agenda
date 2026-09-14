from __future__ import annotations

import json
import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.infrastructure.db import Base, criar_session
from agenda.ports import DestinatarioNotificacao, NotificacaoAgendamento


class DestinatarioNotificacaoModel(Base):
    __tablename__ = "destinatarios_notificacao"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    canal: Mapped[str] = mapped_column(String, nullable=False)
    destino: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, destinatario: DestinatarioNotificacao) -> "DestinatarioNotificacaoModel":
        return cls(
            id=destinatario.id,
            canal=destinatario.canal,
            destino=destinatario.destino,
        )

    def to_domain(self) -> DestinatarioNotificacao:
        return DestinatarioNotificacao(
            id=self.id,
            canal=self.canal,
            destino=self.destino,
        )


class NotificacaoAgendamentoModel(Base):
    __tablename__ = "notificacoes_agendamento"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid7()))
    agendamento_id: Mapped[str] = mapped_column(String, nullable=False)
    destinatario_id: Mapped[str] = mapped_column(String, nullable=False)
    mensagem: Mapped[str] = mapped_column(String, nullable=False)
    enviar_em: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, notificacao: NotificacaoAgendamento) -> "NotificacaoAgendamentoModel":
        return cls(
            id=str(uuid.uuid7()),
            agendamento_id=notificacao.agendamento_id,
            destinatario_id=notificacao.destinatario.id,
            mensagem=notificacao.mensagem,
            enviar_em=notificacao.enviar_em.isoformat(),
        )

    def to_domain(self, destinatario: DestinatarioNotificacao) -> NotificacaoAgendamento:
        from datetime import datetime

        return NotificacaoAgendamento(
            agendamento_id=self.agendamento_id,
            destinatario=destinatario,
            mensagem=self.mensagem,
            enviar_em=datetime.fromisoformat(self.enviar_em),
        )


class NotificacaoAgendamentoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, notificacao: NotificacaoAgendamento) -> NotificacaoAgendamento:
        with criar_session(self.engine) as session:
            session.merge(DestinatarioNotificacaoModel.from_domain(notificacao.destinatario))
            session.merge(
                NotificacaoAgendamentoModel.from_domain(notificacao)
            )
            session.commit()
        return notificacao

    def buscar_por_agendamento_id(self, agendamento_id: str) -> NotificacaoAgendamento | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(NotificacaoAgendamentoModel).where(
                    NotificacaoAgendamentoModel.agendamento_id == agendamento_id
                )
            ).scalar_one_or_none()
            if row is None:
                return None
            destinatario = session.execute(
                select(DestinatarioNotificacaoModel).where(
                    DestinatarioNotificacaoModel.id == row.destinatario_id
                )
            ).scalar_one()
            return row.to_domain(destinatario.to_domain())
