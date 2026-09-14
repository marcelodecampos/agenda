# Agenda

Plataforma de agendamento de serviços de beleza, saúde e bem-estar (manicure, esmalte, depilação, nutricionista, etc.), aproximando clientes de profissionais autônomos e estabelecimentos (salões/clínicas).

O modelo de negócio, pesquisa de mercado, escopo do MVP e roadmap estão documentados em [BUSINESS_MODEL.md](BUSINESS_MODEL.md). As decisões técnicas estão registradas em [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

Fundação do backend iniciada, com FastAPI, SQLAlchemy, Alembic, Structlog e ambiente local em Docker Compose.

## Ambiente de desenvolvimento local

O Postgres e o Keycloak sobem via Docker Compose, com dados persistidos em volumes nomeados (sobrevivem a `docker compose down` sem `-v`).

```powershell
Copy-Item .env.example .env  # ajuste as senhas antes de subir
docker compose up -d
poetry install
poetry run alembic upgrade head
poetry run uvicorn agenda.main:app --reload
```

- Postgres: `localhost:5432` (usuário/senha/banco definidos no `.env`).
- Keycloak: `http://localhost:8080` (modo `start-dev`, adequado só para desenvolvimento).
- Mailpit: `http://localhost:8025` para visualizar e-mails locais.
- Health check: `http://localhost:8000/health`.
- Configuração do realm do Keycloak: ver [keycloak/import/README.md](keycloak/import/README.md).
