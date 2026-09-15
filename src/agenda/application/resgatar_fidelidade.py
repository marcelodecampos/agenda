from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.fidelidade import AplicacaoRecompensa, ProgramaFidelidade, ProgressoFidelidade, aplicar_recompensa


@dataclass(frozen=True)
class ResgateResultado:
    aplicacao: AplicacaoRecompensa
    progresso: ProgressoFidelidade
    resgate_id: uuid.UUID


class ResgatarFidelidade:
    def __init__(self, programas: object, progressos: object, resgates: object) -> None:
        self.programas = programas
        self.progressos = progressos
        self.resgates = resgates

    def executar(
        self,
        *,
        programa_id: uuid.UUID,
        cliente_id: uuid.UUID,
        preco: Decimal,
        agendamento_id: uuid.UUID | None = None,
    ) -> ResgateResultado:
        programa = self.programas.buscar_por_id(programa_id)
        if programa is None:
            raise ValueError("programa de fidelidade nao encontrado")
        progresso = self.progressos.buscar_por_id(programa_id, cliente_id)
        if progresso is None:
            raise ValueError("cliente ainda nao possui progresso neste programa")
        aplicacao = aplicar_recompensa(programa, progresso, preco)
        atualizado = progresso.consumir_recompensa(programa)
        self.progressos.salvar(atualizado)
        resgate_id = self.resgates.salvar(
            programa_id=programa_id,
            cliente_id=cliente_id,
            aplicacao=aplicacao,
            agendamento_id=agendamento_id,
        )
        return ResgateResultado(aplicacao, atualizado, resgate_id)
