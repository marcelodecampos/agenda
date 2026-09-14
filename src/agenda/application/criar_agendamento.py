from __future__ import annotations

from agenda.domain.agendamento import Agendamento


class CriarAgendamento:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, agendamento: Agendamento) -> Agendamento:
        return self.repositorio.salvar(agendamento)
