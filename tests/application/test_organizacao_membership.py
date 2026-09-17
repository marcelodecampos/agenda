from agenda.application.criar_organizacao import CriarOrganizacao
from agenda.application.criar_membership import CriarMembership
from agenda.application.criar_profissional_independente import (
    CriarProfissionalIndependente,
)
from agenda.application.criar_organizacao_com_equipe import CriarOrganizacaoComEquipe
from agenda.domain.ids import novo_id
from agenda.domain.organizacao import Organizacao
from agenda.domain.papel import Papel
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.organizacao_repository import OrganizacaoRepository
from agenda.infrastructure.membership_repository import MembershipRepository


def test_criar_organizacao_persiste_entidade() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = OrganizacaoRepository(engine)
    use_case = CriarOrganizacao(repo)

    organizacao = Organizacao(id=novo_id(), nome="Salao da Ana")
    salvo = use_case.executar(organizacao)
    encontrado = repo.buscar_por_id(organizacao.id)

    assert salvo == organizacao
    assert encontrado == organizacao


def test_criar_membership_persiste_vinculo_com_papeis() -> None:
    engine = criar_engine_sqlite_memoria()
    org_repo = OrganizacaoRepository(engine)
    member_repo = MembershipRepository(engine)

    use_case = CriarMembership(member_repo)
    papel = Papel(id=novo_id(), chave="dono", nome="Dono", permissoes=frozenset({"agenda.configurar"}))

    membership = use_case.executar(
        usuario_id=novo_id(),
        organizacao_id=novo_id(),
        papeis=(papel,),
    )

    assert membership.papeis == [papel]
    assert member_repo.buscar_por_id(membership.id) == membership


def test_criar_profissional_independente_cria_organizacao_unipessoal_e_dono() -> None:
    engine = criar_engine_sqlite_memoria()
    org_repo = OrganizacaoRepository(engine)
    member_repo = MembershipRepository(engine)
    papel = Papel(
        id=novo_id(),
        chave="dono",
        nome="Dono",
        permissoes=frozenset({"agenda.configurar"}),
    )
    usuario_id = novo_id()

    perfil = CriarProfissionalIndependente(org_repo, member_repo).executar(
        usuario_id=usuario_id,
        nome="Ana Estetica",
        papel_dono=papel,
    )

    assert perfil.organizacao.unipessoal is True
    assert perfil.membership.usuario_id == usuario_id
    assert perfil.membership.organizacao_id == perfil.organizacao.id
    assert perfil.membership.chaves_papeis() == frozenset({"dono"})
    assert org_repo.buscar_por_id(perfil.organizacao.id) == perfil.organizacao
    assert member_repo.buscar_por_id(perfil.membership.id) == perfil.membership


def test_criar_organizacao_com_equipe_cria_organizacao_nao_unipessoal_e_dono() -> None:
    engine = criar_engine_sqlite_memoria()
    org_repo = OrganizacaoRepository(engine)
    member_repo = MembershipRepository(engine)
    papel = Papel(
        id=novo_id(),
        chave="dono",
        nome="Dono",
        permissoes=frozenset({"estabelecimento.gerenciar_equipe"}),
    )
    usuario_id = novo_id()

    perfil = CriarOrganizacaoComEquipe(org_repo, member_repo).executar(
        usuario_id=usuario_id,
        nome="Salao Beleza Pura",
        papel_dono=papel,
    )

    assert perfil.organizacao.unipessoal is False
    assert perfil.membership.usuario_id == usuario_id
    assert perfil.membership.organizacao_id == perfil.organizacao.id
    assert perfil.membership.chaves_papeis() == frozenset({"dono"})
    assert org_repo.buscar_por_id(perfil.organizacao.id) == perfil.organizacao
    assert member_repo.buscar_por_id(perfil.membership.id) == perfil.membership
