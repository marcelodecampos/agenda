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

- **Cartão de fidelidade (requisito de MVP, totalmente flexível/parametrizável)**:
  - O profissional/estabelecimento cria **programas de fidelidade** associados a um serviço específico ou a um pacote de serviços — nunca uma regra fixa/genérica hardcoded.
  - **Múltiplos programas simultâneos e combináveis**: o mesmo serviço/pacote pode ter mais de um programa de fidelidade ativo ao mesmo tempo (ex: "a cada 5 manicures, a 6ª tem 50% de desconto" + "a cada 10 manicures, 1 grátis"), e um cliente pode acumular progresso em vários programas ao mesmo tempo, sem serem mutuamente exclusivos.
  - **Modelo de dados**: um "Programa de Fidelidade" define critério de contagem (ex: nº de atendimentos concluídos de um serviço/pacote-alvo) e recompensa (desconto fixo, percentual, serviço/produto grátis, etc.), com serviço/pacote-alvo configurável — mesma filosofia dos demais itens do MVP (nada de enum ou regra fixa em código).
  - **Cartões diferenciados para clientes VIP**: o profissional/estabelecimento pode definir um programa de fidelidade alternativo, vinculado a um segmento "VIP" de clientes, que **sobrepõe** (substitui) o programa padrão do serviço/pacote para esses clientes específicos — não se soma ao padrão, mas tem precedência sobre ele.
  - Reaproveita o histórico de atendimentos concluídos (já previsto no ciclo de vida do agendamento) como fonte de dados para contagem de progresso, sem depender de pagamento pela plataforma.

- **Papéis (roles) do sistema (requisito arquitetural chave, base para autorização)**:
  - **Modelo de autorização escolhido**: RBAC escopado por Membership, com papéis e permissões representados como dados (catálogo de Papel + catálogo de Permissão + tabela Papel↔Permissão), na mesma filosofia do ciclo de vida do agendamento — nada de papel/permissão fixo em enum de código.
  - **Papéis de escopo de organização** (atribuídos via Membership a um Estabelecimento):
    - **Dono**: dono do estabelecimento; presta serviço e/ou administra.
    - **Autônomo Puro**: caso particular de Dono — profissional sem equipe, cuja Organização é unipessoal (ele mesmo). Listado como papel próprio para clareza de negócio, mas implementado mecanicamente como **Dono** de uma Organização de um único membro — não é uma estrutura de dados à parte.
    - **Funcionário**: profissional vinculado formalmente ao estabelecimento.
    - **Autônomo Associado**: profissional autônomo que usa o espaço do estabelecimento, sem vínculo formal de emprego.
  - **Papéis de escopo global/plataforma** (sem vínculo de Membership com um estabelecimento):
    - **Cliente**: usuário final que descobre e agenda serviços.
    - **Administrador da Plataforma**: gestão operacional da plataforma (ex: aprovação/suspensão de cadastro de profissionais/estabelecimentos, visão geral de uso) — escopo mínimo no MVP, sem funcionalidades administrativas avançadas ainda não solicitadas (YAGNI).
  - **Papéis secundários (múltiplos papéis por Membership)**: um Membership não fica restrito a um único papel. Um Funcionário, por exemplo, pode acumular um papel secundário (ex: "Gerente", "Instrutor") que adiciona permissões extras às do papel principal, sem substituí-lo. Modelagem: `Membership ↔ Papel` é **N:N** (não 1:1) — a tabela de permissões efetivas de um Membership é a união das permissões de todos os papéis atribuídos a ele.
  - **Premissa permanente de extensibilidade**: o catálogo de Papéis (e o de Permissões) é **aberto por definição** — o profissional/estabelecimento ou a plataforma podem criar novos papéis, novos perfis, ou combinações de papéis existentes a qualquer momento, sem exigir mudança de código. A lista acima é o ponto de partida do MVP, não um limite fixo do sistema.
  - **Fora do MVP por enquanto**: papéis administrativos não-profissionais dentro do estabelecimento (ex: recepcionista) — não há necessidade comprovada agora; como papéis são dados, podem ser adicionados depois sem mudança de código.

