from agenda.application.sincronizar_usuario_identidade import SincronizarUsuarioIdentidade
from agenda.domain.ids import novo_id
from agenda.domain.usuario import Usuario
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.usuario_repository import UsuarioRepository
from agenda.ports import IdentidadeExterna


def test_sincroniza_identidade_cria_usuario_interno() -> None:
    repositorio = UsuarioRepository(criar_engine_sqlite_memoria())
    identidade = IdentidadeExterna(
        provider="keycloak",
        subject="subject-novo",
        nome="Maria Silva",
        cpf="12345678909",
        email="maria@example.com",
        telefone="+5511999999999",
    )

    usuario = SincronizarUsuarioIdentidade(repositorio).executar(identidade)

    assert usuario.id is not None
    assert usuario.cpf == "12345678909"
    assert repositorio.buscar_por_provider_subject("keycloak", "subject-novo") == usuario


def test_sincroniza_identidade_atualiza_usuario_existente() -> None:
    repositorio = UsuarioRepository(criar_engine_sqlite_memoria())
    usuario_original = repositorio.salvar(
        Usuario(
            id=novo_id(),
            provider="keycloak",
            subject="subject-existente",
            nome="Nome antigo",
        )
    )
    identidade = IdentidadeExterna(
        provider="keycloak",
        subject="subject-existente",
        nome="Nome atualizado",
        email="atualizado@example.com",
    )

    atualizado = SincronizarUsuarioIdentidade(repositorio).executar(identidade)

    assert atualizado.id == usuario_original.id
    assert atualizado.nome == "Nome atualizado"
    assert atualizado.email == "atualizado@example.com"