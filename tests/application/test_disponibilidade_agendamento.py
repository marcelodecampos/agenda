from datetime import datetime
from decimal import Decimal

import pytest

from agenda.application.criar_agendamento import CriarAgendamento
from agenda.application.criar_disponibilidade import CriarDisponibilidade
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.disponibilidade import (
    Disponibilidade,
    IntervaloHorario,
    JanelaSemanal,
)
from agenda.domain.exceptions import AgendamentoInvalidoError
from agenda.domain.ids import novo_id
from agenda.infrastructure.agendamento_repository import AgendamentoRepository
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.disponibilidade_repository import DisponibilidadeRepository


def test_criar_agendamento_rejeita_conflito_do_mesmo_profissional() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = AgendamentoRepository(engine)
    profissional_id = novo_id()
    existente = Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=profissional_id,
        inicio=datetime(2026, 9, 14, 10),
        itens=(
            ItemAgendamento(
                servico_id=novo_id(),
                duracao_minutos=60,
                preco=Decimal("80"),
            ),
        ),
        status_atual="solicitado",
    )
    repo.salvar(existente)

    with pytest.raises(
        AgendamentoInvalidoError,
        match="horario solicitado ja esta ocupado",
    ):
        CriarAgendamento(repo).executar(
            Agendamento(
                id=novo_id(),
                cliente_id=novo_id(),
                profissional_id=profissional_id,
                inicio=datetime(2026, 9, 14, 10, 30),
                itens=(
                    ItemAgendamento(
                        servico_id=novo_id(),
                        duracao_minutos=30,
                        preco=Decimal("40"),
                    ),
                ),
                status_atual="solicitado",
            )
        )


def test_criar_disponibilidade_persiste_janela() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = DisponibilidadeRepository(engine)
    use_case = CriarDisponibilidade(repo)

    disponibilidade = Disponibilidade(
        id=novo_id(),
        semanal=(
            JanelaSemanal(
                dia_semana=0,
                intervalo=IntervaloHorario(inicio=datetime.strptime("09:00", "%H:%M").time(), fim=datetime.strptime("17:00", "%H:%M").time()),
            ),
        ),
        profissional_id=novo_id(),
    )

    salvo = use_case.executar(disponibilidade)
    encontrado = repo.buscar_por_id(disponibilidade.id)

    assert salvo == disponibilidade
    assert encontrado == disponibilidade


def test_criar_agendamento_persiste_agendamento() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = AgendamentoRepository(engine)
    use_case = CriarAgendamento(repo)

    agendamento = Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9, 0),
        itens=(
            ItemAgendamento(
                servico_id=novo_id(),
                duracao_minutos=60,
                preco=Decimal("80.00"),
            ),
        ),
        status_atual="solicitado",
    )

    salvo = use_case.executar(agendamento)
    encontrado = repo.buscar_por_id(agendamento.id)

    assert salvo == agendamento
    assert encontrado == agendamento
