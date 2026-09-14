import uuid
from dataclasses import dataclass

from agenda.domain.endereco import Endereco
from agenda.domain.exceptions import OrganizacaoInvalidaError


@dataclass(frozen=True)
class Organizacao:
    """Estabelecimento ou pratica individual (autonomo puro = organizacao unipessoal)."""

    id: uuid.UUID
    nome: str
    unipessoal: bool = False
    endereco: Endereco | None = None

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise OrganizacaoInvalidaError("nome e obrigatorio")
