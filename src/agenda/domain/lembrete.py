from dataclasses import dataclass
from datetime import timedelta

from agenda.domain.agendamento import Agendamento
from agenda.domain.exceptions import ErroDominio
from agenda.ports import DestinatarioNotificacao, NotificacaoAgendamento


class LembreteInvalidoError(ErroDominio):
    pass


@dataclass(frozen=True)
class ConfiguracaoLembrete:
    antecedencia: timedelta
    canal: str

    def __post_init__(self) -> None:
        if self.antecedencia <= timedelta(0):
            raise LembreteInvalidoError("antecedencia deve ser positiva")
        if not self.canal.strip():
            raise LembreteInvalidoError("canal e obrigatorio")


def criar_lembrete(
    agendamento: Agendamento,
    configuracao: ConfiguracaoLembrete,
    destinatario: DestinatarioNotificacao,
    mensagem: str,
) -> NotificacaoAgendamento:
    if not mensagem.strip():
        raise LembreteInvalidoError("mensagem e obrigatoria")
    if destinatario.canal != configuracao.canal:
        raise LembreteInvalidoError("canal do destinatario difere da configuracao")
    return NotificacaoAgendamento(
        agendamento_id=str(agendamento.id),
        destinatario=destinatario,
        mensagem=mensagem,
        enviar_em=agendamento.inicio - configuracao.antecedencia,
    )