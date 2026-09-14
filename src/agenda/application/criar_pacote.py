from __future__ import annotations

from agenda.domain.pacote import Pacote


class CriarPacote:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, pacote: Pacote) -> Pacote:
        return self.repositorio.salvar(pacote)
