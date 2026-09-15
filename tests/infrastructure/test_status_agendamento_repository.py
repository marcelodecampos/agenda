from agenda.domain.agendamento import CatalogoStatus, StatusAgendamento, TransicaoStatus
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.status_agendamento_repository import CatalogoStatusRepository


def test_catalogo_status_persiste_e_recarrega() -> None:
    repository = CatalogoStatusRepository(criar_engine_sqlite_memoria())
    catalogo = CatalogoStatus(
        status=(StatusAgendamento("solicitado", "Solicitado"), StatusAgendamento("confirmado", "Confirmado")),
        transicoes=(TransicaoStatus("solicitado", "confirmado", frozenset({"profissional"})),),
    )

    repository.salvar(catalogo)

    assert repository.obter() == catalogo