- **Catálogo de permissões por papel (MVP)**: derivado das funcionalidades já decididas. É o **ponto de partida**, não uma lista fechada — novas permissões podem ser adicionadas conforme o catálogo de Papéis evolui (dado, não enum).

  | Permissão | O que cobre | Dono | Autônomo Puro | Funcionário | Autônomo Associado | Cliente | Admin. Plataforma |
  |---|---|---|---|---|---|---|---|
  | `agenda.configurar` | Definir disponibilidade, horários, exceções, folgas | ✔ | ✔ | ✔ (própria) | ✔ (própria) | — | — |
  | `agenda.visualizar` | Ver horários disponíveis/ocupados | ✔ | ✔ | ✔ | ✔ | ✔ (público) | — |
  | `servico.gerenciar` | Criar/editar/excluir serviços e modalidades de atendimento | ✔ | ✔ | — | ✔ (próprios) | — | — |
  | `pacote.gerenciar` | Criar/editar pacotes de serviços | ✔ | ✔ | — | ✔ (próprios) | — | — |
  | `agendamento.solicitar` | Cliente solicita/agenda um atendimento | — | — | — | — | ✔ | — |
  | `agendamento.transicionar_status` | Confirmar, recusar, cancelar, marcar como concluído/não compareceu | ✔ | ✔ | ✔ (próprios) | ✔ (próprios) | ✔ (próprio, conforme transições permitidas ao ator "cliente") | — |
  | `agendamento.visualizar_estabelecimento` | Ver agendamentos de todo o estabelecimento (não só os próprios) | ✔ | ✔ (só tem os próprios) | — | — | — | — |
  | `agendamento.visualizar_proprio` | Ver os próprios agendamentos (como cliente) | ✔ | ✔ | ✔ | ✔ | ✔ | — |
  | `fidelidade.configurar_programa` | Criar/editar programas de fidelidade (incl. regras VIP) | ✔ | ✔ | — | ✔ (próprios serviços) | — | — |
  | `fidelidade.visualizar_proprio_progresso` | Cliente ver o próprio progresso nos cartões de fidelidade | — | — | — | — | ✔ | — |
  | `cliente.ver_ficha` | Ver histórico de confiabilidade (cancelamentos, no-shows) de um cliente | ✔ | ✔ | ✔ (próprios clientes) | ✔ (próprios clientes) | — | — |
  | `estabelecimento.gerenciar_equipe` | Convidar/remover Membership, atribuir papéis (incl. secundários) | ✔ | — (não se aplica, é unipessoal) | — | — | — | — |
  | `estabelecimento.configurar_dados` | Nome, endereço, horário de funcionamento do estabelecimento | ✔ | ✔ (dados próprios) | — | — | — | — |
  | `comissao.configurar_regra` | Definir regra de comissão (percentual/valor fixo) por Membership e/ou serviço | ✔ | — (não se aplica, sem equipe) | — | — | — | — |
  | `comissao.visualizar_relatorio` | Ver relatório de comissão devida (cálculo, sem movimentar dinheiro) | ✔ | — (não se aplica) | ✔ (próprio) | ✔ (próprio) | — | — |
  | `plataforma.aprovar_cadastro` | Aprovar/rejeitar cadastro de profissional/estabelecimento | — | — | — | — | — | ✔ |
  | `plataforma.suspender_conta` | Suspender/banir conta por violação | — | — | — | — | — | ✔ |
  | `plataforma.visualizar_metricas_globais` | Visão agregada de uso da plataforma | — | — | — | — | — | ✔ |

  - **Papéis secundários usam o mesmo catálogo**: um "Gerente" (papel secundário de Funcionário) seria apenas uma linha adicional nessa tabela concedendo, por exemplo, `estabelecimento.gerenciar_equipe` a quem também tem o papel Funcionário — sem exigir estrutura nova.
  - **Fora do MVP por enquanto**: permissões financeiras (repasse, comissão, estatísticas avançadas) — dependem de itens do roadmap pós-MVP ainda não priorizados.

## Funcionalidades adicionais desejadas (roadmap pós-MVP)

## Escopo fechado do MVP

Consolidação de tudo que compõe a primeira entrega, resolvendo a pendência "decisão de quais funcionalidades entram no MVP":

