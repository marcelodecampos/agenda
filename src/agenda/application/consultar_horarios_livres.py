from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from agenda.domain.agendamento import Agendamento
from agenda.domain.disponibilidade import Disponibilidade


@dataclass(frozen=True)
class HorarioLivre:
    inicio: datetime
    fim: datetime


class ConsultarHorariosLivres:
    def __init__(self, disponibilidades: object, agendamentos: object) -> None:
        self.disponibilidades = disponibilidades
        self.agendamentos = agendamentos

    def executar(
        self,
        *,
        profissional_id: uuid.UUID,
        data: date,
        duracao_minutos: int,
        passo_minutos: int = 15,
        organizacao_id: uuid.UUID | None = None,
    ) -> list[HorarioLivre]:
        if duracao_minutos <= 0:
            raise ValueError("duracao deve ser positiva")
        if passo_minutos <= 0:
            raise ValueError("passo deve ser positivo")

        disponibilidades = [
            disponibilidade
            for disponibilidade in self.disponibilidades.listar()
            if self._aplica_disponibilidade(
                disponibilidade, profissional_id, organizacao_id
            )
        ]
        agendamentos = [
            agendamento
            for agendamento in self.agendamentos.listar()
            if agendamento.profissional_id == profissional_id
            and agendamento.inicio.date() == data
        ]

        slots: list[HorarioLivre] = []
        vistos: set[tuple[datetime, datetime]] = set()
        passo = timedelta(minutes=passo_minutos)
        duracao = timedelta(minutes=duracao_minutos)
        for disponibilidade in disponibilidades:
            for intervalo in disponibilidade.intervalos_para(data):
                inicio = datetime.combine(data, intervalo.inicio)
                fim_janela = datetime.combine(data, intervalo.fim)
                while inicio + duracao <= fim_janela:
                    fim = inicio + duracao
                    chave = (inicio, fim)
                    if chave not in vistos and not any(
                        self._conflita(agendamento, inicio, fim)
                        for agendamento in agendamentos
                    ):
                        slots.append(HorarioLivre(inicio=inicio, fim=fim))
                        vistos.add(chave)
                    inicio += passo

        return sorted(slots, key=lambda slot: slot.inicio)

    @staticmethod
    def _aplica_disponibilidade(
        disponibilidade: Disponibilidade,
        profissional_id: uuid.UUID,
        organizacao_id: uuid.UUID | None,
    ) -> bool:
        return (
            disponibilidade.profissional_id == profissional_id
            or (
                organizacao_id is not None
                and disponibilidade.organizacao_id == organizacao_id
            )
        )

    @staticmethod
    def _conflita(
        agendamento: Agendamento,
        inicio: datetime,
        fim: datetime,
    ) -> bool:
        agendamento_inicio = agendamento.inicio.replace(tzinfo=None)
        agendamento_fim = agendamento_inicio + timedelta(
            minutes=agendamento.duracao_total_minutos
        )
        return agendamento_inicio < fim and inicio < agendamento_fim