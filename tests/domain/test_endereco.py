from decimal import Decimal

import pytest

from agenda.domain.endereco import Cliente, Endereco, EnderecoInvalidoError
from agenda.domain.exceptions import ClienteInvalidoError
from agenda.domain.ids import novo_id


def test_cliente_pode_ser_criado_com_cpf_opcional() -> None:
    cliente = Cliente(id=novo_id(), nome="Maria")

    assert cliente.cpf is None


def test_endereco_pode_conter_coordenadas() -> None:
    endereco = Endereco(
        logradouro="Rua A",
        numero="10",
        cidade="Sao Paulo",
        estado="SP",
        cep="01000-000",
        latitude=Decimal("-23.55"),
        longitude=Decimal("-46.63"),
    )

    assert endereco.latitude == Decimal("-23.55")


def test_rejeita_endereco_sem_coordenada_par() -> None:
    with pytest.raises(EnderecoInvalidoError):
        Endereco(
            logradouro="Rua A",
            numero="10",
            cidade="Sao Paulo",
            estado="SP",
            cep="01000-000",
            latitude=Decimal("-23.55"),
        )


def test_rejeita_cliente_sem_nome() -> None:
    with pytest.raises(ClienteInvalidoError):
        Cliente(id=novo_id(), nome=" ")