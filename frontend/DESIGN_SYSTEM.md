# Diretrizes visuais do frontend

## Stack visual

- MUI é a biblioteca única de componentes visuais do frontend.
- Emotion é o mecanismo de estilos do MUI.
- Material Icons é a biblioteca única de ícones.
- Não usar Radix, shadcn/ui, Tailwind ou componentes HTML estilizados diretamente em novas telas.
- Componentes em `Elementos de layout` são protótipos de usabilidade: usam estado local, não chamam API e não persistem dados.

Registro do layout e dos padrões de interação definidos para o MVP da Agenda.

## Direção visual

- A tipografia padrão da interface é a tipografia padrão do MUI; não impor uma família de fonte global.
- Interface administrativa operacional, compacta e orientada a tarefas.
- Paleta predominantemente azul, com sensação de calma e confiança.
- Menu lateral azul-escuro e área de trabalho em azul muito claro.
- Bordas finas, sem cartões excessivos e sem molduras pesadas.
- Aproveitar a viewport; evitar espaços verticais desnecessários.
- Tipografia proporcional para a interface. Registros de catálogo usam `Courier New` como experimento visual atual; reavaliar antes de consolidar.

## Área administrativa

- Administradores não exibem o `topbar` público.
- A barra lateral é a identidade e a navegação principal da administração.
- O avatar do usuário fica no menu lateral, junto de “Administração”.
- Nome e logout aparecem somente no menu do avatar.
- A visão geral é a tela inicial administrativa.
- CRUDs ficam acessíveis pelo menu lateral.
- Recursos ainda não implementados aparecem desabilitados, sem simular funcionalidades.

## CRUDs

O CRUD de `Nomes de Serviço` é o modelo para os próximos catálogos.

- Título com capitalização de título em português: `Nomes de Serviço`; conectores permanecem em minúsculo.
- Lista paginada com 20 registros por página.
- Busca acionada por ícone de lupa, em modo toggle.
- Paginação no início e no final da lista.
- Paginação possui primeira página, anterior, páginas numéricas, próxima e última.
- Controles de paginação usam ícones, fonte pequena e cor suave.
- Registros são ordenados alfabeticamente, respeitando `pt-BR` e acentos.
- Busca, página atual e seleção são preservadas ao retornar da edição.
- Seleção usa checkbox; clicar no texto da linha não edita.
- Ícone de lápis edita; ícone de lixeira inicia exclusão.
- Ações `Todos`, `Nenhum` e `Inverter seleção` atuam sobre o catálogo.
- Com vários registros selecionados, edição fica desabilitada e exclusão em lote fica disponível.
- Inclusão e edição usam o mesmo formulário; a operação é definida pela presença do registro em edição.
- Ao incluir ou editar, a lista é substituída pelo formulário.
- Cancelar ou salvar retorna à lista no contexto anterior.
- Ações do formulário ficam abaixo dos campos, centralizadas e usam ícones.
- Salvar usa verde suave; cancelar usa vermelho suave.
- Ícones possuem `title` e `aria-label`.

## Mensagens

- Sucesso usa toast verde e desaparece após 3 segundos.
- Erro usa toast vermelho e desaparece após 5 segundos.
- Toasts usam `role="status"` para sucesso e `role="alert"` para erro.
- Exclusão usa diálogo próprio, não `window.confirm`.
- O diálogo de exclusão informa o impacto, apresenta ícone de atenção e oferece cancelar/excluir.

## Próximos CRUDs e relatórios

- Reutilizar a estrutura administrativa e o mesmo padrão de busca, paginação, seleção e editor.
- Relatórios devem seguir a mesma linguagem visual compacta, com filtros, totais e tabelas.
- Relatórios devem respeitar o escopo do papel e da organização do usuário.
- Evitar dashboards genéricos ou gráficos decorativos antes de existir uma necessidade operacional clara.
- Os CRUDs territoriais usam paginação no servidor, com janela de 20 registros, busca e filtros relacionais; a administração nunca carrega todas as localidades no navegador.

## Critérios de manutenção

- Preferir KISS e DRY: abstrair componentes quando o mesmo padrão aparecer em mais de um CRUD.
- Não duplicar formulários, paginação, toasts ou diálogos de confirmação.
- Todo componente criado deve possuir um `id` estável e semântico para automação de testes.
- Componentes de tela não devem compartilhar estado de dados implicitamente; contexto, busca, seleção e edição devem ser isolados por rota ou feature.
- Qualquer compartilhamento de estado entre telas exige contrato explícito, chave de contexto e justificativa da operação.
- Campos com máscara fixa devem ter largura visual baseada no tamanho máximo do valor: `quantidade máxima de caracteres × 13px`. Por exemplo, CPF usa `11 × 13px = 143px` e CNPJ usa `14 × 13px = 182px`.
- Campos de input da área administrativa usam fonte de `0.75rem` (`12px`) e altura padrão de `30px`; labels usam `0.75rem`.
- Listas administrativas usam texto de `0.75rem` (`12px`), `line-height: 1.15` e espaçamento vertical compacto; checkboxes e ações mantêm seu tamanho de interação.
- Manter regras de negócio e autorização no backend; o frontend apenas apresenta estados e chama contratos da API.
- Usar `npm run build` após mudanças de frontend.
