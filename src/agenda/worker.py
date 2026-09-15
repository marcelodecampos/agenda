from __future__ import annotations

from datetime import datetime

from agenda.adapters.smtp_notificacao_adapter import SMTPNotificacaoAdapter
from agenda.adapters.webhook_notificacao_adapter import WebhookNotificacaoAdapter
from agenda.application.processar_notificacoes import ProcessarNotificacoesVencidas
from agenda.config import settings
from agenda.infrastructure.db import criar_engine
from agenda.infrastructure.notificacao_repository import NotificacaoAgendamentoRepository


def processar_notificacoes() -> dict[str, int]:
    if settings.notificacao_webhook_url:
        entregador = WebhookNotificacaoAdapter(
            base_url=settings.notificacao_webhook_url
        )
    else:
        entregador = SMTPNotificacaoAdapter(
            host=settings.smtp_host,
            port=settings.smtp_port,
            remetente=settings.smtp_from,
            username=settings.smtp_username,
            password=settings.smtp_password,
            starttls=settings.smtp_starttls,
        )
    return ProcessarNotificacoesVencidas(
        NotificacaoAgendamentoRepository(criar_engine(settings.database_url)),
        entregador,
        max_tentativas=settings.notificacao_max_tentativas,
    ).executar(datetime.now())


if __name__ == "__main__":
    print(processar_notificacoes())