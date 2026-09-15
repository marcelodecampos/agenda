from datetime import datetime
from decimal import Decimal

from agenda.application.consultar_operacao import construir_estatisticas, construir_ficha
from agenda.domain.agendamento import Agendamento, ItemAgendamento, RegistroStatus
from agenda.domain.ids import novo_id


def _agendamento(cliente_id, status, historico_status=None):
    inicio = datetime(2026, 9, 14, 10)
    historico = [
        RegistroStatus(item, "sistema", inicio) for item in (historico_status or [status])
    ]
    return Agendamento(
        id=novo_id(),
        cliente_id=cliente_id,
        profissional_id=novo_id(),
        inicio=inicio,
        itens=(
            ItemAgendamento(
                servico_id=novo_id(),
                duracao_minutos=60,
                preco=Decimal("80"),
            ),
        ),
        status_atual=status,
        historico=historico,
    )


def test_construi_ficha_de_confiabilidade() -> None:
    cliente_id = novo_id()
    agendamentos = [
        _agendamento(cliente_id, "concluido"),
        _agendamento(cliente_id, "nao_compareceu"),
        _agendamento(cliente_id, "cancelado"),
    ]

    ficha = construir_ficha(agendamentos, cliente_id)

    assert ficha.total_agendamentos == 3
    assert ficha.concluidos == 1
    assert ficha.nao_comparecimentos == 1
    assert ficha.cancelamentos == 1


def test_construi_estatisticas_basicas() -> None:
    agendamentos = [_agendamento(novo_id(), "concluido"), _agendamento(novo_id(), "cancelado")]

    estatisticas = construir_estatisticas(agendamentos)

    assert estatisticas.total_agendamentos == 2
    assert estatisticas.concluidos == 1
    assert estatisticas.cancelados == 1
    assert estatisticas.ocupacao_minutos == 120
    assert estatisticas.receita_registrada == Decimal("160")