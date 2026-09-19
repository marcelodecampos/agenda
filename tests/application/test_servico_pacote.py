from decimal import Decimal

from agenda.application.criar_pacote import CriarPacote
from agenda.application.criar_servico import CriarServico
from agenda.domain.ids import novo_id
from agenda.domain.pacote import Pacote
from agenda.domain.servico import ModalidadeAtendimento, Servico
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.pacote_repository import PacoteRepository
from agenda.infrastructure.servico_repository import ServicoRepository


def test_criar_servico_persiste_servico() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = ServicoRepository(engine)
    use_case = CriarServico(repo)

    servico = Servico(
        id=novo_id(),
        nome="Manicure",
        categoria="unhas",
        duracao_base_minutos=60,
        preco_base=Decimal("80.00"),
        profissional_id=novo_id(),
        modalidades=(
            ModalidadeAtendimento(
                chave="domicilio",
                nome="Domicilio",
                ajuste_preco_percentual=Decimal("10"),
                ajuste_duracao_minutos=15,
            ),
        ),
    )

    salvo = use_case.executar(servico)
    encontrado = repo.buscar_por_id(servico.id)

    assert salvo.nome == servico.nome
    assert salvo.categorias == (servico.categoria,)
    assert salvo.nome_servico_id is not None
    assert encontrado is not None
    assert encontrado.nome == servico.nome
    assert encontrado.categorias == (servico.categoria,)
    assert encontrado.nome_servico_id == salvo.nome_servico_id


def test_nome_de_servico_pode_ter_varias_categorias() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = ServicoRepository(engine)

    primeiro = Servico(
        id=novo_id(),
        nome="Massagem",
        categoria="bem-estar",
        duracao_base_minutos=60,
        preco_base=Decimal("100.00"),
        organizacao_id=novo_id(),
    )
    segundo = Servico(
        id=novo_id(),
        nome="Massagem",
        categoria="terapias",
        duracao_base_minutos=60,
        preco_base=Decimal("100.00"),
        organizacao_id=novo_id(),
    )

    salvo_primeiro = repo.salvar(primeiro)
    salvo_segundo = repo.salvar(segundo)
    servicos = repo.listar()

    assert salvo_primeiro.nome_servico_id == salvo_segundo.nome_servico_id
    assert {categoria for servico in servicos for categoria in servico.categorias} == {
        "bem-estar",
        "terapias",
    }


def test_criar_pacote_persiste_pacote() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = PacoteRepository(engine)
    use_case = CriarPacote(repo)

    pacote = Pacote(
        id=novo_id(),
        nome="Combo unhas",
        servico_ids=(novo_id(), novo_id()),
        duracao_total_minutos=90,
        preco=Decimal("150.00"),
        profissional_id=novo_id(),
    )

    salvo = use_case.executar(pacote)
    encontrado = repo.buscar_por_id(pacote.id)

    assert salvo == pacote
    assert encontrado == pacote
