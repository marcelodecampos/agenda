# Princípios de Desenvolvimento - Backup GitHub

## Diretrizes Fundamentais

### 1. Transparência e Comunicação Clara
**Don't assume. Don't hide confusion. Surface tradeoffs.**

- Não faça suposições sobre requisitos ambíguos
- Exponha dúvidas e incertezas imediatamente
- Documente trade-offs de decisões arquiteturais
- Questione antes de implementar interpretações próprias
- Mantenha README.md alinhado com código e comportamento real

**Aplicação no projeto:**
- Validações Fail Fast expõem erros cedo
- Exceções com mensagens claras e exception chaining (`from e`)
- Logs estruturados em níveis apropriados
- Documentação técnica em ARCHITECTURE.md

### 2. Minimalismo e YAGNI
**Minimum code that solves the problem. Nothing speculative.**

- Implemente apenas o que está especificado no README.md
- Evite abstrações prematuras ou "por precaução"
- Não adicione funcionalidades "que podem ser úteis no futuro"
- Prefira soluções simples e diretas (KISS)
- Código especulativo viola YAGNI

**Aplicação no projeto:**
- Apenas branch padrão, sem tags (conforme requisito)
- Ports com métodos estritamente necessários
- Sem frameworks de DI desnecessários
- Testes cobrem comportamento real, não cenários imaginários

### 2.1. Isolamento e substituibilidade arquitetural

O sistema deve ser construído como um **monólito modular** no MVP, com fronteiras explícitas entre domínio, casos de uso e infraestrutura. A ausência de microserviços não autoriza acoplamento direto entre módulos.

- O domínio e os casos de uso não devem depender diretamente de frameworks, brokers, provedores externos, ORMs ou detalhes de infraestrutura.
- Componentes com probabilidade relevante de substituição devem ser acessados por ports (contratos) e implementados por adapters.
- Ports devem representar capacidades do negócio, e não reproduzir a API de um fornecedor.
- Integrações como filas, notificações, geolocalização, autenticação e persistência devem poder trocar de implementação sem alterações no domínio.
- Celery, RabbitMQ, Redis ou qualquer alternativa de mensageria devem ficar atrás de uma porta de fila; a troca pode exigir mudanças no adapter, configuração, testes de integração e propriedades operacionais do contrato.
- Contratos de dados, eventos e APIs entre módulos devem ser versionáveis e não podem depender de classes internas, ORM ou tipos específicos de Python.
- Uma futura implementação em Go ou Rust deve ser viável na fronteira de um módulo por meio de contrato de rede ou eventos, sem compartilhamento direto de estado interno.
- Cada substituição deve ser protegida por testes unitários, testes de integração e, quando houver mais de uma implementação, testes de contrato.
- “Substituível” significa reduzir o raio e o tempo de mudança; não significa custo zero nem eliminar diferenças semânticas entre tecnologias.
- Não criar abstrações para dependências estáveis ou sem necessidade comprovada. A portabilidade deve ser priorizada apenas nas fronteiras que apresentem risco real de mudança.

### 3. Cirurgia Precisa e Responsabilidade
**Touch only what you must. Clean up only your own mess.**

- Modifique apenas arquivos relacionados à tarefa atual
- Não refatore código não relacionado "de passagem"
- Se criar código temporário, remova antes de commitar
- Respeite convenções existentes do código ao redor
- Mantenha blast radius reduzido

**Aplicação no projeto:**
- Cada camada tem responsabilidade única (SRP)
- Adapters isolados não impactam domínio
- Mudanças em um port não afetam outros
- Testes unitários isolam componentes

### 4. Verificação e Critérios de Sucesso
**Define success criteria. Loop until verified.**

- Estabeleça critérios mensuráveis antes de implementar
- Execute testes após cada mudança
- Verifique lint, formatação e erros de compilação
- Confirme alinhamento com requisitos do README.md
- Itere até todos os critérios serem atendidos

**Aplicação no projeto:**
- README.md define requisito funcional oficial
- Testes automatizados validam comportamento (pytest)
- Lint e formatação verificados (ruff)
- Cobertura de código rastreada (pytest-cov)
- CI/CD garante qualidade contínua

## Alinhamento com Padrões Corporativos

Estes princípios reforçam e complementam:

- **SOLID**: Especialmente SRP e DIP
- **Clean Architecture**: Dependency Rule e separação de concerns
- **DDD**: Domínio rico com validações, linguagem ubíqua
- **Fail Fast**: Validar pré-condições antes de efeitos colaterais
- **YAGNI**: Não implementar funcionalidade não solicitada
- **KISS**: Soluções simples; evitar abstrações desnecessárias

### Diretriz arquitetural do MVP

O MVP será um monólito modular, sem microserviços, com a seguinte regra de dependência:

```text
Domínio -> Casos de uso -> Ports -> Adapters -> Infraestrutura
```

O domínio não conhece Celery, RabbitMQ, provedores de e-mail, bancos de dados ou frameworks web. A composição concreta das implementações ocorre na borda da aplicação. A separação deve ser suficiente para permitir, quando justificado por desempenho, memória, custo ou operação, a substituição de um módulo Python por um componente em Go ou Rust.

## Checklist de Qualidade

Antes de considerar uma tarefa completa:

- [ ] Requisito do README.md atendido
- [ ] Testes unitários passando (`pytest`)
- [ ] Cobertura adequada (domain e application 100%)
- [ ] Lint sem erros (`ruff check`)
- [ ] Código formatado (`ruff format`)
- [ ] Sem erros de compilação/importação
- [ ] Domínio sem dependências diretas de infraestrutura
- [ ] Integrações substituíveis isoladas atrás de ports/adapters
- [ ] Contratos entre módulos cobertos por testes apropriados
- [ ] Logs apropriados (INFO para fluxo, ERROR para falhas)
- [ ] Exceções com mensagens claras e chaining
- [ ] Documentação atualizada se comportamento mudou
- [ ] Métodos < 60 linhas
- [ ] Nomes pronunciáveis e pesquisáveis
- [ ] Sem comentários desnecessários

## Antipadrões a Evitar

❌ Implementar features "úteis no futuro"  
❌ Refatorar código não relacionado  
❌ Adicionar abstrações sem necessidade comprovada  
❌ Suprimir exceções silenciosamente  
❌ Logar informações sensíveis (tokens, senhas)  
❌ Duplicar lógica já existente  
❌ Violar separação de camadas  
❌ Concatenar SQL sem parametrização  
❌ Assumir requisitos não documentados  

## Workflow de Desenvolvimento

```
1. Ler requisito no README.md
2. Definir critérios de sucesso
3. Implementar mínimo necessário
4. Executar testes (pytest)
5. Verificar lint e formatação (ruff)
6. Atualizar documentação se necessário
7. Verificar critérios de sucesso
8. Loop (voltar ao passo 3) até todos critérios atendidos
```

---

**Lembre-se**: Código simples, testado e alinhado com requisitos > Código "inteligente" e especulativo.
