import uuid

import pytest

from agenda.application.registrar_usuario import RegistrarUsuario
from agenda.domain.ids import novo_id
from agenda.domain.usuario import Usuario
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.usuario_repository import UsuarioRepository


def test_registrar_usuario_persiste_usuario_no_repositorio() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = UsuarioRepository(engine)
    use_case = RegistrarUsuario(repo)

    usuario = Usuario(
        id=novo_id(),
        provider="keycloak",
        subject="abc123",
        nome="Maria",
    )

    salvo = use_case.executar(usuario)
    encontrado = repo.buscar_por_provider_subject("keycloak", "abc123")

    assert salvo == usuario
    assert encontrado == usuario


def test_registro_rejeita_usuario_duplicado() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = UsuarioRepository(engine)
    use_case = RegistrarUsuario(repo)

    usuario = Usuario(
        id=novo_id(),
        provider="keycloak",
        subject="abc123",
        nome="Maria",
    )

    use_case.executar(usuario)

    try:
        use_case.executar(
            Usuario(
                id=novo_id(),
                provider="keycloak",
                subject="abc123",
                nome="Outra",
            )
        )
        raise AssertionError("esperava erro de usuario duplicado")
    except ValueError as exc:
        assert "duplicado" in str(exc).lower()


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("cpf", "12345678909"),
        ("email", "maria@example.com"),
        ("telefone", "+5511999999999"),
    ],
)
def test_registro_rejeita_identificador_de_contato_duplicado(
    campo: str, valor: str
) -> None:
    engine = criar_engine_sqlite_memoria()
    repo = UsuarioRepository(engine)
    use_case = RegistrarUsuario(repo)

    primeiro = Usuario(
        id=novo_id(),
        provider="keycloak",
        subject=f"primeiro-{campo}",
        nome="Maria",
        **{campo: valor},
    )
    use_case.executar(primeiro)

    segundo = Usuario(
        id=novo_id(),
        provider="keycloak",
        subject=f"segundo-{campo}",
        nome="Outra pessoa",
        **{campo: valor},
    )
    with pytest.raises(ValueError, match="duplicado"):
        use_case.executar(segundo)
