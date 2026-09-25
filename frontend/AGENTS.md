<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Biblioteca de UI

- Usar MUI como biblioteca única de componentes visuais.
- Usar Material Icons para ícones.
- Não introduzir Radix, shadcn/ui, Tailwind ou estilos paralelos em novas telas.
- Elementos em `Elementos de layout` servem somente para validar usabilidade; não devem persistir dados nem chamar o backend.

## Automação de testes

- Todo componente novo deve possuir um `id` estável e semântico para permitir automação de testes.
- O `id` não deve depender de texto traduzível, índice visual ou posição no DOM.
- Elementos repetidos devem receber identificadores determinísticos derivados da identidade do registro.

## Tipografia

- Usar a tipografia padrão do MUI; não impor uma família de fonte global.

## Isolamento de contexto

- Estado de uma tela ou feature não pode ser compartilhado implicitamente com outra.
- Busca, filtros, paginação, seleção, edição, formulários, erros e resultados devem ser locais à tela ou explicitamente isolados por chave de contexto.
- Compartilhamento só é permitido por contrato explícito e documentado, como autenticação, autorização ou uma operação que exija continuidade entre telas.
- Ao trocar de contexto, o estado anterior deve ser descartado ou invalidado antes de aceitar novos resultados assíncronos.

## Campos com máscara

- Campos com máscara fixa devem usar largura visual de `quantidade máxima de caracteres × 13px`.
- CPF: 11 caracteres, largura de referência de 143px.
- CNPJ: 14 caracteres, largura de referência de 182px.

## Tipografia de inputs

- Inputs, selects e textareas administrativos usam `0.75rem` (`12px`) e altura padrão de `30px`.
- Labels administrativos usam `0.75rem`.
- Listas administrativas usam fonte de `0.75rem` (`12px`) com espaçamento vertical compacto, sem reduzir a área de interação de checkboxes e ações.
