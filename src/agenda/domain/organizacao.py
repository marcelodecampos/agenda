import uuid
from dataclasses import dataclass, field

from agenda.domain.endereco import Endereco
from agenda.domain.especialidade import Especialidade
from agenda.domain.exceptions import OrganizacaoInvalidaError


@dataclass(frozen=True)
class Organizacao:
    """Estabelecimento ou pratica individual (autonomo puro = organizacao unipessoal)."""

    id: uuid.UUID
    nome: str
    nome_fantasia: str | None = None
    cnpj: str | None = None
    unipessoal: bool = False
    endereco: Endereco | None = None
    especialidades: tuple[Especialidade, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise OrganizacaoInvalidaError("nome e obrigatorio")
