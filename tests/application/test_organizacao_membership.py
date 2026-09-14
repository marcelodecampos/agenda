from agenda.application.criar_organizacao import CriarOrganizacao
from agenda.application.criar_membership import CriarMembership
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
