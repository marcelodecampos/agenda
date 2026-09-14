import pytest

from agenda.domain.exceptions import UsuarioInvalidoError
from agenda.domain.ids import novo_id
from agenda.domain.usuario import Usuario


def test_cria_usuario_valido() -> None:
    usuario = Usuario(id=novo_id(), provider="keycloak", subject="abc123", nome="Maria")

    assert usuario.provider == "keycloak"
    assert usuario.subject == "abc123"


@pytest.mark.parametrize(
    "provider,subject,nome",
    [
        ("", "abc123", "Maria"),
        ("keycloak", "", "Maria"),
        ("keycloak", "abc123", ""),
    ],
)
def test_rejeita_usuario_com_campo_obrigatorio_vazio(
    provider: str, subject: str, nome: str
) -> None:
    with pytest.raises(UsuarioInvalidoError):
        Usuario(id=novo_id(), provider=provider, subject=subject, nome=nome)


def test_usuario_aceita_identificadores_de_contato() -> None:
    usuario = Usuario(
        id=novo_id(),
        provider="keycloak",
        subject="abc123",
        nome="Maria",
        cpf="12345678909",
        email="maria@example.com",
        telefone="+5511999999999",
    )

    assert usuario.cpf == "12345678909"
    assert usuario.email == "maria@example.com"
    assert usuario.telefone == "+5511999999999"


def test_usuario_rejeita_cpf_com_formato_invalido() -> None:
    with pytest.raises(UsuarioInvalidoError, match="cpf"):
        Usuario(
            id=novo_id(),
            provider="keycloak",
            subject="abc123",
            nome="Maria",
            cpf="123",
        )
