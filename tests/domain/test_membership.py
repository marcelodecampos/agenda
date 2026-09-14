import pytest

from agenda.domain.exceptions import MembershipSemPapelError
from agenda.domain.ids import novo_id
from agenda.domain.membership import Membership
from agenda.domain.papel import Papel

DONO = Papel(
    id=novo_id(), chave="dono", nome="Dono", permissoes=frozenset({"agenda.configurar"})
)
GERENTE = Papel(
    id=novo_id(),
    chave="gerente",
    nome="Gerente",
    permissoes=frozenset({"estabelecimento.gerenciar_equipe"}),
)


def _novo_membership(papeis: list[Papel] | None = None) -> Membership:
    return Membership(
        id=novo_id(),
        usuario_id=novo_id(),
        organizacao_id=novo_id(),
        papeis=papeis or [DONO],
    )


def test_membership_verifica_permissao_do_papel_atribuido() -> None:
    membership = _novo_membership()

    assert membership.tem_permissao("agenda.configurar") is True
    assert membership.tem_permissao("estabelecimento.gerenciar_equipe") is False


def test_papeis_secundarios_somam_permissoes() -> None:
    membership = _novo_membership(papeis=[DONO, GERENTE])

    assert membership.tem_permissao("agenda.configurar") is True
    assert membership.tem_permissao("estabelecimento.gerenciar_equipe") is True


def test_membership_suspenso_nao_concede_nenhuma_permissao() -> None:
    membership = _novo_membership()
    membership.suspender()

    assert membership.tem_permissao("agenda.configurar") is False


def test_membership_reativado_volta_a_conceder_permissao() -> None:
    membership = _novo_membership()
    membership.suspender()
    membership.reativar()

    assert membership.tem_permissao("agenda.configurar") is True


def test_membership_sem_nenhum_papel_e_invalido() -> None:
    with pytest.raises(MembershipSemPapelError):
        Membership(
            id=novo_id(), usuario_id=novo_id(), organizacao_id=novo_id(), papeis=[]
        )


def test_nao_permite_remover_ultimo_papel() -> None:
    membership = _novo_membership()

    with pytest.raises(MembershipSemPapelError):
        membership.remover_papel(DONO)


def test_organizacao_id_none_representa_papel_global() -> None:
    membership = Membership(
        id=novo_id(), usuario_id=novo_id(), organizacao_id=None, papeis=[DONO]
    )

    assert membership.organizacao_id is None


def test_adicionar_papel_secundario() -> None:
    membership = _novo_membership()

    membership.adicionar_papel(GERENTE)

    assert membership.tem_permissao("estabelecimento.gerenciar_equipe") is True


def test_adicionar_papel_ja_atribuido_nao_duplica() -> None:
    membership = _novo_membership(papeis=[DONO, GERENTE])

    membership.adicionar_papel(GERENTE)

    assert membership.papeis.count(GERENTE) == 1


def test_remover_papel_secundario_mantendo_outro() -> None:
    membership = _novo_membership(papeis=[DONO, GERENTE])

    membership.remover_papel(GERENTE)

    assert membership.tem_permissao("estabelecimento.gerenciar_equipe") is False


def test_chaves_papeis_retorna_conjunto_de_chaves() -> None:
    membership = _novo_membership(papeis=[DONO, GERENTE])

    assert membership.chaves_papeis() == frozenset({"dono", "gerente"})
