from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.application.calcular_comissao_agendamento import CalcularComissaoAgendamento
from agenda.domain.agendamento import Agendamento
from agenda.domain.comissao import RegraComissao


@dataclass(frozen=True)
class LinhaComissao:
    agendamento_id: uuid.UUID
    profissional_id: uuid.UUID
    valor: Decimal


@dataclass(frozen=True)
class RelatorioComissao:
    membership_id: uuid.UUID
    linhas: tuple[LinhaComissao, ...]
    total: Decimal


def gerar_relatorio_comissao(
    agendamentos: list[Agendamento],
    membership_id: uuid.UUID,
    regras: tuple[RegraComissao, ...],
    status_concluido: str,
) -> RelatorioComissao:
    calculadora = CalcularComissaoAgendamento()
    linhas = tuple(
        LinhaComissao(
            agendamento_id=agendamento.id,
            profissional_id=agendamento.profissional_id,
            valor=calculadora.executar(
                agendamento, membership_id, regras, status_concluido
            ),
        )
        for agendamento in agendamentos
        if agendamento.status_atual == status_concluido
    )
    return RelatorioComissao(
        membership_id=membership_id,
        linhas=linhas,
        total=sum((linha.valor for linha in linhas), Decimal("0")),
    )
