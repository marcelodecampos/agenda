from __future__ import annotations

from agenda.domain.fidelidade import ProgressoFidelidade


class RegistrarProgressoFidelidade:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, progresso: ProgressoFidelidade) -> ProgressoFidelidade:
        atualizado = progresso.registrar_atendimento()
        return self.repositorio.salvar(atualizado)
