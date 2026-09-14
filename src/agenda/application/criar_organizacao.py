from __future__ import annotations

from agenda.domain.organizacao import Organizacao


class CriarOrganizacao:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, organizacao: Organizacao) -> Organizacao:
        return self.repositorio.salvar(organizacao)
