from datetime import date, time

import pytest

from agenda.domain.disponibilidade import (
    Disponibilidade,
    ExcecaoAgenda,
    IntervaloHorario,
    JanelaSemanal,
)
from agenda.domain.exceptions import DisponibilidadeInvalidaError
from agenda.domain.ids import novo_id


def test_retorna_janela_semanal_para_a_data_consultada() -> None:
    intervalo = IntervaloHorario(time(9), time(17))
    disponibilidade = Disponibilidade(
        id=novo_id(),
        semanal=(JanelaSemanal(dia_semana=0, intervalo=intervalo),),
        profissional_id=novo_id(),
    )

    assert disponibilidade.intervalos_para(date(2026, 9, 14)) == (intervalo,)
    assert disponibilidade.intervalos_para(date(2026, 9, 15)) == ()


def test_excecao_substitui_janela_semanal() -> None:
    semanal = IntervaloHorario(time(9), time(17))
    excecao = ExcecaoAgenda(
        data=date(2026, 9, 14),
        intervalos=(IntervaloHorario(time(12), time(18)),),
    )
    disponibilidade = Disponibilidade(
        id=novo_id(),
        semanal=(JanelaSemanal(dia_semana=0, intervalo=semanal),),
        excecoes=(excecao,),
        profissional_id=novo_id(),
    )

    assert disponibilidade.intervalos_para(date(2026, 9, 14)) == excecao.intervalos


def test_excecao_sem_intervalos_representa_folga() -> None:
    disponibilidade = Disponibilidade(
        id=novo_id(),
        semanal=(
            JanelaSemanal(
                dia_semana=0, intervalo=IntervaloHorario(time(9), time(17))
            ),
        ),
        excecoes=(ExcecaoAgenda(data=date(2026, 9, 14)),),
        organizacao_id=novo_id(),
    )

    assert disponibilidade.intervalos_para(date(2026, 9, 14)) == ()


def test_rejeita_intervalo_invertido() -> None:
    with pytest.raises(DisponibilidadeInvalidaError):
        IntervaloHorario(time(17), time(9))


def test_rejeita_intervalos_semanais_sobrepostos() -> None:
    with pytest.raises(DisponibilidadeInvalidaError):
        Disponibilidade(
            id=novo_id(),
            semanal=(
                JanelaSemanal(dia_semana=0, intervalo=IntervaloHorario(time(9), time(12))),
                JanelaSemanal(dia_semana=0, intervalo=IntervaloHorario(time(11), time(14))),
            ),
            profissional_id=novo_id(),
        )


def test_rejeita_excecoes_duplicadas_na_mesma_data() -> None:
    data_consulta = date(2026, 9, 14)

    with pytest.raises(DisponibilidadeInvalidaError):
        Disponibilidade(
            id=novo_id(),
            excecoes=(ExcecaoAgenda(data_consulta), ExcecaoAgenda(data_consulta)),
            profissional_id=novo_id(),
        )


def test_rejeita_disponibilidade_sem_proprietario() -> None:
    with pytest.raises(DisponibilidadeInvalidaError):
        Disponibilidade(id=novo_id())


def test_disponibilidade_confere_se_intervalo_esta_dentro_da_janela() -> None:
    disponibilidade = Disponibilidade(
        id=novo_id(),
        semanal=(
            JanelaSemanal(
                dia_semana=0,
                intervalo=IntervaloHorario(time(9), time(17)),
            ),
        ),
        profissional_id=novo_id(),
    )

    assert disponibilidade.esta_disponivel(date(2026, 9, 14), time(10), time(11)) is True
    assert disponibilidade.esta_disponivel(date(2026, 9, 14), time(8), time(9)) is False
    assert disponibilidade.esta_disponivel(date(2026, 9, 14), time(16), time(18)) is False


def test_disponibilidade_em_excecao_com_folga_nao_aceita_agendamento() -> None:
    disponibilidade = Disponibilidade(
        id=novo_id(),
        semanal=(
            JanelaSemanal(
                dia_semana=0,
                intervalo=IntervaloHorario(time(9), time(17)),
            ),
        ),
        excecoes=(ExcecaoAgenda(data=date(2026, 9, 14)),),
        profissional_id=novo_id(),
    )

    assert disponibilidade.esta_disponivel(date(2026, 9, 14), time(10), time(11)) is False