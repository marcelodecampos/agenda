# Decisoes Arquiteturais

Registro das decisoes tecnicas que orientam a implementacao da plataforma Agenda. Este documento registra limites e contratos arquiteturais; requisitos de produto e regras de negocio permanecem no [BUSINESS_MODEL.md](BUSINESS_MODEL.md).

## Status

- **Data da primeira versao:** 2026-09-11
- **Estado:** em definicao tecnica
- **Escopo:** MVP

## Decisoes confirmadas

### 1. Monolito modular no MVP

O MVP sera implementado como um monolito modular. Nao serao usados microservicos neste momento.

A ausencia de microservicos nao permite acoplamento direto entre modulos. Cada modulo deve ter responsabilidade clara e fronteiras explicitas. Uma futura extracao para outro processo ou servico somente sera feita quando houver justificativa comprovada de desempenho, custo, memoria, escalabilidade ou operacao.

### 2. Isolamento de dependencias e modulos

O dominio e os casos de uso nao devem depender diretamente de frameworks, brokers, provedores externos, ORMs ou detalhes de infraestrutura.

A regra de dependencia e:

```text
Dominio -> Casos de uso -> Ports -> Adapters -> Infraestrutura
```

Dependencias com probabilidade relevante de mudanca devem ficar atras de ports (contratos) e adapters (implementacoes). Os ports representam capacidades do negocio, e nao APIs de fornecedores.

Exemplos de fronteiras:

- fila de tarefas e notificacoes;
- e-mail, WhatsApp e SMS;
- geocodificacao e calculo de distancia;
- identidade e autenticacao;
- persistencia;
- servicos externos.

A troca de uma implementacao deve ficar concentrada no adapter, na configuracao e nos testes de integracao/contrato. A substituicao nao e considerada custo zero: semanticas como retry, ordenacao, idempotencia, timeout e confirmacao precisam fazer parte do contrato quando forem relevantes.

### 3. Identidade e autenticacao

O **Keycloak** sera usado no desenvolvimento e no MVP como provedor de identidade. A integracao sera feita por OIDC/OAuth 2.0, e a Agenda nao armazenara senhas.

A aplicacao deve permanecer independente do Keycloak por meio de uma porta de identidade. Uma futura migracao para outro provedor deve exigir a troca ou adicao de um adapter, sem alterar o dominio.

A identidade externa sera separada do modelo de negocio:

```text
Identidade externa -> Usuario interno -> Membership -> Organizacao e papeis
```

O e-mail nao sera usado como identificador principal. A aplicacao usara um identificador interno proprio e armazenara o par `provider + subject` como referencia externa.

### 3.1 Identificadores de login e unicidade do usuario

Para o fluxo atual do produto, o CPF sera usado como `username` no Keycloak para novos usuarios. Isso resolve a colisao de nomes: duas pessoas podem se chamar Marcelo, mas nao podem compartilhar o mesmo CPF valido.

Essa decisao nao transforma CPF em identificador interno. O identificador interno continua sendo um UUIDv7, e a referencia externa continua sendo `provider + subject` do Keycloak.

O modelo `Usuario` da Agenda armazena, quando aplicavel, `cpf`, `email` e `telefone`. Cada um possui unicidade propria no banco quando informado. E-mail e telefone sao meios de contato e recuperacao, nao substituem `provider + subject`.

Usuarios legados de desenvolvimento que ainda usam usernames textuais, como `marcelo` e `leila`, foram migrados para usernames baseados em CPF. Como o Keycloak nao permite alterar username, a migracao pode recriar a conta e alterar o `sub`; a Agenda deve executar reconciliacao controlada antes de associar a nova identidade ao usuario interno existente.

O CPF e dado pessoal e a regra exige finalidade, controle de acesso, criptografia, retencao minima, auditoria e fluxo de correcao/exclusao conforme a LGPD.

Entidades e contratos afetados por essa decisao:

- `Usuario`: passa a armazenar CPF, e-mail e telefone opcionais;
- `UsuarioModel`/tabela `usuarios`: novas colunas com unicidade individual;
- `IdentidadeExterna` e adapter Keycloak: propagam `preferred_username`, `cpf`, `email` e `phone_number`;
- `Cliente`: ja possuia CPF, e-mail e telefone; continua representando o perfil de cliente, enquanto `Usuario` representa a identidade autenticada;
- `Membership`, `Organizacao`, `Servico` e `Agendamento`: nao precisam de CPF; continuam referenciando `Usuario` por UUIDv7 quando necessário.

### 4. Identificadores internos

