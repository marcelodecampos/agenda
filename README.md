# Agenda

Plataforma de agendamento de serviços de beleza, saúde e bem-estar (manicure, esmalte, depilação, nutricionista, etc.), aproximando clientes de profissionais autônomos e estabelecimentos (salões/clínicas).

O modelo de negócio, pesquisa de mercado, escopo do MVP e roadmap estão documentados em [BUSINESS_MODEL.md](BUSINESS_MODEL.md). As decisões técnicas estão registradas em [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

Fundação do backend iniciada, com FastAPI, SQLAlchemy, Alembic, Structlog e ambiente local em Docker Compose.

## Desenvolvimento local

Pré-requisitos: WSL2/Debian, Docker Desktop integrado ao WSL2 e Poetry.

```bash
cp .env.example .env
docker compose up -d
poetry install
poetry run alembic upgrade head
poetry run uvicorn agenda.main:app --reload
```

O endpoint `GET http://localhost:8000/health` deve retornar o status da aplicação. O Keycloak fica disponível em `http://localhost:8080` e o Mailpit em `http://localhost:8025`.
