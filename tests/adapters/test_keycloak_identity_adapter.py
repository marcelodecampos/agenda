import httpx
import pytest

from agenda.adapters.keycloak_identity_adapter import (
    IdentidadeNaoAutenticadaError,
    KeycloakIdentityAdapter,
)
from agenda.ports import IdentidadeExterna


def test_obter_identidade_do_keycloak() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer token-123"
        assert request.url == "https://auth.example.com/realms/agenda/protocol/openid-connect/userinfo"
        return httpx.Response(
            200,
            json={"sub": "abc123", "name": "Maria da Silva"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = KeycloakIdentityAdapter(
        base_url="https://auth.example.com",
        realm="agenda",
        client=client,
    )

    identidade = adapter.obter_identidade("token-123")

    assert identidade == IdentidadeExterna(
        provider="keycloak",
        subject="abc123",
        nome="Maria da Silva",
    )


def test_rejeita_token_recusado_pelo_keycloak() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(401))
    )
    adapter = KeycloakIdentityAdapter(
        base_url="https://auth.example.com",
        realm="agenda",
        client=client,
    )

    with pytest.raises(IdentidadeNaoAutenticadaError, match="invalido"):
        adapter.obter_identidade("token-expirado")


def test_rejeita_resposta_sem_subject() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"name": "Maria"})
        )
    )
    adapter = KeycloakIdentityAdapter(
        base_url="https://auth.example.com",
        realm="agenda",
        client=client,
    )

    with pytest.raises(IdentidadeNaoAutenticadaError, match="subject"):
        adapter.obter_identidade("token-sem-subject")
