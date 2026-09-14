from datetime import datetime
from decimal import Decimal

import pytest

from agenda.domain.agendamento import (
    Agendamento,
    CatalogoStatus,
    ItemAgendamento,
    StatusAgendamento,
    TransicaoStatus,
)
from agenda.domain.exceptions import (
    AgendamentoInvalidoError,
    TransicaoAgendamentoNaoPermitidaError,
)
from agenda.domain.ids import novo_id

SOLICITADO = StatusAgendamento("solicitado", "Solicitado")
CONFIRMADO = StatusAgendamento("confirmado", "Confirmado")
CONCLUIDO = StatusAgendamento("concluido", "Concluido")


def _catalogo() -> CatalogoStatus:
    return CatalogoStatus(
        status=(SOLICITADO, CONFIRMADO, CONCLUIDO),
        transicoes=(
            TransicaoStatus("solicitado", "confirmado", frozenset({"profissional"})),
            TransicaoStatus("confirmado", "concluido", frozenset({"profissional"})),
        ),
    )


def _agendamento() -> Agendamento:
    return Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9),
        itens=(
            ItemAgendamento(
                servico_id=novo_id(),
                duracao_minutos=60,
                preco=Decimal("80"),
            ),
            ItemAgendamento(
                pacote_id=novo_id(),
                duracao_minutos=30,
                preco=Decimal("40"),
            ),
        ),
        status_atual="solicitado",
    )


def test_agendamento_soma_duracao_e_preco_dos_itens() -> None:
    agendamento = _agendamento()

    assert agendamento.duracao_total_minutos == 90
    assert agendamento.preco_total == Decimal("120")
    assert len(agendamento.historico) == 1


def test_transicao_permitida_atualiza_status_e_historico() -> None:
    agendamento = _agendamento()
    ocorrido_em = datetime(2026, 9, 13, 10)

    agendamento.transicionar_para(
        "confirmado", "profissional", _catalogo(), ocorrido_em
    )

    assert agendamento.status_atual == "confirmado"
    assert agendamento.historico[-1].status == "confirmado"
    assert agendamento.historico[-1].ocorrido_em == ocorrido_em


def test_transicao_bloqueia_ator_nao_permitido() -> None:
    with pytest.raises(TransicaoAgendamentoNaoPermitidaError):
        _agendamento().transicionar_para(
            "confirmado", "cliente", _catalogo(), datetime.now()
        )


def test_item_deve_referenciar_um_unico_alvo() -> None:
    with pytest.raises(AgendamentoInvalidoError):
        ItemAgendamento(servico_id=novo_id(), pacote_id=novo_id(), duracao_minutos=30)


def test_catalogo_rejeita_transicao_com_status_inexistente() -> None:
    with pytest.raises(AgendamentoInvalidoError):
        CatalogoStatus(
            status=(SOLICITADO,),
            transicoes=(
                TransicaoStatus("solicitado", "confirmado", frozenset({"sistema"})),
            ),
        )