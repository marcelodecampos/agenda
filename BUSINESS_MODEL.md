# Modelo de Negócio — Projeto Agenda

## Ideia inicial
Plataforma para agendar serviços diversos, aproximando clientes de profissionais.

## Decisões tomadas

- **Nicho inicial**: beleza, saúde e bem-estar (manicure, esmalte, depilação, nutricionista, etc.), não generalista.

- **Modelo de receita**: híbrido/flexível — profissional escolhe entre (a) assinatura mensal com valor fixo, ou (b) percentual/comissão por agendamento concluído (sem mensalidade). Reduz barreira de entrada para baixo volume e captura mais receita de alto volume.

- **Escopo do MVP**: descoberta + agenda (busca por categoria/localização, horários disponíveis, agendamento) + redução de no-show (lembretes automáticos WhatsApp/SMS/e-mail, possível sinal/taxa de cancelamento).
  - MVP **não processa pagamento** — cliente paga o profissional diretamente.
  - Consequência: no MVP, o modelo de receita híbrido fica limitado à **assinatura fixa** (comissão por agendamento só é viável quando o pagamento passar pela plataforma — fase futura).

- **Plataforma de acesso (MVP)**: **apenas site responsivo** (funciona bem em celular/tablet/desktop pelo navegador). Sem app nativo/publicado nas lojas por enquanto.
  - Evita a complexidade e o tempo de publicação/aprovação nas lojas (Google Play e Apple App Store) logo de início — equipe nunca fez essa integração.
  - **Visão de futuro (roadmap pós-MVP)**: evoluir para apps nativos/publicados para Android e Apple (iOS/iPadOS), incluindo suporte a tablet. Escolha de stack (nativo vs. React Native/Flutter) fica para quando essa fase for priorizada.
  - Recomendação técnica para viabilizar essa evolução sem retrabalho: construir o site já pensando em PWA (Progressive Web App) e numa API backend bem desacoplada do front-end, facilitando a criação futura do app sem reescrever as regras de negócio.

- **Cliente-piloto real**: já existe um salão de beleza pequeno, com quase todos os serviços do nicho (manicure, esmalte, depilação, etc.), que será o primeiro recrutamento manual (valida a estratégia de foco local + recrutamento manual).

- **Estratégia de lançamento**: recrutamento manual começando por esse salão-piloto; cada profissional recrutado tende a trazer sua própria carteira de clientes.

- **Tipo de usuário/organização (requisito arquitetural chave)**: o modelo precisa suportar arranjos **mistos e flexíveis**, não só "autônomo" OU "salão". Casos a suportar desde o início:
  - Autônomo puro (sem vínculo com estabelecimento).
  - Salão sem funcionários (só o dono presta serviço).
  - Autônomo + salão (profissional atua tanto independente quanto dentro de um salão).
  - Salão + empregados (funcionários vinculados formalmente ao salão).
  - Salão + empregados + autônomos (equipe mista: alguns funcionários fixos, outros prestadores autônomos que usam o espaço).
  - **Implicação de modelagem**: não modelar "profissional" e "salão" como entidades excludentes; precisa de relação profissional↔estabelecimento N:N (um profissional pode estar vinculado a 0, 1 ou vários estabelecimentos, com papéis diferentes — dono, funcionário, autônomo associado), e agenda/serviços podem pertencer ao profissional, ao estabelecimento, ou a ambos.

- **Geolocalização (requisito de produto)**:
  - Buscar profissionais/estabelecimentos mais próximos de um endereço fornecido pelo cliente (residência, trabalho, etc.).
  - **Deslocamento flexível por serviço**: cada serviço pode ser configurado como (a) cliente se desloca até o profissional/salão, (b) profissional se desloca até o cliente (atendimento domiciliar), ou ambos, dependendo do serviço/profissional.
  - Estimativa de custo de deslocamento: sem API pública de preço da Uber para terceiros; usar serviço de distância/tempo (Google Distance Matrix, OSRM/OpenStreetMap) + fórmula própria de custo (ex: R$/km + taxa fixa).

- **LGPD e dados sensíveis**: a plataforma vai armazenar endereços e, futuramente, CPF. Compliance total com a LGPD é obrigatório desde o início (base legal de tratamento, consentimento explícito, minimização de dados, criptografia em repouso/trânsito, direito de exclusão/portabilidade).

- **Visão de longo prazo — pagamento e repasse**: em um momento oportuno (fase futura, fora do MVP), a plataforma deve processar cobrança do cliente e repasse ao profissional (viabilizando a opção de comissão do modelo de receita híbrido e possivelmente cobrança de sinal/taxa de cancelamento).

