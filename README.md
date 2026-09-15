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
poetry run python -m agenda.server
```

- Postgres: `localhost:5432` (usuário/senha/banco definidos no `.env`).
- Keycloak: `http://localhost:8080` (modo `start-dev`, adequado só para desenvolvimento).
- Mailpit: `http://localhost:8025` para visualizar e-mails locais.
- API local: `http://localhost:8081`.
- Descoberta pública: `GET /descoberta?categoria=unhas` ou com `endereco` e `raio_km`.
- Processamento de notificações vencidas: `POST /notificacoes/processar-vencidas`, com `NOTIFICACAO_WEBHOOK_URL` configurada.
- Worker de notificações em execução única: `poetry run python -m agenda.worker`.
- API na rede: `http://<IP-da-maquina>:8081`.
- Health check: `http://localhost:8081/health`.
- Configuração do realm do Keycloak: ver [keycloak/import/README.md](keycloak/import/README.md).

## Identidade e unicidade

Para novos usuários, o CPF normalizado com 11 dígitos será o `username` único no Keycloak. O nome pode se repetir. E-mail e telefone são contatos únicos opcionais; o identificador técnico da Agenda continua sendo o UUIDv7 interno vinculado ao par `provider + subject` do Keycloak.

CPF, e-mail, telefone e endereço são dados pessoais. Não coloque valores reais em arquivos versionados; use variáveis de ambiente e siga a política de LGPD registrada em [ARCHITECTURE.md](ARCHITECTURE.md).

## Token local do Keycloak

Existe uma rotina versionada em `local-tools/get_keycloak_token.py`. A senha não fica no código e é solicitada sem exibi-la:

```powershell
poetry run python local-tools/get_keycloak_token.py --username 59469390415
```

O access token é impresso na saída padrão. Para usar outro realm ou servidor, defina `KEYCLOAK_BASE_URL` e `KEYCLOAK_REALM` no ambiente.
