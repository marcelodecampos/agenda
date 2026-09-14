import uuid

from fastapi.testclient import TestClient
import pytest

from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.main import (
    app,
    exigir_configurar_agenda,
    exigir_configurar_estabelecimento,
    exigir_configurar_fidelidade,
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
        exigir_configurar_estabelecimento,
        exigir_configurar_fidelidade,
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
    assert len(list_response.json()) == 1
    assert get_response.status_code == 200
    assert get_response.json()["nome"] == "Clínica Central"


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
