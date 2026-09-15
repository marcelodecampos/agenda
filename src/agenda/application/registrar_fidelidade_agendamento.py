from __future__ import annotations

import uuid

from agenda.domain.agendamento import Agendamento
from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade


class RegistrarFidelidadeAgendamento:
    def __init__(self, programas: object, progressos: object) -> None:
        self.programas = programas
        self.progressos = progressos

    def executar(self, agendamento: Agendamento) -> list[ProgressoFidelidade]:
        atualizados: list[ProgressoFidelidade] = []
        alvos = {(item.servico_id, item.pacote_id) for item in agendamento.itens}
        for programa in self.programas.listar():
            if not self._programa_aplicavel(programa, agendamento, alvos):
                continue
            progresso = self.progressos.buscar_por_id(
                programa.id, agendamento.cliente_id
            )
            if progresso is None:
                progresso = ProgressoFidelidade(
                    programa_id=programa.id,
                    cliente_id=agendamento.cliente_id,
                )
            atualizado = progresso.registrar_atendimento()
            self.progressos.salvar(atualizado)
            atualizados.append(atualizado)
        return atualizados

    @staticmethod
    def _programa_aplicavel(
        programa: ProgramaFidelidade,
        agendamento: Agendamento,
        alvos: set[tuple[uuid.UUID | None, uuid.UUID | None]],
    ) -> bool:
        if programa.profissional_id not in (None, agendamento.profissional_id):
            return False
        if programa.organizacao_id not in (None, agendamento.organizacao_id):
            return False
        return (programa.alvo_servico_id, programa.alvo_pacote_id) in alvos
