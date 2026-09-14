# Agenda

Plataforma de agendamento de serviços de beleza, saúde e bem-estar (manicure, esmalte, depilação, nutricionista, etc.), aproximando clientes de profissionais autônomos e estabelecimentos (salões/clínicas).

O modelo de negócio, pesquisa de mercado, escopo do MVP e roadmap estão documentados em [BUSINESS_MODEL.md](BUSINESS_MODEL.md). As decisões técnicas estão registradas em [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

Projeto em implementação inicial do modelo de domínio e design técnico.

## Ambiente de desenvolvimento local

O Postgres e o Keycloak sobem via Docker Compose, com dados persistidos em volumes nomeados (sobrevivem a `docker compose down` sem `-v`).

```powershell
Copy-Item .env.example .env  # ajuste as senhas antes de subir
docker compose up -d
```

- Postgres: `localhost:5432` (usuário/senha/banco definidos no `.env`).
- Keycloak: `http://localhost:8080` (modo `start-dev`, adequado só para desenvolvimento).
- Configuração do realm do Keycloak: ver [keycloak/import/README.md](keycloak/import/README.md).
