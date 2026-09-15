from datetime import datetime, timedelta

from agenda.application.processar_notificacoes import ProcessarNotificacoesVencidas
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.ids import novo_id
from agenda.domain.lembrete import ConfiguracaoLembrete
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.notificacao_repository import NotificacaoAgendamentoRepository
from agenda.ports import DestinatarioNotificacao
from agenda.application.criar_notificacao_agendamento import CriarNotificacaoAgendamento


class EntregadorFalso:
    def __init__(self, falhar: bool = False) -> None:
        self.falhar = falhar
        self.enviadas = []

    def enviar(self, notificacao) -> None:
        if self.falhar:
            raise RuntimeError("falha externa")
        self.enviadas.append(notificacao)


def _criar_notificacao(engine):
    agendamento = Agendamento(
        id=novo_id(), cliente_id=novo_id(), profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9),
        itens=(ItemAgendamento(servico_id=novo_id(), duracao_minutos=30, preco=0),),
        status_atual="solicitado",
    )
    CriarNotificacaoAgendamento(NotificacaoAgendamentoRepository(engine)).executar(
        agendamento,
        ConfiguracaoLembrete(timedelta(hours=2), "email"),
        DestinatarioNotificacao("dest", "email", "a@b.com"),
        "Lembrete",
    )


def test_processa_notificacao_vencida_apenas_uma_vez():
    engine = criar_engine_sqlite_memoria()
    _criar_notificacao(engine)
    repo = NotificacaoAgendamentoRepository(engine)
    entregador = EntregadorFalso()
    processador = ProcessarNotificacoesVencidas(repo, entregador)

    resultado = processador.executar(datetime(2026, 9, 14, 8))
    novamente = processador.executar(datetime(2026, 9, 14, 8))

    assert resultado == {"processadas": 1, "enviadas": 1, "falhas": 0}
    assert novamente == {"processadas": 0, "enviadas": 0, "falhas": 0}
    assert len(entregador.enviadas) == 1