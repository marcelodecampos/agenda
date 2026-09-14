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
