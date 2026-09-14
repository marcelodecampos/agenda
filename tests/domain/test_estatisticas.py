from datetime import datetime
from decimal import Decimal

from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.estatisticas import calcular_estatisticas
from agenda.domain.ids import novo_id


def _agendamento(status: str, minutos: int) -> Agendamento:
    return Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9),
        itens=(ItemAgendamento(servico_id=novo_id(), duracao_minutos=minutos),),
        status_atual=status,
    )


def test_calcula_volume_no_show_e_ocupacao() -> None:
    estatisticas = calcular_estatisticas(
        (_agendamento("concluido", 60), _agendamento("nao_compareceu", 30)),
        status_concluido="concluido",
        status_no_show="nao_compareceu",
        minutos_disponiveis=180,
    )

    assert estatisticas.total_agendamentos == 2
    assert estatisticas.total_concluidos == 1
    assert estatisticas.total_no_show == 1
    assert estatisticas.taxa_no_show == Decimal("0.5")
    assert estatisticas.ocupacao == Decimal("0.5")


def test_estatisticas_vazias_nao_dividem_por_zero() -> None:
    estatisticas = calcular_estatisticas((), "concluido", "nao_compareceu", 0)

    assert estatisticas.taxa_no_show == Decimal("0")
    assert estatisticas.ocupacao == Decimal("0")