import uuid

from fastapi.testclient import TestClient
import pytest

from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.main import (
    app,
    exigir_configurar_agenda,
    exigir_configurar_comissao,
    exigir_configurar_estabelecimento,
    exigir_configurar_fidelidade,
    exigir_gerenciar_catalogos,
    exigir_gerenciar_equipe,
    exigir_gerenciar_pacote,
    exigir_gerenciar_servico,
    exigir_solicitar_agendamento,
    identidade_autenticada,
    PublicRateLimiter,
)
from agenda.ports import IdentidadeExterna


client = TestClient(app)


@pytest.fixture(autouse=True)
def permitir_servico_nos_testes_existentes():
    dependencias = {
        identidade_autenticada,
        exigir_configurar_agenda,
        exigir_configurar_comissao,
        exigir_configurar_estabelecimento,
        exigir_configurar_fidelidade,
        exigir_gerenciar_catalogos,
        exigir_gerenciar_equipe,
        exigir_gerenciar_pacote,
        exigir_gerenciar_servico,
        exigir_solicitar_agendamento,
    }
    anteriores = {
        dependencia: app.dependency_overrides.get(dependencia)
        for dependencia in dependencias
    }
    for dependencia in dependencias:
        app.dependency_overrides[dependencia] = lambda: None
    yield
    for dependencia, anterior in anteriores.items():
        if anterior is None:
            app.dependency_overrides.pop(dependencia, None)
        else:
            app.dependency_overrides[dependencia] = anterior


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agenda"}


def test_endpoint_publico_aplica_rate_limit() -> None:
    original = app.state.public_rate_limiter
    app.state.public_rate_limiter = PublicRateLimiter(limit=1)
    try:
        first_response = client.get("/health")
        second_response = client.get("/health")
    finally:
        app.state.public_rate_limiter = original

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.headers["Retry-After"] == "60"


def test_auth_me_exige_bearer_token() -> None:
    original = app.dependency_overrides.pop(identidade_autenticada)
    try:
        response = client.get("/auth/me")
    finally:
        app.dependency_overrides[identidade_autenticada] = original

    assert response.status_code == 401
    assert response.json()["detail"] == "Bearer token obrigatorio"


def test_auth_me_consulta_identidade_no_keycloak() -> None:
    class IdentityAdapterStub:
        def obter_identidade(self, token: str):
            assert token == "token-123"
            from agenda.ports import IdentidadeExterna

            return IdentidadeExterna(
                provider="keycloak",
                subject="abc123",
                nome="Maria da Silva",
            )

    original_adapter = app.state.identity_adapter
    original_dependency = app.dependency_overrides.pop(identidade_autenticada)
    app.state.identity_adapter = IdentityAdapterStub()
    try:
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer token-123"},
        )
    finally:
        app.state.identity_adapter = original_adapter
        app.dependency_overrides[identidade_autenticada] = original_dependency

    assert response.status_code == 200
    assert response.json() == {
        "provider": "keycloak",
        "subject": "abc123",
        "nome": "Maria da Silva",
    }


def test_auth_me_acessos_retorna_permissoes_do_usuario() -> None:
    from agenda.domain.membership import Membership
    from agenda.domain.papel import Papel
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.membership_repository import MembershipRepository
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    original_engine = app.state.engine
    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    usuario = Usuario(
        id=uuid.uuid7(),
        provider="keycloak",
        subject="access-user",
        nome="Maria Silva",
    )
    UsuarioRepository(engine).salvar(usuario)
    MembershipRepository(engine).salvar(
        Membership(
            id=uuid.uuid7(),
            usuario_id=usuario.id,
            organizacao_id=None,
            papeis=[
                Papel(
                    id=uuid.uuid7(),
                    chave="cliente",
                    nome="Cliente",
                    permissoes=frozenset({"agendamento.solicitar"}),
                )
            ],
        )
    )

    class IdentityAdapterStub:
        def obter_identidade(self, token: str):
            from agenda.ports import IdentidadeExterna

            return IdentidadeExterna(
                provider="keycloak",
                subject="access-user",
                nome="Maria Silva",
            )

    original_adapter = app.state.identity_adapter
    original_dependency = app.dependency_overrides.pop(identidade_autenticada)
    app.state.identity_adapter = IdentityAdapterStub()
    try:
        response = client.get(
            "/auth/me/acessos",
            headers={"Authorization": "Bearer token-123"},
        )
    finally:
        app.state.engine = original_engine
        app.state.identity_adapter = original_adapter
        app.dependency_overrides[identidade_autenticada] = original_dependency

    assert response.status_code == 200
    assert response.json()[0]["permissoes"] == ["agendamento.solicitar"]


def test_criar_servico_exige_autenticacao() -> None:
    original = app.dependency_overrides.pop(exigir_gerenciar_servico)
    original_identity = app.dependency_overrides.pop(identidade_autenticada)
    try:
        response = client.post(
            "/servicos",
            json={
                "nome": "Servico protegido",
                "categoria": "beleza",
                "duracao_base_minutos": 30,
                "preco_base": "50.00",
            },
        )
    finally:
        app.dependency_overrides[exigir_gerenciar_servico] = original
        app.dependency_overrides[identidade_autenticada] = original_identity

    assert response.status_code == 401


