from agenda.domain.ids import novo_id
from agenda.domain.papel import Papel
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.membership_repository import PapelRepository


def test_papel_repository_persiste_e_busca_catalogo_por_chave() -> None:
    repository = PapelRepository(criar_engine_sqlite_memoria())
    papel = Papel(
        id=novo_id(),
        chave="dono",
        nome="Dono",
        permissoes=frozenset({"agenda.configurar"}),
    )

    repository.salvar(papel)

    assert repository.buscar_por_chave("dono") == papel
    assert repository.listar() == [papel]