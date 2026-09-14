import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from agenda.domain.exceptions import (
    AgendamentoInvalidoError,
    TransicaoAgendamentoNaoPermitidaError,
)


@dataclass(frozen=True)
class ItemAgendamento:
    """Snapshot comercial de um servico ou pacote no momento da reserva."""

    servico_id: uuid.UUID | None = None
    pacote_id: uuid.UUID | None = None
    duracao_minutos: int = 0
    preco: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if (self.servico_id is None) == (self.pacote_id is None):
            raise AgendamentoInvalidoError(
                "item deve referenciar exatamente um servico ou pacote"
            )
        if self.duracao_minutos <= 0:
            raise AgendamentoInvalidoError("duracao do item deve ser positiva")
        if self.preco < 0:
            raise AgendamentoInvalidoError("preco do item nao pode ser negativo")


@dataclass(frozen=True)
class StatusAgendamento:
    chave: str
    nome: str

    def __post_init__(self) -> None:
        if not self.chave.strip() or not self.nome.strip():
            raise AgendamentoInvalidoError("status precisa de chave e nome")


@dataclass(frozen=True)
class TransicaoStatus:
    de: str
    para: str
    atores: frozenset[str]

    def permite(self, status_atual: str, ator: str, novo_status: str) -> bool:
        return (
            self.de == status_atual
            and self.para == novo_status
            and ator in self.atores
        )


@dataclass(frozen=True)
class CatalogoStatus:
    status: tuple[StatusAgendamento, ...]
    transicoes: tuple[TransicaoStatus, ...]

    def __post_init__(self) -> None:
        chaves = [item.chave for item in self.status]
        if len(chaves) != len(set(chaves)):
            raise AgendamentoInvalidoError("catalogo nao pode repetir status")
        conhecidas = set(chaves)
        if any(
            transicao.de not in conhecidas or transicao.para not in conhecidas
            for transicao in self.transicoes
        ):
            raise AgendamentoInvalidoError(
                "transicao referencia status inexistente"
            )
        if any(not transicao.atores for transicao in self.transicoes):
            raise AgendamentoInvalidoError(
                "transicao precisa ter ao menos um ator permitido"
            )

    def existe(self, chave: str) -> bool:
        return any(item.chave == chave for item in self.status)

    def permite(self, de: str, para: str, ator: str) -> bool:
        return any(
            transicao.permite(de, ator, para) for transicao in self.transicoes
        )


@dataclass(frozen=True)
class RegistroStatus:
    status: str
    ator: str
    ocorrido_em: datetime


@dataclass
class Agendamento:
    id: uuid.UUID
    cliente_id: uuid.UUID
    profissional_id: uuid.UUID
    inicio: datetime
    itens: tuple[ItemAgendamento, ...]
    status_atual: str
    organizacao_id: uuid.UUID | None = None
    historico: list[RegistroStatus] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.itens:
            raise AgendamentoInvalidoError(
                "agendamento precisa ter ao menos um item"
            )
        if not self.status_atual.strip():
            raise AgendamentoInvalidoError("status inicial e obrigatorio")
        if not self.historico:
            self.historico.append(
                RegistroStatus(
                    status=self.status_atual,
                    ator="sistema",
                    ocorrido_em=self.inicio,
                )
            )

    @property
    def duracao_total_minutos(self) -> int:
        return sum(item.duracao_minutos for item in self.itens)

    @property
    def preco_total(self) -> Decimal:
        return sum((item.preco for item in self.itens), Decimal("0"))

    def transicionar_para(
        self,
        novo_status: str,
        ator: str,
        catalogo: CatalogoStatus,
        ocorrido_em: datetime,
    ) -> None:
        if not novo_status.strip() or not ator.strip():
            raise AgendamentoInvalidoError("status e ator sao obrigatorios")
        if not catalogo.existe(novo_status) or not catalogo.permite(
            self.status_atual, novo_status, ator
        ):
            raise TransicaoAgendamentoNaoPermitidaError(
                f"transicao de {self.status_atual} para {novo_status} nao permitida"
            )
        self.status_atual = novo_status
        self.historico.append(
            RegistroStatus(
                status=novo_status,
                ator=ator,
                ocorrido_em=ocorrido_em,
            )
        )