def test_criar_servico_exige_permissao_no_usuario_interno() -> None:
    original = app.dependency_overrides.pop(exigir_gerenciar_servico)
    original_identity = app.dependency_overrides.pop(identidade_autenticada)
    original_adapter = app.state.identity_adapter
    class IdentityAdapterStub:
        def obter_identidade(self, token: str) -> IdentidadeExterna:
            return IdentidadeExterna(
                provider="keycloak",
                subject="sem-acesso",
                nome="Sem Acesso",
            )

    app.state.identity_adapter = IdentityAdapterStub()
    try:
        response = client.post(
            "/servicos",
            headers={"Authorization": "Bearer token-123"},
            json={
                "nome": "Servico protegido",
                "categoria": "beleza",
                "duracao_base_minutos": 30,
                "preco_base": "50.00",
            },
        )
    finally:
        app.state.identity_adapter = original_adapter
        app.dependency_overrides[exigir_gerenciar_servico] = original
        app.dependency_overrides[identidade_autenticada] = original_identity

    assert response.status_code == 403


def test_registrar_usuario_endpoint() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    response = client.post(
        "/usuarios",
        json={
            "provider": "keycloak",
            "subject": "user-123",
            "nome": "Maria Silva",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "keycloak"
    assert payload["subject"] == "user-123"
    assert payload["nome"] == "Maria Silva"


def test_criar_organizacao_endpoint() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    response = client.post(
        "/organizacoes",
        json={
            "nome": "Salão Bela",
            "unipessoal": False,
            "endereco": {
                "logradouro": "Rua das Flores",
                "numero": "100",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01000-000",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["nome"] == "Salão Bela"
    assert payload["unipessoal"] is False
    assert payload["endereco"]["cidade"] == "São Paulo"


def test_criar_profissional_independente_endpoint_usa_papel_do_catalogo() -> None:
    from agenda.domain.papel import Papel
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.membership_repository import (
        MembershipRepository,
        PapelRepository,
    )
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    usuario = Usuario(
        id=uuid.uuid7(),
        provider="keycloak",
        subject="profissional-1",
        nome="Ana Silva",
    )
    UsuarioRepository(engine).salvar(usuario)
    PapelRepository(engine).salvar(
        Papel(
            id=uuid.uuid7(),
            chave="dono",
            nome="Dono",
            permissoes=frozenset({"estabelecimento.configurar_dados"}),
        )
    )

    identidade_anterior = app.dependency_overrides[identidade_autenticada]
    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak",
        subject="profissional-1",
        nome="Ana Silva",
    )
    try:
        response = client.post(
            "/profissionais/independente",
            json={
                "nome": "Ana Estetica",
                "endereco": {
                    "logradouro": "Rua A",
                    "numero": "10",
                    "cidade": "Sao Paulo",
                    "estado": "SP",
                    "cep": "01000-000",
                },
            },
        )
    finally:
        app.dependency_overrides[identidade_autenticada] = identidade_anterior

    assert response.status_code == 200
    payload = response.json()
    assert payload["organizacao"]["unipessoal"] is True
    assert payload["organizacao"]["nome"] == "Ana Estetica"
    assert payload["membership"]["usuario_id"] == str(usuario.id)
    assert payload["membership"]["organizacao_id"] == payload["organizacao"]["id"]
    assert payload["membership"]["papeis"][0]["chave"] == "dono"
    assert MembershipRepository(engine).listar_por_usuario_id(usuario.id)


def test_criar_organizacao_com_equipe_endpoint_cria_organizacao_nao_unipessoal() -> None:
    from agenda.domain.papel import Papel
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.membership_repository import (
        MembershipRepository,
        PapelRepository,
    )
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    usuario = Usuario(
        id=uuid.uuid7(),
        provider="keycloak",
        subject="dono-salao-1",
        nome="Camila Fernandes",
    )
    UsuarioRepository(engine).salvar(usuario)
    PapelRepository(engine).salvar(
        Papel(
            id=uuid.uuid7(),
            chave="dono",
            nome="Dono",
            permissoes=frozenset({"estabelecimento.gerenciar_equipe"}),
        )
    )

    identidade_anterior = app.dependency_overrides[identidade_autenticada]
    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak",
        subject="dono-salao-1",
        nome="Camila Fernandes",
    )
    try:
        response = client.post(
            "/organizacoes/com-equipe",
            json={"nome": "Salão Beleza Pura"},
        )
    finally:
        app.dependency_overrides[identidade_autenticada] = identidade_anterior

    assert response.status_code == 200
    payload = response.json()
    assert payload["organizacao"]["unipessoal"] is False
    assert payload["membership"]["usuario_id"] == str(usuario.id)
    assert payload["membership"]["organizacao_id"] == payload["organizacao"]["id"]
    assert payload["membership"]["papeis"][0]["chave"] == "dono"
    assert MembershipRepository(engine).listar_por_usuario_id(usuario.id)


def test_criar_membership_usa_permissoes_do_catalogo() -> None:
    from agenda.domain.membership import Membership
    from agenda.domain.papel import Papel
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.membership_repository import MembershipRepository, PapelRepository
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    organizacao_id = uuid.uuid7()
    usuario = Usuario(
        id=uuid.uuid7(),
        provider="keycloak",
        subject="membro-1",
        nome="Joao Silva",
    )
    UsuarioRepository(engine).salvar(usuario)
    PapelRepository(engine).salvar(
        Papel(
            id=uuid.uuid7(),
            chave="funcionario",
            nome="Funcionario",
            permissoes=frozenset({"agenda.visualizar"}),
        )
    )
    MembershipRepository(engine).salvar(
        Membership(
            id=uuid.uuid7(),
            usuario_id=usuario.id,
            organizacao_id=organizacao_id,
            papeis=[
                Papel(
                    id=uuid.uuid7(),
                    chave="dono",
                    nome="Dono",
                    permissoes=frozenset({"estabelecimento.gerenciar_equipe"}),
                )
            ],
        )
    )
    identidade_anterior = app.dependency_overrides[exigir_gerenciar_equipe]
    app.dependency_overrides[exigir_gerenciar_equipe] = lambda: IdentidadeExterna(
        provider="keycloak", subject="membro-1", nome="Joao Silva"
    )

    try:
        response = client.post(
            "/memberships",
            json={
                "usuario_id": str(usuario.id),
                "organizacao_id": str(organizacao_id),
                "papeis": ["funcionario"],
            },
        )
    finally:
        app.dependency_overrides[exigir_gerenciar_equipe] = identidade_anterior

    assert response.status_code == 200
    assert response.json()["papeis"][0]["chave"] == "funcionario"
    assert response.json()["papeis"][0]["permissoes"] == ["agenda.visualizar"]


def test_criar_membership_rejeita_papel_fora_do_catalogo() -> None:
    from agenda.domain.membership import Membership
    from agenda.domain.papel import Papel
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.membership_repository import MembershipRepository
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    usuario_id = uuid.uuid7()
    organizacao_id = uuid.uuid7()
    UsuarioRepository(engine).salvar(
        Usuario(
            id=usuario_id,
            provider="keycloak",
            subject="membro-invalido",
            nome="Joao Silva",
        )
    )
    MembershipRepository(engine).salvar(
        Membership(
            id=uuid.uuid7(),
            usuario_id=usuario_id,
            organizacao_id=organizacao_id,
            papeis=[
                Papel(
                    id=uuid.uuid7(),
                    chave="dono",
                    nome="Dono",
                    permissoes=frozenset({"estabelecimento.gerenciar_equipe"}),
                )
            ],
        )
    )
    identidade_anterior = app.dependency_overrides[exigir_gerenciar_equipe]
    app.dependency_overrides[exigir_gerenciar_equipe] = lambda: IdentidadeExterna(
        provider="keycloak", subject="membro-invalido", nome="Joao Silva"
    )

    try:
        response = client.post(
            "/memberships",
            json={
                "usuario_id": str(usuario_id),
                "organizacao_id": str(organizacao_id),
                "papeis": ["papel_inventado"],
            },
        )
    finally:
        app.dependency_overrides[exigir_gerenciar_equipe] = identidade_anterior

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "papel nao encontrado no catalogo: papel_inventado"
    )


def test_criar_servico_endpoint() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    response = client.post(
        "/servicos",
        json={
            "nome": "Manicure",
            "categoria": "unhas",
            "duracao_base_minutos": 60,
            "preco_base": "80.00",
            "profissional_id": "00000000-0000-0000-0000-000000000001",
            "modalidades": [
                {
                    "chave": "domicilio",
                    "nome": "Domicilio",
                    "ajuste_preco_percentual": "10",
                    "ajuste_duracao_minutos": 15,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["nome"] == "Manicure"
    assert payload["categoria"] == "unhas"
    assert payload["modalidades"][0]["chave"] == "domicilio"


def test_criar_servico_independente_exige_profissional_ou_organizacao() -> None:
    response = client.post(
        "/servicos",
        json={
            "nome": "Servico sem ofertante",
            "categoria": "beleza",
            "duracao_base_minutos": 30,
            "preco_base": "50.00",
        },
    )

    assert response.status_code == 422
    assert "servico precisa pertencer" in str(response.json()["detail"])


def test_criar_disponibilidade_exige_profissional_ou_organizacao() -> None:
    response = client.post(
        "/disponibilidades",
        json={
            "semanal": [
                {
                    "dia_semana": 1,
                    "intervalo": {"inicio": "09:00:00", "fim": "18:00:00"},
                }
            ],
            "excecoes": [],
        },
    )

    assert response.status_code == 422
    assert "disponibilidade precisa pertencer" in str(response.json()["detail"])


def test_criar_agendamento_rejeita_item_sem_servico_ou_pacote() -> None:
    response = client.post(
        "/agendamentos",
        json={
            "cliente_id": str(uuid.uuid7()),
            "profissional_id": str(uuid.uuid7()),
            "inicio": "2026-09-20T14:00:00-03:00",
            "itens": [
                {"duracao_minutos": 60, "preco": "100.00"},
            ],
            "status_atual": "solicitado",
        },
    )

    assert response.status_code == 422
    assert "item deve referenciar exatamente" in str(response.json()["detail"])


def test_consultar_horarios_livres_endpoint_remove_agendamento_ocupado() -> None:
    from datetime import datetime, time
    from decimal import Decimal

    from agenda.domain.agendamento import Agendamento, ItemAgendamento
    from agenda.domain.disponibilidade import (
        Disponibilidade,
        IntervaloHorario,
        JanelaSemanal,
    )
    from agenda.infrastructure.agendamento_repository import AgendamentoRepository
    from agenda.infrastructure.disponibilidade_repository import DisponibilidadeRepository

    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    profissional_id = uuid.uuid7()
    DisponibilidadeRepository(engine).salvar(
        Disponibilidade(
            id=uuid.uuid7(),
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
            id=uuid.uuid7(),
            cliente_id=uuid.uuid7(),
            profissional_id=profissional_id,
            inicio=datetime(2026, 9, 14, 10),
            itens=(
                ItemAgendamento(
                    servico_id=uuid.uuid7(),
                    duracao_minutos=60,
                    preco=Decimal("80"),
                ),
            ),
            status_atual="solicitado",
        )
    )

    response = client.get(
        "/horarios-livres",
        params={
            "profissional_id": str(profissional_id),
            "data": "2026-09-14",
            "duracao_minutos": 60,
            "passo_minutos": 60,
        },
    )

    assert response.status_code == 200
    assert [slot["inicio"][11:16] for slot in response.json()] == [
        "09:00",
        "11:00",
    ]


def test_transicionar_agendamento_usa_catalogo_persistido() -> None:
    from datetime import datetime
    from decimal import Decimal

    from agenda.domain.agendamento import Agendamento, ItemAgendamento
    from agenda.infrastructure.agendamento_repository import AgendamentoRepository
    from agenda.infrastructure.status_agendamento_repository import CatalogoStatusRepository
    from agenda.domain.agendamento import CatalogoStatus, StatusAgendamento, TransicaoStatus

    engine = criar_engine_sqlite_memoria()
    app.state.engine = engine
    agendamento = Agendamento(
        id=uuid.uuid7(),
        cliente_id=uuid.uuid7(),
        profissional_id=uuid.uuid7(),
        inicio=datetime(2026, 9, 14, 10),
        itens=(ItemAgendamento(servico_id=uuid.uuid7(), duracao_minutos=30, preco=Decimal("40")),),
        status_atual="solicitado",
    )
    AgendamentoRepository(engine).salvar(agendamento)
    CatalogoStatusRepository(engine).salvar(
        CatalogoStatus(
            status=(StatusAgendamento("solicitado", "Solicitado"), StatusAgendamento("confirmado", "Confirmado")),
            transicoes=(TransicaoStatus("solicitado", "confirmado", frozenset({"profissional"})),),
        )
    )

    response = client.post(
        f"/agendamentos/{agendamento.id}/transicoes",
        json={"novo_status": "confirmado", "ator": "profissional"},
    )

    assert response.status_code == 200
    assert response.json()["status_atual"] == "confirmado"


def test_listar_e_buscar_usuarios_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    created = client.post(
        "/usuarios",
        json={
            "provider": "keycloak",
            "subject": "user-list-1",
            "nome": "Ana Souza",
        },
    )
    user_id = created.json()["id"]

    list_response = client.get("/usuarios")
    get_response = client.get(f"/usuarios/{user_id}")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert get_response.status_code == 200
    assert get_response.json()["subject"] == "user-list-1"


def test_listar_e_buscar_organizacoes_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    created = client.post(
        "/organizacoes",
        json={
            "nome": "Clínica Central",
            "unipessoal": True,
            "endereco": {
                "logradouro": "Av. Paulista",
                "numero": "123",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01311-000",
            },
        },
    )
    org_id = created.json()["id"]

    list_response = client.get("/organizacoes")
    get_response = client.get(f"/organizacoes/{org_id}")

    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert len(list_response.json()) == 1
    assert get_response.json()["nome"] == "Clínica Central"


def test_atualizar_e_remover_pacote_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    profissional_id = uuid.uuid7()
    servico = client.post(
        "/servicos",
        json={
            "nome": "Corte",
            "categoria": "cabelo",
            "duracao_base_minutos": 30,
            "preco_base": "40.00",
            "profissional_id": str(profissional_id),
        },
    ).json()

    criado = client.post(
        "/pacotes",
        json={
            "nome": "Combo Corte",
            "servico_ids": [servico["id"]],
            "duracao_total_minutos": 30,
            "preco": "35.00",
            "profissional_id": str(profissional_id),
        },
    )
    assert criado.status_code == 200
    pacote_id = criado.json()["id"]

    atualizado = client.put(
        f"/pacotes/{pacote_id}",
        json={
            "nome": "Combo Corte Promo",
            "servico_ids": [servico["id"]],
            "duracao_total_minutos": 30,
            "preco": "30.00",
            "profissional_id": str(profissional_id),
        },
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Combo Corte Promo"

    removido = client.delete(f"/pacotes/{pacote_id}")
    assert removido.status_code == 200
    assert client.get(f"/pacotes/{pacote_id}").status_code == 404


def test_atualizar_e_remover_disponibilidade_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    profissional_id = uuid.uuid7()

    criada = client.post(
        "/disponibilidades",
        json={
            "profissional_id": str(profissional_id),
            "semanal": [
                {"dia_semana": 1, "intervalo": {"inicio": "09:00:00", "fim": "18:00:00"}}
            ],
            "excecoes": [],
        },
    )
    assert criada.status_code == 200
    disponibilidade_id = criada.json()["id"]

    atualizada = client.put(
        f"/disponibilidades/{disponibilidade_id}",
        json={
            "profissional_id": str(profissional_id),
            "semanal": [
                {"dia_semana": 2, "intervalo": {"inicio": "10:00:00", "fim": "19:00:00"}}
            ],
            "excecoes": [],
        },
    )
    assert atualizada.status_code == 200
    assert atualizada.json()["semanal"][0]["dia_semana"] == 2

    removida = client.delete(f"/disponibilidades/{disponibilidade_id}")
    assert removida.status_code == 200


def test_atualizar_e_remover_programa_fidelidade_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    profissional_id = uuid.uuid7()
    servico = client.post(
        "/servicos",
        json={
            "nome": "Corte Fidelidade",
            "categoria": "cabelo",
            "duracao_base_minutos": 30,
            "preco_base": "40.00",
            "profissional_id": str(profissional_id),
        },
    ).json()

    criado = client.post(
        "/programas-fidelidade",
        json={
            "nome": "Fidelidade Corte",
            "profissional_id": str(profissional_id),
            "alvo_servico_id": servico["id"],
            "atendimentos_necessarios": 5,
            "recompensa": {"tipo": "desconto_percentual", "valor": "10"},
        },
    )
    assert criado.status_code == 200
    programa_id = criado.json()["id"]

    atualizado = client.put(
        f"/programas-fidelidade/{programa_id}",
        json={
            "nome": "Fidelidade Corte VIP",
            "profissional_id": str(profissional_id),
            "alvo_servico_id": servico["id"],
            "atendimentos_necessarios": 3,
            "recompensa": {"tipo": "desconto_percentual", "valor": "20"},
        },
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Fidelidade Corte VIP"

    removido = client.delete(f"/programas-fidelidade/{programa_id}")
    assert removido.status_code == 200


def test_regra_comissao_crud_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    profissional_id = uuid.uuid7()
    servico = client.post(
        "/servicos",
        json={
            "nome": "Manicure",
            "categoria": "unhas",
            "duracao_base_minutos": 30,
            "preco_base": "25.00",
            "profissional_id": str(profissional_id),
        },
    ).json()

    regra_id = str(uuid.uuid7())
    criada = client.post(
        "/comissoes/regras",
        json={"id": regra_id, "tipo": "percentual", "valor": "10", "servico_id": servico["id"]},
    )
    assert criada.status_code == 200

    busca = client.get(f"/comissoes/regras/{regra_id}")
    assert busca.status_code == 200
    assert busca.json()["valor"] == "10"

    atualizada = client.put(
        f"/comissoes/regras/{regra_id}",
        json={"id": regra_id, "tipo": "percentual", "valor": "15", "servico_id": servico["id"]},
    )
    assert atualizada.status_code == 200
    assert atualizada.json()["valor"] == "15"

    removida = client.delete(f"/comissoes/regras/{regra_id}")
    assert removida.status_code == 200
    assert client.get(f"/comissoes/regras/{regra_id}").status_code == 404


def test_catalogo_papeis_crud_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    criado = client.post(
        "/catalogo/papeis",
        json={"chave": "recepcionista", "nome": "Recepcionista", "permissoes": ["agenda.visualizar"]},
    )
    assert criado.status_code == 200
    papel_id = criado.json()["id"]

    listado = client.get("/catalogo/papeis")
    assert listado.status_code == 200
    assert any(item["chave"] == "recepcionista" for item in listado.json())

    duplicado = client.post(
        "/catalogo/papeis",
        json={"chave": "recepcionista", "nome": "Recepcionista", "permissoes": []},
    )
    assert duplicado.status_code == 409

    atualizado = client.put(
        f"/catalogo/papeis/{papel_id}",
        json={
            "chave": "recepcionista",
            "nome": "Recepcionista Senior",
            "permissoes": ["agenda.visualizar", "cliente.ver_ficha"],
        },
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Recepcionista Senior"

    removido = client.delete(f"/catalogo/papeis/{papel_id}")
    assert removido.status_code == 200


def test_catalogo_status_agendamento_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    obtido = client.get("/catalogo/status-agendamento")
    assert obtido.status_code == 200
    assert obtido.json() == {"status": [], "transicoes": []}

    atualizado = client.put(
        "/catalogo/status-agendamento",
        json={
            "status": [{"chave": "solicitado", "nome": "Solicitado"}],
            "transicoes": [],
        },
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["status"] == [{"chave": "solicitado", "nome": "Solicitado"}]


def test_catalogo_tipos_procedimento_crud_e_vinculo_com_servico() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    criado = client.post(
        "/catalogo/tipos-procedimento",
        json={"chave": "manicure", "nome": "Manicure"},
    )
    assert criado.status_code == 200
    tipo_id = criado.json()["id"]

    duplicado = client.post(
        "/catalogo/tipos-procedimento",
        json={"chave": "manicure", "nome": "Manicure"},
    )
    assert duplicado.status_code == 409

    listado = client.get("/catalogo/tipos-procedimento")
    assert listado.status_code == 200
    assert any(item["chave"] == "manicure" for item in listado.json())

    profissional_id = uuid.uuid7()
    servico = client.post(
        "/servicos",
        json={
            "nome": "Manicure simples",
            "categoria": "unhas",
            "duracao_base_minutos": 30,
            "preco_base": "30.00",
            "profissional_id": str(profissional_id),
            "tipo_procedimento_id": tipo_id,
        },
    )
    assert servico.status_code == 200
    assert servico.json()["tipo_procedimento_id"] == tipo_id

    atualizado = client.put(
        f"/catalogo/tipos-procedimento/{tipo_id}",
        json={"chave": "manicure", "nome": "Manicure Tradicional"},
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Manicure Tradicional"

    removido = client.delete(f"/catalogo/tipos-procedimento/{tipo_id}")
    assert removido.status_code == 200


def test_catalogo_nomes_servico_crud() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    criado = client.post(
        "/catalogo/nomes-servico",
        json={"nome": "Manicure"},
    )
    assert criado.status_code == 200
    nome_id = criado.json()["id"]

    duplicado = client.post(
        "/catalogo/nomes-servico",
        json={"nome": "Manicure"},
    )
    assert duplicado.status_code == 409

    listado = client.get("/catalogo/nomes-servico")
    assert listado.status_code == 200
    assert listado.json() == [{"id": nome_id, "nome": "Manicure"}]

    buscado = client.get(f"/catalogo/nomes-servico/{nome_id}")
    assert buscado.status_code == 200
    assert buscado.json()["nome"] == "Manicure"

    atualizado = client.put(
        f"/catalogo/nomes-servico/{nome_id}",
        json={"nome": "Manicure tradicional"},
    )
    assert atualizado.status_code == 200
    assert atualizado.json()["nome"] == "Manicure tradicional"

    removido = client.delete(f"/catalogo/nomes-servico/{nome_id}")
    assert removido.status_code == 200
    assert client.get(f"/catalogo/nomes-servico/{nome_id}").status_code == 404


def test_listar_servicos_endpoint() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    client.post(
        "/servicos",
        json={
            "nome": "Corte de cabelo",
            "categoria": "beleza",
            "duracao_base_minutos": 45,
            "preco_base": "70.00",
            "organizacao_id": "00000000-0000-0000-0000-000000000099",
            "modalidades": [
                {
                    "chave": "premium",
                    "nome": "Premium",
                    "ajuste_preco_fixo": "10.00",
                    "ajuste_duracao_minutos": 10,
                }
            ],
        },
    )

    response = client.get("/servicos")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["nome"] == "Corte de cabelo"


def test_atualizar_e_deletar_usuario_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    created = client.post(
        "/usuarios",
        json={
            "provider": "keycloak",
            "subject": "user-update-delete",
            "nome": "Usuário Antigo",
        },
    )
    user_id = created.json()["id"]

    update_response = client.put(
        f"/usuarios/{user_id}",
        json={
            "provider": "keycloak",
            "subject": "user-update-delete",
            "nome": "Usuário Atualizado",
        },
    )
    delete_response = client.delete(f"/usuarios/{user_id}")
    get_after_delete = client.get(f"/usuarios/{user_id}")

    assert update_response.status_code == 200
    assert update_response.json()["nome"] == "Usuário Atualizado"
    assert delete_response.status_code == 200
    assert get_after_delete.status_code == 404


def test_atualizar_e_deletar_servico_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    created = client.post(
        "/servicos",
        json={
            "nome": "Corte simples",
            "categoria": "beleza",
            "duracao_base_minutos": 30,
            "preco_base": "50.00",
            "organizacao_id": "00000000-0000-0000-0000-000000000099",
            "modalidades": [
                {
                    "chave": "basico",
                    "nome": "Básico",
                    "ajuste_preco_fixo": "5.00",
                    "ajuste_duracao_minutos": 5,
                }
            ],
        },
    )
    service_id = created.json()["id"]

    update_response = client.put(
        f"/servicos/{service_id}",
        json={
            "nome": "Corte premium",
            "categoria": "beleza",
            "duracao_base_minutos": 40,
            "preco_base": "75.00",
            "organizacao_id": "00000000-0000-0000-0000-000000000099",
            "modalidades": [
                {
                    "chave": "premium",
                    "nome": "Premium",
                    "ajuste_preco_fixo": "15.00",
                    "ajuste_duracao_minutos": 10,
                }
            ],
        },
    )
    delete_response = client.delete(f"/servicos/{service_id}")
    get_after_delete = client.get(f"/servicos/{service_id}")

    assert update_response.status_code == 200
    assert update_response.json()["nome"] == "Corte premium"
    assert delete_response.status_code == 200
    assert get_after_delete.status_code == 404


def test_listar_clientes_endpoint_retorna_apenas_proprio_sem_permissao() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    usuario = Usuario(id=uuid.uuid7(), provider="keycloak", subject="cliente-lista-1", nome="Ana")
    UsuarioRepository(app.state.engine).salvar(usuario)

    identidade_anterior = app.dependency_overrides[identidade_autenticada]
    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak", subject="cliente-lista-1", nome="Ana"
    )
    try:
        client.post("/clientes", json={"nome": "Ana Cliente"})
        outro = client.post("/clientes", json={"nome": "Outro Cliente"})
        assert outro.status_code == 200

        listado = client.get("/clientes")
    finally:
        app.dependency_overrides[identidade_autenticada] = identidade_anterior

    assert listado.status_code == 200
    assert len(listado.json()) == 2


def test_listar_e_buscar_lembretes_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    profissional_id = uuid.uuid7()
    UsuarioRepository(app.state.engine).salvar(
        Usuario(id=profissional_id, provider="keycloak", subject="prof-lembrete-1", nome="Prof")
    )
    servico = client.post(
        "/servicos",
        json={
            "nome": "Corte Lembrete",
            "categoria": "cabelo",
            "duracao_base_minutos": 30,
            "preco_base": "40.00",
            "profissional_id": str(profissional_id),
        },
    ).json()

    agendamento = client.post(
        "/agendamentos",
        json={
            "cliente_id": str(uuid.uuid7()),
            "profissional_id": str(profissional_id),
            "inicio": "2026-10-01T10:00:00-03:00",
            "itens": [
                {"servico_id": servico["id"], "duracao_minutos": 30, "preco": "40.00"}
            ],
            "status_atual": "solicitado",
        },
    ).json()

    criado = client.post(
        f"/agendamentos/{agendamento['id']}/lembretes",
        json={
            "configuracao": {"antecedencia_horas": 2, "canal": "email"},
            "destinatario": {"id": "cliente-1", "canal": "email", "destino": "a@example.com"},
            "mensagem": "Lembrete de teste",
        },
    )
    assert criado.status_code == 200

    identidade_anterior = app.dependency_overrides[identidade_autenticada]
    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak", subject="prof-lembrete-1", nome="Prof"
    )
    try:
        listado = client.get("/lembretes")
        busca = client.get(f"/agendamentos/{agendamento['id']}/lembretes")
    finally:
        app.dependency_overrides[identidade_autenticada] = identidade_anterior

    assert listado.status_code == 200
    assert len(listado.json()) == 1

    assert busca.status_code == 200
    assert busca.json()["mensagem"] == "Lembrete de teste"


def test_listar_e_buscar_resgates_fidelidade_endpoints() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    profissional_id = uuid.uuid7()
    UsuarioRepository(app.state.engine).salvar(
        Usuario(id=profissional_id, provider="keycloak", subject="prof-resgate-1", nome="Prof")
    )
    cliente_id = uuid.uuid7()
    servico = client.post(
        "/servicos",
        json={
            "nome": "Corte Resgate",
            "categoria": "cabelo",
            "duracao_base_minutos": 30,
            "preco_base": "40.00",
            "profissional_id": str(profissional_id),
        },
    ).json()
    programa = client.post(
        "/programas-fidelidade",
        json={
            "nome": "Fidelidade Resgate",
            "profissional_id": str(profissional_id),
            "alvo_servico_id": servico["id"],
            "atendimentos_necessarios": 1,
            "recompensa": {"tipo": "desconto_percentual", "valor": "10"},
        },
    ).json()
    client.post(
        "/progresso-fidelidade",
        json={
            "programa_id": programa["id"],
            "cliente_id": str(cliente_id),
            "atendimentos_concluidos": 1,
        },
    )

    resgatado = client.post(
        "/fidelidade/resgates",
        json={"programa_id": programa["id"], "cliente_id": str(cliente_id), "preco": "40.00"},
    )
    assert resgatado.status_code == 200
    resgate_id = resgatado.json()["resgate_id"]

    identidade_anterior = app.dependency_overrides[identidade_autenticada]
    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak", subject="prof-resgate-1", nome="Prof"
    )
    try:
        listado = client.get("/fidelidade/resgates")
        busca = client.get(f"/fidelidade/resgates/{resgate_id}")
    finally:
        app.dependency_overrides[identidade_autenticada] = identidade_anterior

    assert listado.status_code == 200
    assert len(listado.json()) == 1

    assert busca.status_code == 200
    assert busca.json()["programa_id"] == programa["id"]


def test_listar_memberships_admin_ve_todos_outros_veem_so_os_proprios() -> None:
    app.state.engine = criar_engine_sqlite_memoria()
    from agenda.domain.membership import Membership
    from agenda.domain.papel import Papel
    from agenda.domain.usuario import Usuario
    from agenda.infrastructure.membership_repository import MembershipRepository
    from agenda.infrastructure.usuario_repository import UsuarioRepository

    engine = app.state.engine
    admin = Usuario(id=uuid.uuid7(), provider="keycloak", subject="admin-1", nome="Admin")
    outro_usuario = Usuario(id=uuid.uuid7(), provider="keycloak", subject="comum-1", nome="Comum")
    UsuarioRepository(engine).salvar(admin)
    UsuarioRepository(engine).salvar(outro_usuario)
    MembershipRepository(engine).salvar(
        Membership(
            id=uuid.uuid7(),
            usuario_id=admin.id,
            organizacao_id=None,
            papeis=[
                Papel(
                    id=uuid.uuid7(),
                    chave="administrador_plataforma",
                    nome="Administrador",
                    permissoes=frozenset({"plataforma.visualizar_metricas_globais"}),
                )
            ],
        )
    )
    MembershipRepository(engine).salvar(
        Membership(
            id=uuid.uuid7(),
            usuario_id=outro_usuario.id,
            organizacao_id=uuid.uuid7(),
            papeis=[Papel(id=uuid.uuid7(), chave="dono", nome="Dono", permissoes=frozenset())],
        )
    )

    identidade_anterior = app.dependency_overrides[identidade_autenticada]

    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak", subject="admin-1", nome="Admin"
    )
    admin_response = client.get("/memberships")

    app.dependency_overrides[identidade_autenticada] = lambda: IdentidadeExterna(
        provider="keycloak", subject="comum-1", nome="Comum"
    )
    comum_response = client.get("/memberships")

    app.dependency_overrides[identidade_autenticada] = identidade_anterior

    assert admin_response.status_code == 200
    assert len(admin_response.json()) == 2
    assert comum_response.status_code == 200
    assert len(comum_response.json()) == 1


def test_buscar_papel_e_tipo_procedimento_por_id() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    papel = client.post(
        "/catalogo/papeis",
        json={"chave": "estagiario", "nome": "Estagiário", "permissoes": []},
    ).json()
    busca_papel = client.get(f"/catalogo/papeis/{papel['id']}")
    assert busca_papel.status_code == 200
    assert busca_papel.json()["chave"] == "estagiario"

    tipo = client.post(
        "/catalogo/tipos-procedimento",
        json={"chave": "depilacao", "nome": "Depilação"},
    ).json()
    busca_tipo = client.get(f"/catalogo/tipos-procedimento/{tipo['id']}")
    assert busca_tipo.status_code == 200
    assert busca_tipo.json()["chave"] == "depilacao"


def test_enviar_media_deduplica_e_permite_buscar() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    conteudo = b"conteudo-unico-para-teste-de-media"
    primeiro = client.post(
        "/medias",
        files={"arquivo": ("foto.png", conteudo, "image/png")},
    )
    assert primeiro.status_code == 200
    payload = primeiro.json()
    assert payload["reaproveitada"] is False
    assert "url" in payload

    segundo = client.post(
        "/medias",
        files={"arquivo": ("foto-copia.png", conteudo, "image/png")},
    )
    assert segundo.status_code == 200
    assert segundo.json()["reaproveitada"] is True
    assert segundo.json()["id"] == payload["id"]

    busca = client.get(f"/medias/{payload['id']}")
    assert busca.status_code == 200
    assert busca.json()["sha256"] == payload["sha256"]


def test_enviar_media_rejeita_arquivo_vazio() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    response = client.post("/medias", files={"arquivo": ("vazio.png", b"", "image/png")})

    assert response.status_code == 422


def test_anexar_media_a_organizacao_e_listar_por_entidade() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    organizacao_id = client.post(
        "/organizacoes",
        json={"nome": "Salão com Fotos", "unipessoal": True},
    ).json()["id"]
    media_id = client.post(
        "/medias",
        files={"arquivo": ("layout.jpg", b"foto-do-layout", "image/jpeg")},
    ).json()["id"]

    anexado = client.post(
        "/anexos",
        json={
            "media_id": media_id,
            "entidade_tipo": "organizacao",
            "entidade_id": organizacao_id,
            "papel": "layout",
        },
    )
    assert anexado.status_code == 200
    anexo_id = anexado.json()["id"]

    listado = client.get(
        "/anexos",
        params={"entidade_tipo": "organizacao", "entidade_id": organizacao_id},
    )
    assert listado.status_code == 200
    assert len(listado.json()) == 1
    assert listado.json()[0]["media"]["id"] == media_id

    remocao_media = client.delete(f"/medias/{media_id}")
    assert remocao_media.status_code == 409

    remocao_anexo = client.delete(f"/anexos/{anexo_id}")
    assert remocao_anexo.status_code == 200

    remocao_media_ok = client.delete(f"/medias/{media_id}")
    assert remocao_media_ok.status_code == 200


def test_anexar_media_rejeita_entidade_tipo_desconhecido() -> None:
    app.state.engine = criar_engine_sqlite_memoria()

    media_id = client.post(
        "/medias",
        files={"arquivo": ("doc.pdf", b"conteudo-pdf", "application/pdf")},
    ).json()["id"]

    resposta = client.post(
        "/anexos",
        json={
            "media_id": media_id,
            "entidade_tipo": "tipo-nao-mapeado",
            "entidade_id": str(uuid.uuid7()),
            "papel": "documento",
        },
    )

    assert resposta.status_code == 422
    assert "autorização" in resposta.json()["detail"] or "autorizacao" in resposta.json()["detail"]