- **Ciclo de vida do agendamento (requisito arquitetural chave)**: deve ser **totalmente parametrizável**, não fixo em código/banco. Nada de enum hardcoded de status.
  - **Status e transições viram dados**: tabela de status disponíveis + tabela de transições permitidas ("de → para" + quem pode disparar: cliente, profissional ou sistema). Permite adicionar novos status/transições (ex: "Pago", "Reembolsado") no futuro sem alterar código.
  - O domínio expõe uma operação central de transição (ex: `Agendamento.transicionar_para(novo_status, ator)`) que valida contra essa tabela antes de aplicar — regra de negócio centralizada e testável, mas o conteúdo da regra é dado, não código.
  - **Decisão explícita: sem motor de workflow externo (Temporal, Camunda, Step Functions, etc.) por enquanto** — desproporcional para o estágio atual (MVP, salão-piloto único), adiciona infraestrutura/operação/curva de aprendizado sem necessidade comprovada (viola YAGNI do COPILOT.md). Reavaliar apenas se surgir necessidade real de orquestração distribuída (múltiplos serviços, timers, retries automáticos de pagamento).
  - **Status considerados** (organizados por fase, não todos obrigatórios no MVP): pré-agendamento (solicitado, pendente de confirmação, pendente de pagamento, pago, confirmado), execução (em andamento, atrasado, não compareceu, reagendado), pós-execução (concluído, avaliado, arquivado), exceções (cancelado, expirado, falha, reembolsado).
  - MVP não tem pagamento, então status ligados a pagamento (pendente de pagamento, pago, reembolsado) ficam **previstos no modelo de dados mas sem uso** até a fase de pagamento ser implementada.

- **Agenda como núcleo do sistema (requisito arquitetural chave, diferencial de produto)**:
  - A agenda é o **ponto forte e núcleo central** do sistema — deve ser flexível o suficiente para abarcar **qualquer possibilidade de agendamento**, sem limitações artificiais impostas pelo sistema.
  - **Feriados (nacionais, estaduais, municipais)**: buscar de APIs externas e exibir/informar ao profissional e ao cliente, mas **nunca bloquear automaticamente** um horário só por ser feriado — é sempre o profissional quem decide se trabalha ou não nesse dia.
  - **Parametrização da agenda**: o profissional deve poder configurar sua própria disponibilidade da forma mais intuitiva possível — UX/UI é item fundamental aqui, não só a regra de negócio por trás.
  - Nenhuma regra de disponibilidade deve ser fixa/hardcoded — tudo deve ser configurável pelo profissional (dias, horários, exceções, folgas, feriados que ele escolhe respeitar ou não).

- **Atributos do Serviço (MVP)**: duração base, preço base, categoria.
  - **Modalidade de atendimento não é uma ramificação de regra de negócio, é uma variação comercial do mesmo serviço**: local do atendimento (no estabelecimento vs. no endereço do cliente) não muda a natureza do serviço, só gera ajuste de preço e/ou duração.
  - **Modelo**: cada Serviço tem uma lista de modalidades de atendimento aceitas, cada uma com ajuste opcional de preço (fixo ou percentual) e ajuste opcional de duração.
  - **Ajuste de duração não é só deslocamento**: pode ser motivado por deslocamento do profissional, mas também por outros fatores (ex: falta de ferramenta/equipamento que existe no estabelecimento e precisa de tempo extra no atendimento domiciliar). Deve ser **totalmente configurável**, sem semântica fixa amarrada a "tempo de deslocamento".
  - O profissional/estabelecimento define as modalidades padrão que aceita; o serviço herda esse padrão, mas pode sobrescrever com ajustes próprios quando fizer sentido.

- **Sinal/cancelamento no MVP**: **sem cobrança de sinal** — a plataforma ainda não processa pagamento, então não há como cobrar. Fica só como estrutura de dados prevista (campo/regra) para quando o pagamento existir.

- **Ficha técnica do cliente (histórico de confiabilidade)**: o profissional deve ter acesso a um painel com o histórico de comportamento do cliente — quantos cancelamentos, quantos no-shows, etc.
  - Viável para o MVP com baixo custo: reaproveita o histórico de transições de status do agendamento (já previsto no ciclo de vida parametrizável), sem depender de pagamento.
  - Serve de base para o profissional decidir se confirma, recusa ou exige alguma garantia extra de um cliente com histórico ruim.
  - Relacionado ao item "Estatísticas e relatórios" / "Insights de desempenho" do roadmap, mas aplicado à ficha do cliente, não só à performance do profissional/estabelecimento.

- **Campos do Cliente e LGPD (minimização de dados)**:
  - **CPF do cliente: opcional no MVP**, não obrigatório no cadastro — sem pagamento/repasse pela plataforma ainda, não há finalidade concreta que justifique exigir esse dado (princípio da necessidade, Art. 6º da LGPD). Torna-se obrigatório apenas quando a funcionalidade de pagamento/repasse for implementada (finalidade clara: nota fiscal, split de pagamento).
  - **CPF/CNPJ do profissional/estabelecimento**: pode ser exigido mais cedo, pois serve para identificação/verificação de quem está sendo cadastrado como parceiro na plataforma (mitigar fraude), independente de processar pagamento.

