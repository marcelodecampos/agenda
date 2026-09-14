from datetime import datetime, timedelta

from agenda.application.criar_notificacao_agendamento import CriarNotificacaoAgendamento
from agenda.domain.agendamento import Agendamento, ItemAgendamento
from agenda.domain.ids import novo_id
from agenda.domain.lembrete import ConfiguracaoLembrete
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.notificacao_repository import NotificacaoAgendamentoRepository
from agenda.ports import DestinatarioNotificacao


def test_cria_notificacao_agendamento_persiste_o_payload() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = NotificacaoAgendamentoRepository(engine)
    use_case = CriarNotificacaoAgendamento(repo)

    agendamento = Agendamento(
        id=novo_id(),
        cliente_id=novo_id(),
        profissional_id=novo_id(),
        inicio=datetime(2026, 9, 14, 9, 0),
        itens=(ItemAgendamento(servico_id=novo_id(), duracao_minutos=60, preco=0),),
        status_atual="solicitado",
    )
    configuracao = ConfiguracaoLembrete(timedelta(hours=2), "email")
    destinatario = DestinatarioNotificacao("dest-1", "email", "cliente@teste.com")

    notificacao = use_case.executar(
        agendamento=agendamento,
        configuracao=configuracao,
        destinatario=destinatario,
        mensagem="Seu horario esta proximo",
    )
    encontrado = repo.buscar_por_agendamento_id(str(agendamento.id))

    assert notificacao.enviar_em == datetime(2026, 9, 14, 7, 0)
    assert encontrado == notificacao
