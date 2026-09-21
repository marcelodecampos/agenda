from __future__ import annotations

import uuid
from dataclasses import dataclass

from agenda.application.busca_textual import normalizar_texto, pontuar_busca
from agenda.domain.catalogo_servico import NomeServico


@dataclass(frozen=True)
class EntradaIndiceBusca:
    id: uuid.UUID
    nome: str
    nome_normalizado: str


class IndiceBuscaNomesServico:
    """Índice em memória dos nomes usados na descoberta pública."""

    def __init__(self) -> None:
        self._engine: object | None = None
        self._entradas: tuple[EntradaIndiceBusca, ...] = ()

    def garantir_atualizado(self, engine: object, nomes: list[NomeServico]) -> None:
        if self._engine is not engine or not self._entradas:
            self.recarregar(engine, nomes)

    def recarregar(self, engine: object, nomes: list[NomeServico]) -> int:
        self._engine = engine
        self._entradas = tuple(
            EntradaIndiceBusca(
                id=nome.id,
                nome=nome.nome,
                nome_normalizado=normalizar_texto(nome.nome),
            )
            for nome in nomes
        )
        return len(self._entradas)

    def buscar(self, termo: str, *, limite: int = 100) -> dict[uuid.UUID, float]:
        resultados = [
            (entrada.id, pontuar_busca(termo, entrada.nome_normalizado))
            for entrada in self._entradas
        ]
        return {
            id_: pontuacao
            for id_, pontuacao in sorted(
                (item for item in resultados if item[1] >= 0.72),
                key=lambda item: (-item[1], str(item[0])),
            )[:limite]
        }

    @property
    def quantidade(self) -> int:
        return len(self._entradas)

    def invalidar(self) -> None:
        self._engine = None