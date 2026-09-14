import uuid
from dataclasses import dataclass
import re

from agenda.domain.exceptions import UsuarioInvalidoError


@dataclass(frozen=True)
class Usuario:
    """Identidade interna vinculada a um provedor externo (Keycloak) via provider+subject."""

    id: uuid.UUID
    provider: str
    subject: str
    nome: str
    cpf: str | None = None
    email: str | None = None
    telefone: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise UsuarioInvalidoError("provider e obrigatorio")
        if not self.subject.strip():
            raise UsuarioInvalidoError("subject e obrigatorio")
        if not self.nome.strip():
            raise UsuarioInvalidoError("nome e obrigatorio")
        for campo, valor in (
            ("cpf", self.cpf),
            ("email", self.email),
            ("telefone", self.telefone),
        ):
            if valor is not None and not valor.strip():
                raise UsuarioInvalidoError(f"{campo} nao pode ser vazio")
        if self.cpf is not None and not re.fullmatch(r"\d{11}", self.cpf):
            raise UsuarioInvalidoError("cpf deve conter 11 digitos")
