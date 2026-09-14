from datetime import datetime

import httpx

from agenda.adapters.webhook_notificacao_adapter import WebhookNotificacaoAdapter
from agenda.ports import DestinatarioNotificacao, NotificacaoAgendamento


def test_envia_notificacao_para_provedor_http() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == "https://notify.example.com/notifications"
        assert request.headers["Content-Type"] == "application/json"

        payload = request.read()
        assert b'"agendamento_id": "ag-123"' in payload
        assert b'"destino": "maria@example.com"' in payload
        assert b'"mensagem": "Lembrete"' in payload
        assert b'"enviar_em": "2026-09-14T09:00:00"' in payload

        return httpx.Response(202)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = WebhookNotificacaoAdapter(
        base_url="https://notify.example.com",
        client=client,
    )

    notificacao = NotificacaoAgendamento(
        agendamento_id="ag-123",
        destinatario=DestinatarioNotificacao(
            id="user-1",
            canal="email",
            destino="maria@example.com",
        ),
        mensagem="Lembrete",
        enviar_em=datetime(2026, 9, 14, 9, 0, 0),
    )

    adapter.enviar(notificacao)
