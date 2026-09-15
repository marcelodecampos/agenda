from datetime import date, datetime, time
from decimal import Decimal

from agenda.application.consultar_horarios_livres import ConsultarHorariosLivres
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.disponibilidade import Disponibilidade, IntervaloHorario, JanelaSemanal
from agenda.domain.ids import novo_id
from agenda.infrastructure.agendamento_repository import AgendamentoRepository
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.disponibilidade_repository import DisponibilidadeRepository


def test_consulta_horarios_livres_remove_conflitos() -> None:
    engine = criar_engine_sqlite_memoria()
    profissional_id = novo_id()
    data_consulta = date(2026, 9, 14)
    DisponibilidadeRepository(engine).salvar(
        Disponibilidade(
            id=novo_id(),
            semanal=(
                JanelaSemanal(
                    dia_semana=0,
                    intervalo=IntervaloHorario(time(9), time(12)),
                ),
            ),
            profissional_id=profissional_id,
        )
    )
    AgendamentoRepository(engine).salvar(
        Agendamento(
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
    )

    slots = ConsultarHorariosLivres(
        DisponibilidadeRepository(engine), AgendamentoRepository(engine)
    ).executar(
        profissional_id=profissional_id,
        data=data_consulta,
        duracao_minutos=60,
        passo_minutos=60,
    )

    assert [(slot.inicio.hour, slot.fim.hour) for slot in slots] == [
        (9, 10),
        (11, 12),
    ]


def test_consulta_horarios_livres_respeita_folga() -> None:
    engine = criar_engine_sqlite_memoria()
    profissional_id = novo_id()
    slots = ConsultarHorariosLivres(
        DisponibilidadeRepository(engine), AgendamentoRepository(engine)
    ).executar(
        profissional_id=profissional_id,
        data=date(2026, 9, 14),
        duracao_minutos=30,
    )

    assert slots == []