from decimal import Decimal

from agenda.application.criar_programa_fidelidade import CriarProgramaFidelidade
from agenda.application.registrar_progresso_fidelidade import RegistrarProgressoFidelidade
from agenda.domain.fidelidade import ProgramaFidelidade, ProgressoFidelidade, RecompensaFidelidade
from agenda.domain.ids import novo_id
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.fidelidade_repository import ProgramaFidelidadeRepository, ProgressoFidelidadeRepository


def test_programa_fidelidade_persiste_e_recupera() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = ProgramaFidelidadeRepository(engine)
    use_case = CriarProgramaFidelidade(repo)

    programa = ProgramaFidelidade(
        id=novo_id(),
        nome="Cartao manicure",
        alvo_servico_id=novo_id(),
        atendimentos_necessarios=3,
        recompensa=RecompensaFidelidade(tipo="desconto_percentual", valor=Decimal("10")),
        profissional_id=novo_id(),
    )

    salvo = use_case.executar(programa)
    encontrado = repo.buscar_por_id(programa.id)

    assert salvo == programa
    assert encontrado == programa


def test_progresso_fidelidade_persiste_a_contagem() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = ProgressoFidelidadeRepository(engine)
    use_case = RegistrarProgressoFidelidade(repo)

    progresso = ProgressoFidelidade(programa_id=novo_id(), cliente_id=novo_id())
    atualizado = use_case.executar(progresso)
    encontrado = repo.buscar_por_id(progresso.programa_id, progresso.cliente_id)

    assert atualizado == progresso.registrar_atendimento()
    assert encontrado == progresso.registrar_atendimento()
