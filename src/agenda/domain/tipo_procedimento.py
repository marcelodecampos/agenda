import uuid
from dataclasses import dataclass

from agenda.domain.exceptions import ErroDominio


class TipoProcedimentoInvalidoError(ErroDominio):
    pass


@dataclass(frozen=True)
class TipoProcedimento:
    """Catalogo controlado de tipos de procedimento (ex: Manicure), compartilhado
    entre saloes/autonomos para manter consistencia na busca/comparacao. Gerenciado
    apenas pelo administrador da plataforma; Servico.categoria (texto livre)
    continua existindo em paralelo para casos fora do catalogo."""

    id: uuid.UUID
    chave: str
    nome: str

    def __post_init__(self) -> None:
        if not self.chave.strip():
            raise TipoProcedimentoInvalidoError("chave e obrigatoria")
        if not self.nome.strip():
            raise TipoProcedimentoInvalidoError("nome e obrigatorio")
