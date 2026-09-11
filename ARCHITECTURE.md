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
