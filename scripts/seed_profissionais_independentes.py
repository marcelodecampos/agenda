"""Autentica usuários já existentes no Keycloak e cria perfis de profissional
independente via API real (POST /profissionais/independente).

Requer:
- API rodando (poetry run python -m agenda.server);
- os usuários sintéticos já criados por scripts/seed_keycloak_usuarios.py, com a
  senha compartilhada em KEYCLOAK_SEED_USERS_PASSWORD.

Uso:
    poetry run python scripts/seed_profissionais_independentes.py --quantidade 15
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

KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
REALM = os.getenv("KEYCLOAK_REALM", "agenda")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
SEED_PASSWORD = os.getenv("KEYCLOAK_SEED_USERS_PASSWORD")
API_BASE_URL = os.getenv("AGENDA_API_BASE_URL", "http://localhost:8081")

# usuários reais da equipe, declarados em keycloak/config/realm.json: nunca usar como cobaia.
USERNAMES_RESERVADOS = {"59469390415", "49025066291"}

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


def listar_usuarios_sinteticos(client: httpx.Client, token: str, quantidade: int) -> list[str]:
    response = client.get(
        f"/admin/realms/{REALM}/users",
        params={"max": 500},
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    usernames = [
        str(usuario["username"])
        for usuario in response.json()
        if re.fullmatch(r"\d{11}", usuario.get("username", ""))
        and usuario["username"] not in USERNAMES_RESERVADOS
    ]
    if len(usernames) < quantidade:
        raise SystemExit(
            f"Só há {len(usernames)} usuários sintéticos disponíveis no Keycloak; "
            f"rode seed_keycloak_usuarios.py com --quantidade maior."
        )
    return usernames[:quantidade]


def obter_token_usuario(client: httpx.Client, username: str) -> str:
    response = client.post(
        f"/realms/{REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "agenda-web",
            "username": username,
            "password": SEED_PASSWORD,
            "scope": "openid email profile",
        },
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


def criar_profissional_independente(api_client: httpx.Client, token: str) -> bool:
    payload = {
        "nome": f"{FAKE.name()} ({FAKE.job()})",
        "endereco": {
            "logradouro": FAKE.street_name(),
            "numero": str(FAKE.building_number()),
            "cidade": FAKE.city(),
            "estado": FAKE.estado_sigla(),
            "cep": re.sub(r"\D", "", FAKE.postcode()),
        },
    }
    response = api_client.post(
        "/profissionais/independente",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    if response.status_code != 200:
        print(f"Falha ({response.status_code}): {response.text}", file=sys.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria profissionais independentes via API.")
    parser.add_argument("--quantidade", type=int, default=15)
    args = parser.parse_args()

    if not ADMIN_PASSWORD:
        print("Defina KEYCLOAK_ADMIN_PASSWORD no .env.", file=sys.stderr)
        return 2
    if not SEED_PASSWORD:
        print("Defina KEYCLOAK_SEED_USERS_PASSWORD no .env.", file=sys.stderr)
        return 2

    criados = 0
    with httpx.Client(base_url=KEYCLOAK_BASE_URL, timeout=10.0) as kc_client, httpx.Client(
        base_url=API_BASE_URL, timeout=10.0
    ) as api_client:
        admin_token = obter_token_admin(kc_client)
        usernames = listar_usuarios_sinteticos(kc_client, admin_token, args.quantidade)
        for username in usernames:
            token = obter_token_usuario(kc_client, username)
            if criar_profissional_independente(api_client, token):
                criados += 1

    print(f"{criados}/{args.quantidade} profissionais independentes criados.")
    return 0 if criados == args.quantidade else 1


if __name__ == "__main__":
    raise SystemExit(main())
