from __future__ import annotations

from agenda.domain.fidelidade import ProgramaFidelidade


class CriarProgramaFidelidade:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, programa: ProgramaFidelidade) -> ProgramaFidelidade:
        return self.repositorio.salvar(programa)
