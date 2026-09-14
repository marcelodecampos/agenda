import pytest

from agenda.domain.endereco import Endereco
from agenda.domain.exceptions import OrganizacaoInvalidaError
from agenda.domain.ids import novo_id
from agenda.domain.organizacao import Organizacao


def test_cria_organizacao_valida() -> None:
    organizacao = Organizacao(id=novo_id(), nome="Salao da Ana")

    assert organizacao.unipessoal is False


def test_cria_organizacao_unipessoal_para_autonomo_puro() -> None:
    organizacao = Organizacao(id=novo_id(), nome="Joao Cabeleireiro", unipessoal=True)

    assert organizacao.unipessoal is True


def test_organizacao_pode_ter_endereco() -> None:
    endereco = Endereco("Rua A", "10", "Sao Paulo", "SP", "01000-000")
    organizacao = Organizacao(id=novo_id(), nome="Salao", endereco=endereco)

    assert organizacao.endereco == endereco


def test_rejeita_organizacao_sem_nome() -> None:
    with pytest.raises(OrganizacaoInvalidaError):
        Organizacao(id=novo_id(), nome="   ")
