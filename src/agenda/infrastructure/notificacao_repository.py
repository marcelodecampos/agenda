from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import String, UniqueConstraint, select
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
    __table_args__ = (UniqueConstraint("agendamento_id", name="uq_notificacao_agendamento"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid7()))
    agendamento_id: Mapped[str] = mapped_column(String, nullable=False)
    destinatario_id: Mapped[str] = mapped_column(String, nullable=False)
    mensagem: Mapped[str] = mapped_column(String, nullable=False)
    enviar_em: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pendente")
    tentativas: Mapped[int] = mapped_column(default=0, nullable=False)
    erro: Mapped[str | None] = mapped_column(String, nullable=True)
    enviado_em: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, notificacao: NotificacaoAgendamento) -> "NotificacaoAgendamentoModel":
        return cls(
            id=str(uuid.uuid7()),
            agendamento_id=notificacao.agendamento_id,
            destinatario_id=notificacao.destinatario.id,
            mensagem=notificacao.mensagem,
            enviar_em=notificacao.enviar_em.isoformat(),
            status="pendente",
            tentativas=0,
        )

    def to_domain(self, destinatario: DestinatarioNotificacao) -> NotificacaoAgendamento:
        from datetime import datetime

        return NotificacaoAgendamento(
            agendamento_id=self.agendamento_id,
            destinatario=destinatario,
            mensagem=self.mensagem,
            enviar_em=datetime.fromisoformat(self.enviar_em),
            status=self.status,
            tentativas=self.tentativas,
            erro=self.erro,
            enviado_em=datetime.fromisoformat(self.enviado_em)
            if self.enviado_em
            else None,
        )


class NotificacaoAgendamentoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, notificacao: NotificacaoAgendamento) -> NotificacaoAgendamento:
        with criar_session(self.engine) as session:
            session.merge(DestinatarioNotificacaoModel.from_domain(notificacao.destinatario))
            row = session.execute(
                select(NotificacaoAgendamentoModel).where(
                    NotificacaoAgendamentoModel.agendamento_id == notificacao.agendamento_id
                )
            ).scalar_one_or_none()
            if row is None:
                session.add(NotificacaoAgendamentoModel.from_domain(notificacao))
            else:
                row.destinatario_id = notificacao.destinatario.id
                row.mensagem = notificacao.mensagem
                row.enviar_em = notificacao.enviar_em.isoformat()
                row.status = "pendente"
                row.tentativas = 0
                row.erro = None
                row.enviado_em = None
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

    def listar(self) -> list[NotificacaoAgendamento]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(NotificacaoAgendamentoModel)).scalars().all()
            destinatarios = {
                item.id: item.to_domain()
                for item in session.execute(select(DestinatarioNotificacaoModel)).scalars().all()
            }
            return [row.to_domain(destinatarios[row.destinatario_id]) for row in rows]

    def listar_pendentes_vencidas(self, agora: datetime) -> list[NotificacaoAgendamento]:
        with criar_session(self.engine) as session:
            rows = session.execute(
                select(NotificacaoAgendamentoModel).where(
                    NotificacaoAgendamentoModel.status.in_(("pendente", "falhou")),
                )
            ).scalars().all()
            resultado = []
            for row in rows:
                if datetime.fromisoformat(row.enviar_em) <= agora:
                    destinatario = session.execute(
                        select(DestinatarioNotificacaoModel).where(
                            DestinatarioNotificacaoModel.id == row.destinatario_id
                        )
                    ).scalar_one()
                    resultado.append(row.to_domain(destinatario.to_domain()))
            return resultado

    def marcar_enviando(self, agendamento_id: str) -> bool:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(NotificacaoAgendamentoModel).where(
                    NotificacaoAgendamentoModel.agendamento_id == agendamento_id,
                    NotificacaoAgendamentoModel.status == "pendente",
                )
            ).scalar_one_or_none()
            if row is None:
                return False
            row.status = "enviando"
            row.tentativas += 1
            session.commit()
            return True

    def marcar_enviada(self, agendamento_id: str, enviado_em: datetime) -> None:
        self._atualizar_status(agendamento_id, "enviada", enviado_em=enviado_em)

    def marcar_falha(self, agendamento_id: str, erro: str) -> None:
        self._atualizar_status(agendamento_id, "falhou", erro=erro)

    def _atualizar_status(
        self,
        agendamento_id: str,
        status: str,
        *,
        enviado_em: datetime | None = None,
        erro: str | None = None,
    ) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(NotificacaoAgendamentoModel).where(
                    NotificacaoAgendamentoModel.agendamento_id == agendamento_id
                )
            ).scalar_one_or_none()
            if row is None:
                return
            row.status = status
            row.enviado_em = enviado_em.isoformat() if enviado_em else None
            row.erro = erro
            session.commit()
