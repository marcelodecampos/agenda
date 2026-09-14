import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.agendamento import Agendamento
from agenda.domain.exceptions import ComissaoInvalidaError


@dataclass(frozen=True)
class RegraComissao:
    id: uuid.UUID
    tipo: str
    valor: Decimal
    membership_id: uuid.UUID | None = None
    servico_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if self.tipo not in {"percentual", "fixa"}:
            raise ComissaoInvalidaError("tipo de comissao invalido")
        if self.valor < 0:
            raise ComissaoInvalidaError("valor da comissao nao pode ser negativo")
        if self.membership_id is None and self.servico_id is None:
            raise ComissaoInvalidaError(
                "regra precisa filtrar por membership ou servico"
            )
        if self.tipo == "percentual" and self.valor > 100:
            raise ComissaoInvalidaError("percentual nao pode exceder 100")

    def aplica_a(self, membership_id: uuid.UUID, servico_ids: set[uuid.UUID]) -> bool:
        return (self.membership_id in {None, membership_id}) and (
            self.servico_id is None or self.servico_id in servico_ids
        )

    def calcular(self, preco: Decimal) -> Decimal:
        if self.tipo == "percentual":
            return preco * self.valor / Decimal("100")
        return self.valor


def calcular_comissao(
    agendamento: Agendamento,
    membership_id: uuid.UUID,
    regras: tuple[RegraComissao, ...],
    status_concluido: str,
) -> Decimal:
    if agendamento.status_atual != status_concluido:
        return Decimal("0")
    servico_ids = {
        item.servico_id for item in agendamento.itens if item.servico_id is not None
    }
    regras_aplicaveis = [
        regra
        for regra in regras
        if regra.aplica_a(membership_id, servico_ids)
    ]
    if not regras_aplicaveis:
        return Decimal("0")
    return sum(
        (regra.calcular(agendamento.preco_total) for regra in regras_aplicaveis),
        Decimal("0"),
    )