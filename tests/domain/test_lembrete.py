from datetime import datetime, timedelta

import pytest

from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.ids import novo_id
from agenda.domain.lembrete import (
    ConfiguracaoLembrete,
    LembreteInvalidoError,
    criar_lembrete,
)
from agenda.ports import DestinatarioNotificacao


def _agendamento() -> Agendamento:
    return Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9),
        itens=(ItemAgendamento(servico_id=novo_id(), duracao_minutos=30),),
        status_atual="solicitado",
    )


def test_cria_lembrete_antes_do_horario_do_agendamento() -> None:
    agendamento = _agendamento()
    configuracao = ConfiguracaoLembrete(timedelta(hours=2), "email")
    destinatario = DestinatarioNotificacao(novo_id().__str__(), "email", "a@b.com")

    lembrete = criar_lembrete(
        agendamento, configuracao, destinatario, "Seu horario esta proximo"
    )

    assert lembrete.enviar_em == datetime(2026, 9, 14, 7)


def test_rejeita_canal_diferente_do_destinatario() -> None:
    with pytest.raises(LembreteInvalidoError):
        criar_lembrete(
            _agendamento(),
            ConfiguracaoLembrete(timedelta(hours=2), "sms"),
            DestinatarioNotificacao("1", "email", "a@b.com"),
            "Mensagem",
        )