from decimal import Decimal

import pytest

from agenda.domain.fidelidade import (
    ProgramaFidelidade,
    ProgressoFidelidade,
    RecompensaFidelidade,
    aplicar_recompensa,
)
from agenda.domain.ids import novo_id
from agenda.domain.exceptions import FidelidadeInvalidaError


def _programa(tipo: str, valor: Decimal | None = None) -> ProgramaFidelidade:
    return ProgramaFidelidade(
        id=novo_id(),
        nome="Programa",
        alvo_servico_id=novo_id(),
        atendimentos_necessarios=3,
        recompensa=RecompensaFidelidade(tipo, valor=valor),
        organizacao_id=novo_id(),
    )


def test_aplica_desconto_percentual() -> None:
    programa = _programa("desconto_percentual", Decimal("20"))
    progresso = ProgressoFidelidade(programa.id, novo_id(), 3)

    aplicacao = aplicar_recompensa(programa, progresso, Decimal("100"))

    assert aplicacao.desconto == Decimal("20.00")
    assert aplicacao.preco_final == Decimal("80.00")
    assert aplicacao.gratuito is False


def test_aplica_servico_gratis_e_consumo_bloqueia_reuso() -> None:
    programa = _programa("servico_gratis")
    cliente_id = novo_id()
    progresso = ProgressoFidelidade(programa.id, cliente_id, 3)

    aplicacao = aplicar_recompensa(programa, progresso, Decimal("100"))
    restante = progresso.consumir_recompensa(programa)

    assert aplicacao.preco_final == Decimal("0")
    assert restante.atendimentos_concluidos == 0
    with pytest.raises(FidelidadeInvalidaError):
        aplicar_recompensa(programa, restante, Decimal("100"))