from __future__ import annotations

from agenda.domain.agendamento import Agendamento
from agenda.domain.lembrete import ConfiguracaoLembrete, criar_lembrete
from agenda.ports import DestinatarioNotificacao


class CriarNotificacaoAgendamento:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(
        self,
        agendamento: Agendamento,
        configuracao: ConfiguracaoLembrete,
        destinatario: DestinatarioNotificacao,
        mensagem: str,
    ):
        notificacao = criar_lembrete(
            agendamento=agendamento,
            configuracao=configuracao,
            destinatario=destinatario,
            mensagem=mensagem,
        )
        return self.repositorio.salvar(notificacao)
