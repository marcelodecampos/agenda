from decimal import Decimal

import pytest

from agenda.domain.exceptions import ServicoInvalidoError
from agenda.domain.ids import novo_id
from agenda.domain.servico import ModalidadeAtendimento, Servico


def test_cria_servico_de_profissional_com_modalidade() -> None:
    modalidade = ModalidadeAtendimento(
        chave="domicilio",
        nome="Atendimento domiciliar",
        ajuste_preco_percentual=Decimal("15"),
        ajuste_duracao_minutos=30,
    )

    servico = Servico(
        id=novo_id(),
        nome="Manicure",
        categoria="unhas",
        duracao_base_minutos=60,
        preco_base=Decimal("80.00"),
        profissional_id=novo_id(),
        modalidades=(modalidade,),
    )

    assert servico.modalidades == (modalidade,)
    assert servico.organizacao_id is None


def test_servico_pode_pertencer_a_organizacao_e_profissional() -> None:
    servico = Servico(
        id=novo_id(),
        nome="Corte",
        categoria="cabelo",
        duracao_base_minutos=45,
        preco_base=Decimal("50"),
        profissional_id=novo_id(),
        organizacao_id=novo_id(),
    )

    assert servico.profissional_id is not None
    assert servico.organizacao_id is not None


@pytest.mark.parametrize(
    "alteracao",
    [
        {"duracao_base_minutos": 0},
        {"preco_base": Decimal("-1")},
        {"profissional_id": None, "organizacao_id": None},
    ],
)
def test_rejeita_servico_invalido(alteracao: dict[str, object]) -> None:
    dados: dict[str, object] = {
        "id": novo_id(),
        "nome": "Servico",
        "categoria": "categoria",
        "duracao_base_minutos": 30,
        "preco_base": Decimal("10"),
        "profissional_id": novo_id(),
    }
    dados.update(alteracao)

    with pytest.raises(ServicoInvalidoError):
        Servico(**dados)  # type: ignore[arg-type]


def test_rejeita_modalidade_com_dois_ajustes_de_preco() -> None:
    with pytest.raises(ServicoInvalidoError):
        ModalidadeAtendimento(
            chave="domicilio",
            nome="Domicilio",
            ajuste_preco_fixo=Decimal("10"),
            ajuste_preco_percentual=Decimal("5"),
        )


def test_rejeita_chaves_de_modalidade_duplicadas() -> None:
    modalidade = ModalidadeAtendimento(chave="salao", nome="No salao")

    with pytest.raises(ServicoInvalidoError):
        Servico(
            id=novo_id(),
            nome="Servico",
            categoria="categoria",
            duracao_base_minutos=30,
            preco_base=Decimal("10"),
            profissional_id=novo_id(),
            modalidades=(modalidade, modalidade),
        )