- **Múltiplos serviços por agendamento**: **totalmente configurável**, sem limitação fixa. O profissional pode oferecer:
  - Um único serviço avulso por agendamento.
  - Pacotes de serviços (combinação pré-definida pelo profissional, ex: manicure + esmalte com preço/duração de pacote).
  - Múltiplos serviços livres combinados pelo cliente/profissional na hora de agendar.
  - Coerente com o requisito de que a agenda é o núcleo do sistema e não deve ter limitações artificiais.

## Funcionalidades adicionais desejadas (roadmap pós-MVP)

Itens levantados que ampliam o escopo além do MVP mínimo (descoberta + agenda + no-show). Precisam ser priorizados e fasear-se conforme dependências:

- **Agendamento via redes sociais** (Instagram, Facebook, Google e outros): integração com APIs de mensageria/agendamento dessas plataformas para captar clientes onde eles já estão.
- **Gestão do estabelecimento**: cadastro/administração de salão, equipe, horários de funcionamento, serviços oferecidos — depende do modelo profissional↔estabelecimento N:N já definido.
- **Comissão de equipe**: cálculo de comissão de funcionários/autônomos vinculados a um estabelecimento — depende de processamento de pagamento (fase futura) ou ao menos de registro manual de valores recebidos.
- **Fluxo de receitas** (caixa/financeiro): acompanhamento de entradas por profissional/estabelecimento — pode começar como registro manual antes de existir pagamento via plataforma.
- **Estatísticas e relatórios**: volume de agendamentos, taxa de no-show, ocupação da agenda, etc.
- **Insights de desempenho**: análises mais avançadas (ex: comparação entre profissionais/serviços, tendências), construídas sobre os dados de estatísticas.
- **Mensagens em massa**: campanhas de comunicação para clientes (promoções, lembretes gerais) — reaproveita a infraestrutura de notificação já prevista para lembretes de no-show.

**Observação de dependências**: comissão de equipe e fluxo de receita completo dependem de pagamento passar pela plataforma (ainda não decidido para o MVP). Estatísticas/relatórios e gestão do estabelecimento podem ser implementados sem pagamento. Agendamento via redes sociais e mensagens em massa são independentes, mas exigem integração com APIs externas.

**Decisão**: manter esta lista como roadmap **sem ordem de prioridade definida** por enquanto, mas pelo menos parte destes itens deve compor o MVP (não são só "fase futura distante") — todas as funcionalidades listadas aqui devem ser mantidas no escopo do produto, a decisão de quais entram exatamente no MVP fica para quando iniciarmos o design técnico.

## Pesquisa de mercado (concorrentes)

- **Booksy** (referência internacional, beleza/barbearia):
  - Modelo: SaaS por assinatura mensal paga pelo profissional/salão.
  - Preço: US$ 29,99/mês (profissional principal) + US$ 20/mês por profissional adicional.
  - Cliente final não paga nada para agendar.
  - Processamento de pagamento opcional: ~2,49%–2,69% + taxa fixa por transação.
  - "Boost" (impulsionamento no marketplace): grátis para ativar, comissão única de 30% sobre a primeira visita do cliente trazido por essa via.
  - Todas as features incluídas no plano único (sem tiers por funcionalidade).
- **Trinks** (Brasil, beleza/estética):
  - Modelo: SaaS por assinatura mensal, planos escalonados por nº de profissionais/módulos (financeiro, estoque, CRM).
  - Tem marketplace (Trinks App) onde salão paga taxa adicional para aparecer na busca/agenda pública.
  - Página pública não expõe tabela de preços (vendas sob consulta); estimativa de mercado: faixa de R$ 100–300+/mês por unidade (não confirmado oficialmente).
  - Cliente final não paga para agendar.
- **Padrão comum**: profissional/estabelecimento é o cliente pagante (B2B SaaS), cliente final usa grátis. Receita: (1) assinatura recorrente principal, (2) taxas de pagamento/antecipação, (3) marketing pago para visibilidade no marketplace.

## Pontos ainda em aberto

1. Consolidar modelo de negócio em resumo estruturado (opcional).
2. Iniciar design técnico: modelagem de dados (profissional, estabelecimento, vínculo profissional-estabelecimento, serviço, agendamento, cliente), considerando a flexibilidade mista acima.
3. Definir stack/arquitetura do projeto (já é Python, `src/agenda`).
4. Definir MVP técnico mínimo para validar com o salão-piloto.
5. Escolher provedor de geocoding/distância (Google Maps Platform vs. OpenStreetMap/Nominatim + OSRM) considerando custo e cobertura no Brasil.
6. Definir fórmula de custo de deslocamento (R$/km, taxa fixa, quem paga) para serviços com atendimento domiciliar.
7. Detalhar requisitos LGPD (base legal, política de privacidade, retenção/exclusão de dados, criptografia) antes de armazenar endereço/CPF.
8. Planejar arquitetura de pagamento e repasse (split de pagamento) para a fase futura de processamento de cobrança pela plataforma.

## Próximo passo sugerido

Esboçar tabela de preços inicial (ex: plano solo + valor incremental por profissional extra) baseada no padrão Booksy/Trinks, assim que as decisões acima forem fechadas.
