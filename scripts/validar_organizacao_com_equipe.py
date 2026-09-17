"""Valida end-to-end o novo endpoint POST /organizacoes/com-equipe:
um usuário Keycloak vira dono de um salão com equipe, e então adiciona um
funcionário via POST /memberships (antes impossível, pois ninguém tinha
membership na organização recém-criada).

Uso:
    poetry run python scripts/validar_organizacao_com_equipe.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agenda.infrastructure.db import criar_engine
from agenda.infrastructure.usuario_repository import UsuarioRepository
from agenda.config import settings

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

KEYCLOAK_BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
REALM = os.getenv("KEYCLOAK_REALM", "agenda")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
SEED_PASSWORD = os.getenv("KEYCLOAK_SEED_USERS_PASSWORD")
API_BASE_URL = os.getenv("AGENDA_API_BASE_URL", "http://localhost:8081")
USERNAMES_RESERVADOS = {"59469390415", "49025066291"}


def main() -> int:
    with httpx.Client(base_url=KEYCLOAK_BASE_URL, timeout=10.0) as kc:
        response = kc.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
            },
        )
        response.raise_for_status()
        admin_token = response.json()["access_token"]

        usuarios = kc.get(
            f"/admin/realms/{REALM}/users",
            params={"max": 500},
            headers={"Authorization": f"Bearer {admin_token}"},
        ).json()
        candidatos = [
            u["username"]
            for u in usuarios
            if re.fullmatch(r"\d{11}", u.get("username", ""))
            and u["username"] not in USERNAMES_RESERVADOS
        ]
        if len(candidatos) < 2:
            print("Não há usuários sintéticos suficientes no Keycloak.", file=sys.stderr)
            return 1
        cpf_dono = candidatos[-1]

        token_dono = kc.post(
            f"/realms/{REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "agenda-web",
                "username": cpf_dono,
                "password": SEED_PASSWORD,
                "scope": "openid email profile",
            },
        )
        token_dono.raise_for_status()
        token_dono = token_dono.json()["access_token"]

    engine = criar_engine(settings.database_url)
    funcionario = next(
        u for u in UsuarioRepository(engine).listar() if u.provider == "seed-api"
    )

    with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as api:
        criado = api.post(
            "/organizacoes/com-equipe",
            json={"nome": "Salão de Validação E2E"},
            headers={"Authorization": f"Bearer {token_dono}"},
        )
        criado.raise_for_status()
        organizacao_id = criado.json()["organizacao"]["id"]
        print("Organização criada:", organizacao_id)
        print("Membership do dono:", criado.json()["membership"]["papeis"])

        membership = api.post(
            "/memberships",
            json={
                "usuario_id": str(funcionario.id),
                "organizacao_id": organizacao_id,
                "papeis": ["funcionario"],
            },
            headers={"Authorization": f"Bearer {token_dono}"},
        )
        if membership.status_code != 200:
            print(f"Falha ao adicionar funcionário ({membership.status_code}): {membership.text}")
            return 1
        print("Funcionário adicionado com sucesso:", membership.json()["papeis"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
