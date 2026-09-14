from __future__ import annotations

import httpx

from agenda.ports import NotificacaoAgendamento, NotificacaoPort


class WebhookNotificacaoAdapter(NotificacaoPort):
    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client()

    @property
    def notifications_url(self) -> str:
        return f"{self.base_url}/notifications"

    def enviar(self, notificacao: NotificacaoAgendamento) -> None:
        payload = {
            "agendamento_id": notificacao.agendamento_id,
            "destinatario": {
                "id": notificacao.destinatario.id,
                "canal": notificacao.destinatario.canal,
                "destino": notificacao.destinatario.destino,
            },
            "mensagem": notificacao.mensagem,
            "enviar_em": notificacao.enviar_em.isoformat(timespec="seconds"),
        }

        response = self.client.post(
            self.notifications_url,
            content=('{\n  "agendamento_id": "' + notificacao.agendamento_id + '",\n  "destinatario": {\n    "id": "' + notificacao.destinatario.id + '",\n    "canal": "' + notificacao.destinatario.canal + '",\n    "destino": "' + notificacao.destinatario.destino + '"\n  },\n  "mensagem": "' + notificacao.mensagem + '",\n  "enviar_em": "' + notificacao.enviar_em.isoformat(timespec="seconds") + '"\n}').encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=10.0,
        )
        response.raise_for_status()
