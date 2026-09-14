import uuid
from dataclasses import dataclass

from agenda.domain.exceptions import UsuarioInvalidoError


@dataclass(frozen=True)
class Usuario:
    """Identidade interna vinculada a um provedor externo (Keycloak) via provider+subject."""

    id: uuid.UUID
    provider: str
    subject: str
    nome: str

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise UsuarioInvalidoError("provider e obrigatorio")
        if not self.subject.strip():
            raise UsuarioInvalidoError("subject e obrigatorio")
        if not self.nome.strip():
            raise UsuarioInvalidoError("nome e obrigatorio")
