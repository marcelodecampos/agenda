import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from agenda.domain.exceptions import ServicoInvalidoError


@dataclass(frozen=True)
class ModalidadeAtendimento:
    """Variacao comercial de um servico, sem criar uma nova regra de servico."""

    chave: str
    nome: str
    ajuste_preco_fixo: Decimal | None = None
    ajuste_preco_percentual: Decimal | None = None
    ajuste_duracao_minutos: int = 0

    def __post_init__(self) -> None:
        if not self.chave.strip():
            raise ServicoInvalidoError("chave da modalidade e obrigatoria")
        if not self.nome.strip():
            raise ServicoInvalidoError("nome da modalidade e obrigatorio")
        if (
            self.ajuste_preco_fixo is not None
            and self.ajuste_preco_percentual is not None
        ):
            raise ServicoInvalidoError(
                "modalidade nao pode ter ajuste fixo e percentual ao mesmo tempo"
            )
        if self.ajuste_duracao_minutos < 0:
            raise ServicoInvalidoError("ajuste de duracao nao pode ser negativo")


@dataclass(frozen=True)
class Servico:
    """Servico oferecido por um profissional, uma organizacao ou ambos."""

    id: uuid.UUID
    nome: str
    categoria: str
    duracao_base_minutos: int
    preco_base: Decimal
    profissional_id: uuid.UUID | None = None
    organizacao_id: uuid.UUID | None = None
    modalidades: tuple[ModalidadeAtendimento, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise ServicoInvalidoError("nome e obrigatorio")
        if not self.categoria.strip():
            raise ServicoInvalidoError("categoria e obrigatoria")
        if self.duracao_base_minutos <= 0:
            raise ServicoInvalidoError("duracao base deve ser positiva")
        if self.preco_base < 0:
            raise ServicoInvalidoError("preco base nao pode ser negativo")
        if self.profissional_id is None and self.organizacao_id is None:
            raise ServicoInvalidoError(
                "servico precisa pertencer a um profissional ou organizacao"
            )
        chaves = [modalidade.chave for modalidade in self.modalidades]
        if len(chaves) != len(set(chaves)):
            raise ServicoInvalidoError("modalidades nao podem ter chave duplicada")