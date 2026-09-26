---
description: "Marca uma tabela para sincronização com o OpenSearch (trigger + carga inicial em search_event)."
argument-hint: "nome da tabela, ex: municipality"
agent: agent
---

Marque a tabela `${input:tabela}` para sincronização com o OpenSearch.

Siga exatamente os requisitos da seção 9.1 de [ARCHITECTURE.md](../../ARCHITECTURE.md), que é a fonte única dessas regras:

1. Confirme que a tabela existe e tem chave primária `id` do tipo `uuid`; se não tiver, pare e avise.
2. Verifique se já não existe migração marcando essa tabela.
3. Crie uma nova migração Alembic encadeada na última revisão (revision ID com no máximo 32 caracteres).
4. Crie e registre o indexador da tabela, conforme a seção 9.1. Se os campos do documento não estiverem definidos, pergunte antes de criá-lo.
5. Aplique com `poetry run alembic upgrade head` e valide com `poetry run ruff check src migrations`.
6. Atualize a lista "Tabelas sincronizadas" na seção 9.1.
