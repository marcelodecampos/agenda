from __future__ import annotations

from agenda.domain.servico import Servico


class CriarServico:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, servico: Servico) -> Servico:
        return self.repositorio.salvar(servico)
