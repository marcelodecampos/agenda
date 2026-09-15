from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.agendamento import Agendamento


@dataclass(frozen=True)
class FichaConfiabilidade:
    cliente_id: uuid.UUID
    total_agendamentos: int
    cancelamentos: int
    nao_comparecimentos: int
    concluidos: int


@dataclass(frozen=True)
class EstatisticasOperacao:
    total_agendamentos: int
    concluidos: int
    cancelados: int
    nao_comparecimentos: int
    ocupacao_minutos: int
    receita_registrada: Decimal


def _filtrar(
    agendamentos: list[Agendamento],
    *,
    organizacao_id: uuid.UUID | None = None,
    profissional_id: uuid.UUID | None = None,
) -> list[Agendamento]:
    return [
        agendamento
        for agendamento in agendamentos
        if (organizacao_id is None or agendamento.organizacao_id == organizacao_id)
        and (
            profissional_id is None
            or agendamento.profissional_id == profissional_id
        )
    ]


def construir_ficha(
    agendamentos: list[Agendamento], cliente_id: uuid.UUID
) -> FichaConfiabilidade:
    itens = [item for item in agendamentos if item.cliente_id == cliente_id]
    return FichaConfiabilidade(
        cliente_id=cliente_id,
        total_agendamentos=len(itens),
        cancelamentos=sum(
            any(registro.status == "cancelado" for registro in item.historico)
            for item in itens
        ),
        nao_comparecimentos=sum(
            any(registro.status == "nao_compareceu" for registro in item.historico)
            for item in itens
        ),
        concluidos=sum(item.status_atual == "concluido" for item in itens),
    )


def construir_estatisticas(
    agendamentos: list[Agendamento],
    *,
    organizacao_id: uuid.UUID | None = None,
    profissional_id: uuid.UUID | None = None,
) -> EstatisticasOperacao:
    itens = _filtrar(
        agendamentos,
        organizacao_id=organizacao_id,
        profissional_id=profissional_id,
    )
    return EstatisticasOperacao(
        total_agendamentos=len(itens),
        concluidos=sum(item.status_atual == "concluido" for item in itens),
        cancelados=sum(item.status_atual == "cancelado" for item in itens),
        nao_comparecimentos=sum(
            item.status_atual == "nao_compareceu" for item in itens
        ),
        ocupacao_minutos=sum(item.duracao_total_minutos for item in itens),
        receita_registrada=sum(
            (item.preco_total for item in itens), Decimal("0")
        ),
    )