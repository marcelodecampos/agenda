from __future__ import annotations

from typing import Protocol

import httpx
import structlog

from agenda.ports import IdentidadeExterna, IdentidadePort


logger = structlog.get_logger(__name__)


class IdentidadeNaoAutenticadaError(ValueError):
    """Raised when Keycloak rejects or returns an unusable access token."""


class ProvedorIdentidadeIndisponivelError(RuntimeError):
    """Raised when Keycloak cannot be reached."""


class KeycloakIdentityAdapter(IdentidadePort):
    def __init__(
        self,
        *,
        base_url: str,
        realm: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client = client or httpx.Client()

    @property
    def userinfo_url(self) -> str:
        return (
            f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/userinfo"
        )

    def obter_identidade(self, token: str) -> IdentidadeExterna:
        if not token.strip():
            logger.warning("keycloak_token_missing")
            raise IdentidadeNaoAutenticadaError("token de acesso ausente")

        logger.info("keycloak_userinfo_request_started", realm=self.realm)
        try:
            response = self.client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
        except httpx.RequestError as exc:
            logger.error(
                "keycloak_userinfo_request_failed",
                realm=self.realm,
                error_type=type(exc).__name__,
            )
            raise ProvedorIdentidadeIndisponivelError(
                "provedor de identidade indisponivel"
            ) from exc

        logger.info(
            "keycloak_userinfo_response_received",
            realm=self.realm,
            status_code=response.status_code,
        )
        if response.status_code in (401, 403):
            logger.warning(
                "keycloak_token_rejected",
                realm=self.realm,
                status_code=response.status_code,
            )
            raise IdentidadeNaoAutenticadaError("token de acesso invalido")
        response.raise_for_status()

        payload = response.json()
        subject = payload.get("sub")
        if not subject:
            logger.error("keycloak_userinfo_subject_missing", realm=self.realm)
            raise IdentidadeNaoAutenticadaError(
                "resposta do provedor sem subject"
            )

        logger.info("keycloak_identity_resolved", realm=self.realm)

        return IdentidadeExterna(
            provider="keycloak",
            subject=str(subject),
            nome=str(payload.get("name") or payload.get("preferred_username") or ""),
            username=(
                str(payload["preferred_username"])
                if payload.get("preferred_username")
                else None
            ),
            cpf=(
                str(payload["cpf"])
                if payload.get("cpf")
                else None
            ),
            email=(str(payload["email"]) if payload.get("email") else None),
            telefone=(
                str(payload["phone_number"])
                if payload.get("phone_number")
                else None
            ),
        )
