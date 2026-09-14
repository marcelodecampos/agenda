import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.exceptions import PacoteInvalidoError


@dataclass(frozen=True)
class Pacote:
    """Combinacao configuravel de um ou mais servicos oferecidos."""

    id: uuid.UUID
    nome: str
    servico_ids: tuple[uuid.UUID, ...]
    duracao_total_minutos: int
    preco: Decimal
    profissional_id: uuid.UUID | None = None
    organizacao_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise PacoteInvalidoError("nome e obrigatorio")
        if not self.servico_ids:
            raise PacoteInvalidoError("pacote precisa ter ao menos um servico")
        if len(self.servico_ids) != len(set(self.servico_ids)):
            raise PacoteInvalidoError("pacote nao pode repetir servicos")
        if self.duracao_total_minutos <= 0:
            raise PacoteInvalidoError("duracao total deve ser positiva")
        if self.preco < 0:
            raise PacoteInvalidoError("preco nao pode ser negativo")
        if self.profissional_id is None and self.organizacao_id is None:
            raise PacoteInvalidoError(
                "pacote precisa pertencer a um profissional ou organizacao"
            )