- Descoberta (busca por categoria/localização/proximidade) e geolocalização com deslocamento flexível por serviço.
- Agenda parametrizável (disponibilidade, exceções, feriados informativos) e ciclo de vida de agendamento com status/transições como dados.
- Redução de no-show (lembretes automáticos WhatsApp/SMS/e-mail).
- Serviços com modalidades de atendimento, pacotes e múltiplos serviços por agendamento.
- Cartão de fidelidade flexível (programas combináveis + sobreposição VIP).
- Ficha técnica do cliente (histórico de confiabilidade), reaproveitando o histórico de transições de status.
- Papéis e permissões (RBAC via Membership, catálogo já fechado).
- **Gestão básica do estabelecimento** (cadastro do estabelecimento, horários de funcionamento, convite/gestão de equipe via Membership): promovida do roadmap para o MVP porque é **pré-requisito direto** das permissões já fechadas (`estabelecimento.gerenciar_equipe`, `estabelecimento.configurar_dados`) — sem isso, Dono não tem como formar equipe nem o Membership N:N vira operável.
- **Estatísticas básicas** (volume de agendamentos, taxa de no-show, ocupação da agenda): promovida do roadmap para o MVP em versão mínima, porque os dados já existem "de graça" a partir do ciclo de vida do agendamento (mesmo motivo da ficha do cliente) e agregam valor perceptível ao salão-piloto pagante a baixo custo de implementação. **Não inclui** "insights de desempenho" (análises comparativas/tendências), que permanece fora do MVP.
- **Comissão de equipe** (revisado — ver nota abaixo): cálculo/relatório de quanto o estabelecimento deve pagar a cada Funcionário/Autônomo Associado, a partir de uma regra de comissão configurável (percentual ou valor fixo, por Membership e/ou por serviço) aplicada sobre os agendamentos concluídos. **Não envolve movimentação real de dinheiro pela plataforma** — o Dono continua pagando a equipe por fora, da mesma forma que o cliente paga o profissional diretamente. Promovida ao MVP porque não depende de pagamento passar pela plataforma (a dependência registrada originalmente só valia para o repasse automático via plataforma, não para o cálculo em si) e reaproveita dados já existentes (`Serviço.preço`, `Agendamento` concluído, `Membership`).
- Autenticação via Keycloak (OIDC/OAuth2), sem senha própria armazenada.
- Conformidade LGPD básica (minimização de dados, CPF do cliente opcional).

**Fora do MVP** (permanece no roadmap do produto, não descartado — ver seção seguinte): repasse automático de comissão pela plataforma (movimentação real de dinheiro), fluxo de receitas/financeiro completo, insights de desempenho avançados, mensagens em massa, agendamento via redes sociais, processamento de pagamento/repasse, apps nativos.

## Funcionalidades adicionais desejadas (roadmap pós-MVP)

Itens que ampliam o escopo além do MVP fechado acima. Permanecem no roadmap do produto (não descartados), mas não entram na primeira entrega:

- **Agendamento via redes sociais** (Instagram, Facebook, Google e outros): integração com APIs de mensageria/agendamento dessas plataformas para captar clientes onde eles já estão. Fora do MVP: maior dependência de integrações externas, e o lançamento já usa recrutamento manual (não depende de descoberta via redes sociais).
- **Repasse automático de comissão pela plataforma**: diferente do *cálculo* de comissão (que entrou no MVP), o repasse automático (a plataforma efetivamente transferir o valor ao Funcionário/Autônomo Associado) depende de processamento de pagamento pela plataforma (fase futura), ainda não decidido para o MVP.
- **Fluxo de receitas** (caixa/financeiro completo): acompanhamento de entradas por profissional/estabelecimento além do relatório de comissão do MVP — não é essencial para validar a proposta de valor central (agenda + no-show + fidelidade) com o salão-piloto.
- **Insights de desempenho**: análises mais avançadas (ex: comparação entre profissionais/serviços, tendências), construídas sobre os dados das estatísticas básicas do MVP.
- **Mensagens em massa**: campanhas de comunicação para clientes (promoções, lembretes gerais) — reaproveita a infraestrutura de notificação já prevista para lembretes de no-show, mas não é core para a validação inicial.

**Observação de dependências**: repasse automático de comissão e fluxo de receita completo dependem de pagamento passar pela plataforma. Agendamento via redes sociais e mensagens em massa são independentes, mas exigem integração com APIs externas — candidatos a entrar logo após o MVP validar o salão-piloto.

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
4. ~~Definir MVP técnico mínimo para validar com o salão-piloto.~~ **Fechado** — ver seção "Escopo fechado do MVP".
5. Escolher provedor de geocoding/distância (Google Maps Platform vs. OpenStreetMap/Nominatim + OSRM) considerando custo e cobertura no Brasil.
6. Definir fórmula de custo de deslocamento (R$/km, taxa fixa, quem paga) para serviços com atendimento domiciliar.
7. Detalhar requisitos LGPD (base legal, política de privacidade, retenção/exclusão de dados, criptografia) antes de armazenar endereço/CPF.
8. Planejar arquitetura de pagamento e repasse (split de pagamento) para a fase futura de processamento de cobrança pela plataforma.

## Próximo passo sugerido

Esboçar tabela de preços inicial (ex: plano solo + valor incremental por profissional extra) baseada no padrão Booksy/Trinks, assim que as decisões acima forem fechadas.
