import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.exceptions import FidelidadeInvalidaError


@dataclass(frozen=True)
class RecompensaFidelidade:
    tipo: str
    valor: Decimal | None = None
    alvo_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if not self.tipo.strip():
            raise FidelidadeInvalidaError("tipo da recompensa e obrigatorio")
        if self.valor is None and self.alvo_id is None:
            raise FidelidadeInvalidaError(
                "recompensa precisa de valor ou alvo"
            )
        if self.valor is not None and self.valor < 0:
            raise FidelidadeInvalidaError("valor da recompensa nao pode ser negativo")


@dataclass(frozen=True)
class ProgramaFidelidade:
    id: uuid.UUID
    nome: str
    alvo_servico_id: uuid.UUID | None = None
    alvo_pacote_id: uuid.UUID | None = None
    atendimentos_necessarios: int = 1
    recompensa: RecompensaFidelidade | None = None
    segmento_cliente: str | None = None
    profissional_id: uuid.UUID | None = None
    organizacao_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise FidelidadeInvalidaError("nome e obrigatorio")
        if (self.alvo_servico_id is None) == (self.alvo_pacote_id is None):
            raise FidelidadeInvalidaError(
                "programa deve ter exatamente um alvo"
            )
        if self.atendimentos_necessarios <= 0:
            raise FidelidadeInvalidaError(
                "atendimentos necessarios deve ser positivo"
            )
        if self.recompensa is None:
            raise FidelidadeInvalidaError("recompensa e obrigatoria")
        if self.profissional_id is None and self.organizacao_id is None:
            raise FidelidadeInvalidaError(
                "programa precisa pertencer a um profissional ou organizacao"
            )

    def corresponde_ao_alvo(
        self, servico_id: uuid.UUID | None, pacote_id: uuid.UUID | None
    ) -> bool:
        return self.alvo_servico_id == servico_id and self.alvo_pacote_id == pacote_id


@dataclass(frozen=True)
class ProgressoFidelidade:
    programa_id: uuid.UUID
    cliente_id: uuid.UUID
    atendimentos_concluidos: int = 0

    def registrar_atendimento(self) -> "ProgressoFidelidade":
        return ProgressoFidelidade(
            programa_id=self.programa_id,
            cliente_id=self.cliente_id,
            atendimentos_concluidos=self.atendimentos_concluidos + 1,
        )

    def recompensa_disponivel(self, programa: ProgramaFidelidade) -> bool:
        return self.atendimentos_concluidos >= programa.atendimentos_necessarios