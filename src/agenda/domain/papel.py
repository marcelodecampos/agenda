import uuid
from dataclasses import dataclass, field

from agenda.domain.exceptions import PapelInvalidoError


@dataclass(frozen=True)
class Papel:
    """Catalogo de papel (role): permissoes sao dados, nunca fixas em codigo."""

    id: uuid.UUID
    chave: str
    nome: str
    permissoes: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.chave.strip():
            raise PapelInvalidoError("chave e obrigatoria")
        if not self.nome.strip():
            raise PapelInvalidoError("nome e obrigatorio")

    def concede(self, permissao: str) -> bool:
        return permissao in self.permissoes
