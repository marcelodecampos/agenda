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
