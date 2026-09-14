from __future__ import annotations

from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade


class RegistrarAtendimentoFidelidade:
    def executar(
        self,
        progresso: ProgressoFidelidade,
        programa: ProgramaFidelidade,
    ) -> ProgressoFidelidade:
        return progresso.registrar_atendimento()
