"""Cria usuários sintéticos REAIS no Keycloak (realm 'agenda') via Admin REST API.

Diferente de scripts/seed_usuarios_via_api.py, estes usuários existem de fato no
Keycloak e conseguem autenticar (todos com a mesma senha de teste, definida em
KEYCLOAK_SEED_USERS_PASSWORD). Não ficam declarados em keycloak/config/realm.json
porque não são contas reais da equipe, apenas massa de teste.

Requer no .env (ou variáveis de ambiente):
- KEYCLOAK_ADMIN / KEYCLOAK_ADMIN_PASSWORD (credenciais administrativas já usadas
  pelo bootstrap.py);
- KEYCLOAK_SEED_USERS_PASSWORD (senha compartilhada dos usuários de teste, à sua escolha).

Uso:
    poetry run python scripts/seed_keycloak_usuarios.py --quantidade 50
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from faker import Faker

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
REALM = os.getenv("KEYCLOAK_REALM", "agenda")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
SEED_PASSWORD = os.getenv("KEYCLOAK_SEED_USERS_PASSWORD")

FAKE = Faker("pt_BR")


def obter_token_admin(client: httpx.Client) -> str:
    response = client.post(
        "/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD,
        },
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


def usuario_existe(client: httpx.Client, token: str, username: str) -> bool:
    response = client.get(
        f"/admin/realms/{REALM}/users",
        params={"username": username, "exact": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return bool(response.json())


def criar_usuario(client: httpx.Client, token: str) -> bool:
    cpf = re.sub(r"\D", "", FAKE.unique.cpf())
    if usuario_existe(client, token, cpf):
        return False
    payload = {
        "username": cpf,
        "firstName": FAKE.first_name(),
        "lastName": FAKE.last_name(),
        "email": FAKE.unique.email(),
        "emailVerified": True,
        "enabled": True,
        "attributes": {
            "cpf": [cpf],
            "phone_number": [re.sub(r"\D", "", FAKE.unique.phone_number())],
        },
        "credentials": [
            {"type": "password", "value": SEED_PASSWORD, "temporary": False}
        ],
    }
    response = client.post(
        f"/admin/realms/{REALM}/users",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code == 409:
        return False
    response.raise_for_status()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria usuários sintéticos no Keycloak.")
    parser.add_argument("--quantidade", type=int, default=50)
    args = parser.parse_args()

    if not ADMIN_PASSWORD:
        print("Defina KEYCLOAK_ADMIN_PASSWORD no .env.", file=sys.stderr)
        return 2
    if not SEED_PASSWORD:
        print(
            "Defina KEYCLOAK_SEED_USERS_PASSWORD no .env "
            "(senha compartilhada dos usuários de teste).",
            file=sys.stderr,
        )
        return 2

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        token = obter_token_admin(client)
        criados = 0
        for _ in range(args.quantidade):
            if criar_usuario(client, token):
                criados += 1
        print(f"{criados}/{args.quantidade} usuários criados no Keycloak (realm '{REALM}').")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
