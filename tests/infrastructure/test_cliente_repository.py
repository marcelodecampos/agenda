from agenda.domain.endereco import Cliente, Endereco
from agenda.domain.ids import novo_id
from agenda.infrastructure.cliente_repository import ClienteRepository
from agenda.infrastructure.db import criar_engine_sqlite_memoria


def test_anonimiza_cliente_preservando_id() -> None:
    repository = ClienteRepository(criar_engine_sqlite_memoria())
    cliente = Cliente(
        id=novo_id(),
        nome="Maria Silva",
        email="maria@example.com",
        endereco=Endereco("Rua A", "10", "Sao Paulo", "SP", "01000-000"),
    )
    repository.salvar(cliente)

    anonimizado = repository.anonimizar(cliente.id)

    assert anonimizado is not None
    assert anonimizado.id == cliente.id
    assert anonimizado.nome == "Cliente anonimizado"
    assert anonimizado.email is None
    assert anonimizado.endereco is None