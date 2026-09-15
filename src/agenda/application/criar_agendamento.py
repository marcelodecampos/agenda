from __future__ import annotations

from datetime import timedelta

from agenda.domain.agendamento import Agendamento
from agenda.domain.exceptions import AgendamentoInvalidoError


class CriarAgendamento:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(self, agendamento: Agendamento) -> Agendamento:
        inicio = agendamento.inicio.replace(tzinfo=None)
        fim = inicio + timedelta(minutes=agendamento.duracao_total_minutos)
        for existente in self.repositorio.listar():
            if existente.id == agendamento.id:
                continue
            if existente.profissional_id != agendamento.profissional_id:
                continue
            existente_inicio = existente.inicio.replace(tzinfo=None)
            existente_fim = existente_inicio + timedelta(
                minutes=existente.duracao_total_minutos
            )
            if existente_inicio < fim and inicio < existente_fim:
                raise AgendamentoInvalidoError(
                    "horario solicitado ja esta ocupado para o profissional"
                )
        return self.repositorio.salvar(agendamento)
