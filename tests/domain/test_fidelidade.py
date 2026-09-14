from decimal import Decimal

import pytest

from agenda.domain.exceptions import FidelidadeInvalidaError
from agenda.domain.fidelidade import (
    ProgramaFidelidade,
    ProgressoFidelidade,
    RecompensaFidelidade,
)
from agenda.domain.ids import novo_id


def _programa(**alteracoes: object) -> ProgramaFidelidade:
    dados: dict[str, object] = {
        "id": novo_id(),
        "nome": "Cartao manicure",
        "alvo_servico_id": novo_id(),
        "atendimentos_necessarios": 5,
        "recompensa": RecompensaFidelidade(
            tipo="desconto_percentual", valor=Decimal("50")
        ),
        "profissional_id": novo_id(),
    }
    dados.update(alteracoes)
    return ProgramaFidelidade(**dados)  # type: ignore[arg-type]


def test_programas_combinaveis_usam_alvos_configuraveis() -> None:
    programa = _programa()
    vip = _programa(segmento_cliente="vip")

    assert programa.alvo_servico_id is not None
    assert vip.segmento_cliente == "vip"


def test_progresso_acumula_atendimentos_e_libera_recompensa() -> None:
    programa = _programa()
    progresso = ProgressoFidelidade(programa.id, novo_id())

    for _ in range(5):
        progresso = progresso.registrar_atendimento()

    assert progresso.recompensa_disponivel(programa) is True


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"alvo_servico_id": None, "alvo_pacote_id": None},
        {"alvo_pacote_id": novo_id()},
        {"atendimentos_necessarios": 0},
        {"recompensa": None},
        {"profissional_id": None, "organizacao_id": None},
    ],
)
def test_rejeita_programa_invalido(alteracoes: dict[str, object]) -> None:
    with pytest.raises(FidelidadeInvalidaError):
        _programa(**alteracoes)


def test_recompensa_pode_ser_servico_gratis() -> None:
    recompensa = RecompensaFidelidade(tipo="servico_gratis", alvo_id=novo_id())

    assert recompensa.alvo_id is not None