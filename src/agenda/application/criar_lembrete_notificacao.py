from __future__ import annotations

from datetime import datetime

from agenda.domain.agendamento import Agendamento
from agenda.domain.lembrete import ConfiguracaoLembrete, criar_lembrete
from agenda.ports import DestinatarioNotificacao


class CriarLembreteNotificacao:
    def executar(
        self,
        agendamento: Agendamento,
        configuracao: ConfiguracaoLembrete,
        destinatario: DestinatarioNotificacao,
        mensagem: str,
    ):
        return criar_lembrete(
            agendamento=agendamento,
            configuracao=configuracao,
            destinatario=destinatario,
            mensagem=mensagem,
        )
