from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
BASE_URL = os.getenv("KEYCLOAK_BASE_URL", "http://localhost:8080").rstrip("/")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "changeme")
REALM = os.getenv("KEYCLOAK_REALM", "agenda")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove um realm Keycloak de desenvolvimento."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirma a remoção destrutiva do realm",
    )
    args = parser.parse_args()
    if not args.yes:
        parser.error("a remoção exige --yes")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        token_response = client.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD,
            },
        )
        token_response.raise_for_status()
        response = client.delete(
            f"/admin/realms/{REALM}",
            headers={"Authorization": f"Bearer {token_response.json()['access_token']}"},
        )
        if response.status_code == 404:
            print(f"Realm '{REALM}' já não existia.")
        else:
            response.raise_for_status()
            print(f"Realm '{REALM}' removido com sucesso.")


if __name__ == "__main__":
    main()