import pytest

from agenda.domain.exceptions import PapelInvalidoError
from agenda.domain.ids import novo_id
from agenda.domain.papel import Papel


def test_papel_concede_permissao_do_seu_catalogo() -> None:
    papel = Papel(
        id=novo_id(),
        chave="dono",
        nome="Dono",
        permissoes=frozenset({"agenda.configurar", "servico.gerenciar"}),
    )

    assert papel.concede("agenda.configurar") is True
    assert papel.concede("plataforma.aprovar_cadastro") is False


def test_papel_sem_chave_e_invalido() -> None:
    with pytest.raises(PapelInvalidoError):
        Papel(id=novo_id(), chave="", nome="Dono")


def test_papel_sem_nome_e_invalido() -> None:
    with pytest.raises(PapelInvalidoError):
        Papel(id=novo_id(), chave="dono", nome="")
