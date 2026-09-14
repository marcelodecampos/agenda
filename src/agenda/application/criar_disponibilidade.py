from __future__ import annotations

from agenda.domain.disponibilidade import Disponibilidade


class CriarDisponibilidade:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, disponibilidade: Disponibilidade) -> Disponibilidade:
        return self.repositorio.salvar(disponibilidade)
