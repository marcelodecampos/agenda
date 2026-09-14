from decimal import Decimal

import pytest

from agenda.domain.exceptions import PacoteInvalidoError
from agenda.domain.ids import novo_id
from agenda.domain.pacote import Pacote


def test_cria_pacote_com_multiplos_servicos() -> None:
    servico_ids = (novo_id(), novo_id())

    pacote = Pacote(
        id=novo_id(),
        nome="Maos completas",
        servico_ids=servico_ids,
        duracao_total_minutos=90,
        preco=Decimal("120.00"),
        profissional_id=novo_id(),
    )

    assert pacote.servico_ids == servico_ids
    assert pacote.organizacao_id is None


def test_pacote_pode_pertencer_a_organizacao_e_profissional() -> None:
    pacote = Pacote(
        id=novo_id(),
        nome="Pacote do salao",
        servico_ids=(novo_id(),),
        duracao_total_minutos=60,
        preco=Decimal("80"),
        profissional_id=novo_id(),
        organizacao_id=novo_id(),
    )

    assert pacote.profissional_id is not None
    assert pacote.organizacao_id is not None


@pytest.mark.parametrize(
    "alteracao",
    [
        {"servico_ids": ()},
        {"duracao_total_minutos": 0},
        {"preco": Decimal("-1")},
        {"profissional_id": None, "organizacao_id": None},
    ],
)
def test_rejeita_pacote_invalido(alteracao: dict[str, object]) -> None:
    dados: dict[str, object] = {
        "id": novo_id(),
        "nome": "Pacote",
        "servico_ids": (novo_id(),),
        "duracao_total_minutos": 30,
        "preco": Decimal("10"),
        "profissional_id": novo_id(),
    }
    dados.update(alteracao)

    with pytest.raises(PacoteInvalidoError):
        Pacote(**dados)  # type: ignore[arg-type]


def test_rejeita_servico_repetido_no_pacote() -> None:
    servico_id = novo_id()

    with pytest.raises(PacoteInvalidoError):
        Pacote(
            id=novo_id(),
            nome="Pacote",
            servico_ids=(servico_id, servico_id),
            duracao_total_minutos=60,
            preco=Decimal("10"),
            profissional_id=novo_id(),
        )