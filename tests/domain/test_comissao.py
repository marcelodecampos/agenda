from datetime import datetime
from decimal import Decimal

from agenda.domain.agendamento import (
    Agendamento,
    CatalogoStatus,
    ItemAgendamento,
    StatusAgendamento,
    TransicaoStatus,
)
from agenda.domain.comissao import RegraComissao, calcular_comissao
from agenda.domain.ids import novo_id


def _agendamento() -> tuple[Agendamento, CatalogoStatus, object]:
    solicitado = StatusAgendamento("solicitado", "Solicitado")
    concluido = StatusAgendamento("concluido", "Concluido")
    catalogo = CatalogoStatus(
        status=(solicitado, concluido),
        transicoes=(
            TransicaoStatus("solicitado", "concluido", frozenset({"profissional"})),
        ),
    )
    agendamento = Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9),
        itens=(
            ItemAgendamento(servico_id=novo_id(), duracao_minutos=60, preco=Decimal("100")),
        ),
        status_atual="solicitado",
    )
    return agendamento, catalogo, concluido


def test_calcula_comissao_percentual_apos_conclusao() -> None:
    agendamento, catalogo, concluido = _agendamento()
    agendamento.transicionar_para("concluido", "profissional", catalogo, datetime.now())
    regra = RegraComissao(novo_id(), "percentual", Decimal("10"), membership_id=novo_id())

    assert calcular_comissao(agendamento, regra.membership_id, (regra,), concluido.chave) == Decimal("10")


def test_comissao_fixa_nao_e_calculada_antes_do_status_concluido() -> None:
    agendamento, _, concluido = _agendamento()
    membership_id = novo_id()
    regra = RegraComissao(novo_id(), "fixa", Decimal("25"), membership_id=membership_id)

    assert calcular_comissao(agendamento, membership_id, (regra,), concluido.chave) == Decimal("0")