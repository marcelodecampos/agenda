# Agent Instructions — Projeto Agenda

Diretrizes carregadas automaticamente em toda sessão de chat neste workspace.

## Documentação de referência

- [BUSINESS_MODEL.md](BUSINESS_MODEL.md) — requisitos de produto e decisões de negócio.
- [ARCHITECTURE.md](ARCHITECTURE.md) — decisões técnicas e limites arquiteturais.
- [COPILOT.md](COPILOT.md) — princípios de desenvolvimento (YAGNI, isolamento arquitetural, checklist de qualidade).
- Ainda não há código de implementação em `src/agenda` (projeto em fase de definição de requisitos).

## Revisão de prontidão no início de cada sessão

No **primeiro prompt de uma nova sessão** neste workspace, antes de iniciar qualquer implementação de código:

1. Releia [BUSINESS_MODEL.md](BUSINESS_MODEL.md) e [ARCHITECTURE.md](ARCHITECTURE.md).
2. Avalie se os requisitos necessários para a tarefa pedida estão realmente elucidados (sem lacunas bloqueantes) ou se ainda dependem de decisão de produto/arquitetura em aberto.
3. Se houver lacuna bloqueante relevante para a tarefa, avise o usuário explicitamente antes de programar — não assuma requisito não documentado (ver princípio "Transparência" do COPILOT.md).
4. Não repita essa revisão completa a cada mensagem da mesma sessão — apenas na primeira interação ou quando o usuário pedir uma reavaliação explícita.

## Convenções já decididas (não reabrir sem justificativa)

- Identificadores internos novos usam **UUIDv7**, não UUIDv4.
- Monólito modular no MVP, regra de dependência `Domínio -> Casos de uso -> Ports -> Adapters -> Infraestrutura`.
- Regras de negócio parametrizáveis viram **dados** (ex: status/transição de agendamento, papéis/permissões), nunca enum fixo em código, quando há risco real de mudança.
- Todas as entidades persistentes Python devem derivar de SQLAlchemy 2.x, usando sua API tipada; não criar entidades persistentes com `dataclass`, `BaseModel` ou ORM alternativo.
- Tabelas do banco usam sempre nomes técnicos em inglês, no singular e em caixa baixa. A hierarquia polimórfica de identidade usa `BaseUser` como base (`base_user`), com `Person` (`person`) e `Company` (`company`) como derivadas; o discriminador fica em `base_user.person_type`.
- `BaseUser` possui `name` e `nickname` como strings de 255 caracteres e `birth_date` como `date` sem horário; `Person` possui `cpf` e `Company` possui `cnpj`, ambos únicos no banco. Não definir obrigatoriedade ou formato desses documentos sem requisito explícito.
- `BaseUser.nickname` representa o nome social quando informado; não criar uma coluna separada `social_name` sem novo requisito.
- Catálogos simples de tipos ou opções usam somente `id` UUIDv7 e `description` textual única; não criar campo `code` separado nem enum fixo em Python.
- Campos de negócio são opcionais quando possível. `BaseUser.name` é obrigatório; em catálogos simples, `id` e `description` são obrigatórios. Campos técnicos permanecem obrigatórios.
