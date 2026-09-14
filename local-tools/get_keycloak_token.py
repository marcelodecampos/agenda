from __future__ import annotations

import argparse
import getpass
import os
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Obtém um access token local do realm Agenda."
    )
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--password-env",
        default="KEYCLOAK_USER_PASSWORD",
        help="Variável opcional que contém a senha; sem ela, solicita a senha ocultamente.",
    )
    args = parser.parse_args()

    base_url = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
    realm = os.getenv("KEYCLOAK_REALM", "agenda")
    password = os.getenv(args.password_env) or getpass.getpass("Senha Keycloak: ")
    if not password:
        print("Senha não informada.", file=sys.stderr)
        return 2

    try:
        response = httpx.post(
            f"{base_url}/realms/{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "agenda-web",
                "username": args.username,
                "password": password,
                "scope": "openid email profile",
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print(
            f"Keycloak rejeitou a autenticação: HTTP {exc.response.status_code}",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError as exc:
        print(f"Não foi possível acessar o Keycloak: {exc}", file=sys.stderr)
        return 1

    print(response.json()["access_token"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
