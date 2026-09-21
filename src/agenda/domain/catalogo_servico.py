from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from agenda.domain.exceptions import ErroDominio


class CatalogoServicoInvalidoError(ErroDominio):
    pass


@dataclass(frozen=True)
class CategoriaServico:
    id: uuid.UUID
    nome: str

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise CatalogoServicoInvalidoError("nome da categoria e obrigatorio")


@dataclass(frozen=True)
class NomeServico:
    id: uuid.UUID
    nome: str
    categorias: tuple[CategoriaServico, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise CatalogoServicoInvalidoError("nome do servico e obrigatorio")
