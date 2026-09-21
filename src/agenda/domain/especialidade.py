from __future__ import annotations

import uuid
from dataclasses import dataclass

from agenda.domain.exceptions import ErroDominio


class EspecialidadeInvalidaError(ErroDominio):
    pass


@dataclass(frozen=True)
class Especialidade:
    id: uuid.UUID
    nome: str

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise EspecialidadeInvalidaError("nome da especialidade e obrigatorio")
