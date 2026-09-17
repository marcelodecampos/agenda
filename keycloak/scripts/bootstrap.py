from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT.parent / ".env")
CONFIG_PATH = Path(
    os.getenv("KEYCLOAK_REALM_CONFIG", ROOT / "config" / "realm.json")
)
BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")


class KeycloakAdmin:
    def __init__(self, client: httpx.Client) -> None:
        self.client = client
        self.token = self._get_admin_token()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self.client.request(
            method,
            path,
            headers={"Authorization": f"Bearer {self.token}"},
            **kwargs,
        )
        if response.is_error:
            raise RuntimeError(
                f"Keycloak API {method} {path} falhou: "
                f"{response.status_code} {response.text}"
            )
        return response

    def _get_admin_token(self) -> str:
        response = self.client.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
            },
        )
        if response.is_error:
            raise RuntimeError(
                "Não foi possível obter token administrativo do Keycloak: "
                f"{response.status_code} {response.text}"
            )
        return str(response.json()["access_token"])

    def realm_exists(self, realm: str) -> bool:
        response = self.client.request(
            "GET",
            f"/admin/realms/{realm}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if response.status_code == 404:
            return False
        if response.is_error:
            raise RuntimeError(
                f"Falha ao consultar realm {realm}: "
                f"{response.status_code} {response.text}"
            )
        return True

    def ensure_realm(self, config: dict[str, Any]) -> None:
        realm = str(config["realm"])
        realm_payload = {
            key: value
            for key, value in config.items()
            if key not in {"clients", "roles", "users"}
        }
        if not self.realm_exists(realm):
            self._request("POST", "/admin/realms", json=realm_payload)
            return
        self._request("PUT", f"/admin/realms/{realm}", json=realm_payload)

    def ensure_client(self, realm: str, desired: dict[str, Any]) -> None:
        client_id = str(desired["clientId"])
        response = self._request(
            "GET",
            f"/admin/realms/{realm}/clients",
            params={"clientId": client_id},
        )
        clients = response.json()
        if not clients:
            self._request(
                "POST",
                f"/admin/realms/{realm}/clients",
                json=desired,
            )
            return
        internal_id = clients[0]["id"]
        self._request(
            "PUT",
            f"/admin/realms/{realm}/clients/{internal_id}",
            json=desired,
        )

    def ensure_role(self, realm: str, desired: dict[str, Any]) -> None:
        role_name = str(desired["name"])
        response = self.client.request(
            "GET",
            f"/admin/realms/{realm}/roles/{role_name}",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        if response.status_code == 404:
            self._request("POST", f"/admin/realms/{realm}/roles", json=desired)
            return
        if response.is_error:
            raise RuntimeError(
                f"Falha ao consultar role {role_name}: "
                f"{response.status_code} {response.text}"
            )
        self._request(
            "PUT",
            f"/admin/realms/{realm}/roles/{role_name}",
            json=desired,
        )

    def ensure_user_profile(self, realm: str) -> None:
        response = self._request(
            "GET",
            f"/admin/realms/{realm}/users/profile",
        )
        profile = response.json()
        attributes = profile.get("attributes", [])
        declared_names = {attribute.get("name") for attribute in attributes}
        for name, display_name in (("cpf", "CPF"), ("phone_number", "Telefone")):
            if name not in declared_names:
                attributes.append(
                    {
                        "name": name,
                        "displayName": display_name,
                        "permissions": {
                            "view": ["admin", "user"],
                            "edit": ["admin", "user"],
                        },
                    }
                )
        profile["attributes"] = attributes
        self._request("PUT", f"/admin/realms/{realm}/users/profile", json=profile)

    def ensure_user(self, realm: str, desired: dict[str, Any]) -> None:
        username = str(desired["username"])
        previous_username = desired.get("previousUsername")
        password_env = str(desired["passwordEnv"])
        password = os.getenv(password_env)
        if not password:
            raise RuntimeError(
                f"A variável {password_env} é obrigatória para o usuário {username}."
            )

        response = self._request(
            "GET",
            f"/admin/realms/{realm}/users",
            params={"username": username, "exact": "true"},
        )
        users = response.json()
        if not users and previous_username:
            response = self._request(
                "GET",
                f"/admin/realms/{realm}/users",
                params={"username": str(previous_username), "exact": "true"},
            )
            users = response.json()
            if users:
                self._request(
                    "DELETE",
                    f"/admin/realms/{realm}/users/{users[0]['id']}",
                )
                users = []
        payload = {
            key: value
            for key, value in desired.items()
            if key not in {"passwordEnv", "roles", "previousUsername"}
        }
        payload["credentials"] = [
            {"type": "password", "value": password, "temporary": False}
        ]
        payload.setdefault("emailVerified", True)

        if not users:
            self._request("POST", f"/admin/realms/{realm}/users", json=payload)
            response = self._request(
                "GET",
                f"/admin/realms/{realm}/users",
                params={"username": username, "exact": "true"},
            )
            users = response.json()
        else:
            self._request(
                "PUT",
                f"/admin/realms/{realm}/users/{users[0]['id']}",
                json=payload,
            )

        user_id = users[0]["id"]
        for role_name in desired.get("roles", []):
            role_response = self._request(
                "GET",
                f"/admin/realms/{realm}/roles/{role_name}",
            )
            self._request(
                "POST",
                f"/admin/realms/{realm}/users/{user_id}/role-mappings/realm",
                json=[role_response.json()],
            )


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    realm = str(config["realm"])
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        admin = KeycloakAdmin(client)
        admin.ensure_realm(config)
        admin.ensure_user_profile(realm)
        for desired_client in config.get("clients", []):
            admin.ensure_client(realm, desired_client)
        for desired_role in config.get("roles", []):
            admin.ensure_role(realm, desired_role)
        for desired_user in config.get("users", []):
            admin.ensure_user(realm, desired_user)
    print(f"Realm '{realm}' configurado com sucesso em {BASE_URL}.")


if __name__ == "__main__":
    main()