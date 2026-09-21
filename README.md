# Agenda

Plataforma de agendamento de serviços de beleza, saúde e bem-estar (manicure, esmalte, depilação, nutricionista, etc.), aproximando clientes de profissionais autônomos e estabelecimentos (salões/clínicas).

O modelo de negócio, pesquisa de mercado, escopo do MVP e roadmap estão documentados em [BUSINESS_MODEL.md](BUSINESS_MODEL.md). As decisões técnicas estão registradas em [ARCHITECTURE.md](ARCHITECTURE.md).

## Status

Fundação do backend iniciada, com FastAPI, SQLAlchemy, Alembic, Structlog e ambiente local em Docker Compose.

## Ambiente de desenvolvimento local

O Postgres e o Keycloak sobem via Docker Compose, com dados persistidos em volumes nomeados (sobrevivem a `docker compose down` sem `-v`).

```powershell
Copy-Item .env.example .env  # ajuste as senhas antes de subir
.\scripts\wslc-up.ps1
poetry install
poetry run alembic upgrade head
poetry run python -m agenda.server
```

### Ambiente com WSLC

O ambiente local pode ser executado sem Docker ou Podman usando o WSLC:

```powershell
.\scripts\wslc-up.ps1
.\scripts\wslc-status.ps1
.\scripts\wslc-down.ps1
```

`wslc-down.ps1` remove os containers, mas preserva os volumes `agenda_postgres_data`
e `agenda_keycloak_data`. Para recriar os dados, remova esses volumes manualmente
com `wslc volume remove`.

- Postgres: `localhost:5432` (usuário/senha/banco definidos no `.env`).
- Keycloak: `http://localhost:8080` (modo `start-dev`, adequado só para desenvolvimento).
- Mailpit: `http://localhost:8025` para visualizar e-mails locais.
- API local: `http://localhost:8081`.
- Descoberta pública: `GET /descoberta?categoria=unhas` ou com `endereco` e `raio_km`.
- Catálogo de serviços: nomes e categorias são entidades separadas; um nome pode pertencer a várias categorias.
- Processamento de notificações vencidas: `POST /notificacoes/processar-vencidas`, com `NOTIFICACAO_WEBHOOK_URL` configurada.
- Worker de notificações em execução única: `poetry run python -m agenda.worker`.
- API na rede: `http://<IP-da-maquina>:8081`.
- Health check: `http://localhost:8081/health`.
- Configuração do realm do Keycloak: ver [keycloak/import/README.md](keycloak/import/README.md).

### Dados territoriais do IBGE

O procedimento completo está em [docs/IMPORTACAO_DADOS_IBGE.md](docs/IMPORTACAO_DADOS_IBGE.md).

As migrações criam os catálogos `unidades_federacao`, `municipios` e
`localidades`. Os municípios são importados da [API de Localidades do
IBGE](https://servicodados.ibge.gov.br/api/docs/localidades):

```powershell
poetry run python scripts/importar_localidades_ibge.py --municipios
```

As localidades selecionadas de 2010 podem ser importadas do arquivo
`BR_Localidades_2010_v1.mdb`, disponível no [cadastro de localidades do
IBGE](https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/cadastro_de_localidades_selecionadas_2010/):

```powershell
poetry run python scripts/importar_localidades_ibge.py --localidades-mdb path/to/BR_Localidades_2010_v1.mdb
```

Também é possível usar o KML oficial, sem instalar GDAL/OGR:

```powershell
poetry run python scripts/importar_localidades_ibge.py --localidades-kml path/to/BR_Localidades_2010_v1.kml
```

O comando que usa MDB requer GDAL/OGR com suporte ao formato GeoMedia/Access
(`ogrinfo` e `ogr2ogr`). As coordenadas são armazenadas em graus decimais,
conforme o dicionário do IBGE, e o ano da fonte fica registrado como `2010`.

### Logs detalhados em desenvolvimento

Para ver o SQL e os detalhes de cada requisição HTTP, execute a API com:

```powershell
$env:LOG_LEVEL = "DEBUG"
poetry run python -m agenda.server
```

O log de requisição inclui método, caminho, query string, headers não sensíveis,
status HTTP e duração. `Authorization`, `Cookie`, `Set-Cookie` e `X-Api-Key`
são mascarados. O SQL exibido pelo SQLAlchemy inclui a instrução e os parâmetros.
O corpo da requisição não é registrado por padrão para evitar exposição de dados
pessoais, tokens e arquivos enviados.

## Identidade e unicidade

Para novos usuários, o CPF normalizado com 11 dígitos será o `username` único no Keycloak. O nome pode se repetir. E-mail e telefone são contatos únicos opcionais; o identificador técnico da Agenda continua sendo o UUIDv7 interno vinculado ao par `provider + subject` do Keycloak.

CPF, e-mail, telefone e endereço são dados pessoais. Não coloque valores reais em arquivos versionados; use variáveis de ambiente e siga a política de LGPD registrada em [ARCHITECTURE.md](ARCHITECTURE.md).

## Token local do Keycloak

Existe uma rotina versionada em `local-tools/get_keycloak_token.py`. A senha não fica no código e é solicitada sem exibi-la:

```powershell
poetry run python local-tools/get_keycloak_token.py --username 59469390415
```

O access token é impresso na saída padrão. Para usar outro realm ou servidor, defina `KEYCLOAK_BASE_URL` e `KEYCLOAK_REALM` no ambiente.

## Administradores da plataforma

O role `platform_admin` do Keycloak autentica os administradores, mas as permissões de negócio são mantidas pela Agenda. Depois que cada administrador fizer login pelo menos uma vez, provisione o papel interno com:

```powershell
poetry run python scripts/seed_platform_admins.py
```

A rotina é idempotente e associa os usuários declarados no realm ao papel `administrador_plataforma`. Sem esse membership interno, endpoints administrativos retornam `403 Forbidden`.
