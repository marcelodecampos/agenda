"""Cria usuários de teste chamando a API real (POST /usuarios), em vez de gravar direto no banco.

Diferente de scripts/seed_dev_data.py, este script exercita a camada HTTP completa:
autenticação, validação Pydantic, tratamento de conflito (409) e serialização.

Requer:
- a API rodando (`poetry run python -m agenda.server`);
- um token Bearer válido do Keycloak, via variável de ambiente AGENDA_API_TOKEN
  (obtenha com `poetry run python local-tools/get_keycloak_token.py --username <cpf>`).

Uso:
    $env:AGENDA_API_TOKEN = "<token>"
    poetry run python scripts/seed_usuarios_via_api.py --quantidade 50
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import uuid

import httpx
from faker import Faker

FAKE = Faker("pt_BR")


def _cpf_digits() -> str:
    return re.sub(r"\D", "", FAKE.cpf())


def criar_usuario(client: httpx.Client, *, max_tentativas: int = 5) -> dict | None:
    for _ in range(max_tentativas):
        payload = {
            "provider": "seed-api",
            "subject": f"seed-api-{uuid.uuid4()}",
            "nome": FAKE.name(),
            "cpf": _cpf_digits(),
            "email": FAKE.unique.email(),
            "telefone": re.sub(r"\D", "", FAKE.phone_number()),
        }
        response = client.post("/usuarios", json=payload)
        if response.status_code == 200:
            return response.json()
        if response.status_code == 409:
            continue
        print(f"Falha inesperada ({response.status_code}): {response.text}", file=sys.stderr)
        return None
    print("Não foi possível gerar um usuário sem conflito após várias tentativas.", file=sys.stderr)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria usuários de teste via API.")
    parser.add_argument("--quantidade", type=int, default=50)
    parser.add_argument("--base-url", default=os.getenv("AGENDA_API_BASE_URL", "http://localhost:8081"))
    args = parser.parse_args()

    token = os.getenv("AGENDA_API_TOKEN")
    if not token:
        print("Defina AGENDA_API_TOKEN com um token Bearer válido do Keycloak.", file=sys.stderr)
        return 2

    criados = 0
    with httpx.Client(
        base_url=args.base_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10.0,
    ) as client:
        for _ in range(args.quantidade):
            usuario = criar_usuario(client)
            if usuario is not None:
                criados += 1

    print(f"{criados}/{args.quantidade} usuários criados com sucesso.")
    return 0 if criados == args.quantidade else 1


if __name__ == "__main__":
    raise SystemExit(main())
