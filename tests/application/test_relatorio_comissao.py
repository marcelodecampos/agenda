from datetime import datetime
from decimal import Decimal

from agenda.application.relatorio_comissao import gerar_relatorio_comissao
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.comissao import RegraComissao
from agenda.domain.ids import novo_id


def test_relatorio_comissao_soma_agendamentos_concluidos() -> None:
    membership_id = novo_id()
    agendamento = Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 10),
        itens=(ItemAgendamento(servico_id=novo_id(), duracao_minutos=60, preco=Decimal("200")),),
        status_atual="concluido",
    )
    regra = RegraComissao(
        id=novo_id(), tipo="percentual", valor=Decimal("10"), membership_id=membership_id
    )

    relatorio = gerar_relatorio_comissao(
        [agendamento], membership_id, (regra,), "concluido"
    )

    assert relatorio.total == Decimal("20")
    assert len(relatorio.linhas) == 1