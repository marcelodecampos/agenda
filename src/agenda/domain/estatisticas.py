from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.agendamento import Agendamento


@dataclass(frozen=True)
class EstatisticasAgenda:
    total_agendamentos: int
    total_concluidos: int
    total_no_show: int
    minutos_agendados: int
    taxa_no_show: Decimal
    ocupacao: Decimal


def calcular_estatisticas(
    agendamentos: tuple[Agendamento, ...],
    status_concluido: str,
    status_no_show: str,
    minutos_disponiveis: int,
) -> EstatisticasAgenda:
    concluidos = sum(
        agendamento.status_atual == status_concluido for agendamento in agendamentos
    )
    no_show = sum(
        agendamento.status_atual == status_no_show for agendamento in agendamentos
    )
    minutos_agendados = sum(
        agendamento.duracao_total_minutos for agendamento in agendamentos
    )
    total = len(agendamentos)
    return EstatisticasAgenda(
        total_agendamentos=total,
        total_concluidos=concluidos,
        total_no_show=no_show,
        minutos_agendados=minutos_agendados,
        taxa_no_show=(Decimal(no_show) / Decimal(total) if total else Decimal("0")),
        ocupacao=(
            Decimal(minutos_agendados) / Decimal(minutos_disponiveis)
            if minutos_disponiveis > 0
            else Decimal("0")
        ),
    )