Novos identificadores internos usarao **UUIDv7**, preferencialmente no tipo nativo `uuid` do PostgreSQL.

UUIDv7 foi escolhido por manter unicidade distribuida e oferecer ordenacao aproximada por tempo, reduzindo a aleatoriedade de insercao em indices em comparacao com UUIDv4. Ele nao elimina toda fragmentacao de indice e nao deve ser tratado como mecanismo de seguranca ou autorizacao.

A geracao deve usar uma implementacao confiavel e, quando necessario, comportamento monotonicamente ordenavel para varios IDs criados no mesmo milissegundo.

### 5. Evolucao para outras linguagens

Modulos que futuramente precisem ser implementados em Go ou Rust devem possuir fronteiras baseadas em contratos de rede ou eventos versionados. Nao sera permitido compartilhar classes Python, modelos ORM ou estado interno entre implementacoes.

A substituicao deve preservar, conforme aplicavel:

- contrato de entrada e saida;
- validacoes relevantes;
- idempotencia;
- erros observaveis;
- timeouts;
- telemetria;
- compatibilidade de dados.

### 6. Ambiente de desenvolvimento local

O desenvolvimento local usara WSL2/Debian como ambiente principal, com Docker Desktop integrado ao WSL2.

O Docker Compose sera usado para executar as dependencias externas do ambiente local:

- PostgreSQL;
- Keycloak;
- Mailpit para testes locais de e-mail.

A aplicacao Python sera executada diretamente no WSL por meio do Poetry, facilitando o ciclo de desenvolvimento, o debug e o reload. O frontend tambem sera executado localmente conforme o framework que vier a ser escolhido.

O PostgreSQL local usara bancos separados para a aplicacao e para o Keycloak, evitando misturar seus dados mesmo compartilhando o mesmo servidor local.

Redis, Celery, RabbitMQ ou outra infraestrutura de processamento assincrono somente serao adicionados quando esse mecanismo for definido e houver necessidade comprovada. Ferramentas administrativas adicionais, como uma interface para PostgreSQL, sao opcionais e nao fazem parte do ambiente minimo.

O Docker Compose sera utilizado para desenvolvimento local e para apoiar testes de integracao/CI. Ele nao define a estrategia de producao: nessa etapa serao avaliados banco gerenciado, hospedagem da aplicacao e forma de operacao do Keycloak.

### 7. Framework HTTP do backend

O backend HTTP do MVP usara FastAPI, com Uvicorn como servidor ASGI. A camada HTTP permanecera na borda da aplicacao e nao sera acessada diretamente pelo dominio.

## Regras de implementacao

- Nao importar bibliotecas de infraestrutura no dominio.
- Nao expor tipos de ORM nos ports ou contratos publicos.
- Nao usar classes internas de um modulo como API de outro modulo.
- Preferir contratos pequenos e orientados a capacidades do negocio.
- Cobrir o dominio com testes unitarios.
- Cobrir cada adapter com testes de integracao.
- Usar testes de contrato quando houver mais de uma implementacao para o mesmo port.
- Manter a composicao concreta das dependencias na borda da aplicacao.
- Criar uma abstracao somente quando houver uma fronteira real de negocio ou uma dependencia com risco concreto de substituicao.

## Ambiente de desenvolvimento local

Postgres e Keycloak rodam via `docker-compose.yml` na raiz do repositorio, com volumes nomeados persistentes (dados sobrevivem a reinicios do container). Esta e uma decisao de **ambiente de desenvolvimento**, nao define a escolha final de hospedagem/producao.

O realm do Keycloak e importado automaticamente na subida (`start-dev --import-realm`) a partir de `keycloak/import/`; o fluxo de configuracao e export do realm esta documentado em [keycloak/import/README.md](keycloak/import/README.md).

## Decisoes ainda em avaliacao

- framework definitivo do frontend;
- escolha final de hospedagem;
- PostgreSQL/PostGIS como banco de producao;
- mecanismo de filas para tarefas assincronas;
- provedor de geocodificacao e distancia;
- provedor de notificacoes.

Esses itens nao devem ser tratados como decisoes confirmadas ate que seus trade-offs sejam registrados aqui.

## Criterios para alterar uma decisao

Uma decisao pode ser revisada quando houver evidencia de:

- custo operacional ou financeiro inadequado;
- limitacao de desempenho ou memoria;
- risco de seguranca ou conformidade;
- dificuldade comprovada de evolucao;
- necessidade operacional do produto;
- nova informacao que invalide a premissa original.

Toda revisao deve registrar a motivacao, as alternativas consideradas, os impactos da mudanca e o plano de migracao.
