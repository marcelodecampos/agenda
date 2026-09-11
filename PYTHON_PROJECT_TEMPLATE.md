# PARTE I - TEMPLATE GENÉRICO
> Esta seção contém diretrizes e padrões reutilizáveis para outros projetos Python

## Pré-requisitos Padrão

- Python 3.11 ou superior
- Poetry para gerenciamento de pacotes
- Credenciais de autenticação (configuradas via `.env`)

### Bibliotecas Essenciais

- **typer** - Interface de linha de comando
- **loguru** - Sistema de logs estruturado
- **pydantic-settings** - Gerenciamento de configurações

### Segurança

- Nenhum token ou senha deve ser commitado no git
- Arquivo `.env` para informações sensíveis
- Arquivo `.gitignore` compreensivo configurado
- **Autenticação:** Utilizar `DefaultAzureCredential` (Azure Identity)
  - Suporta múltiplos métodos automaticamente: Managed Identity, Azure CLI, Environment Variables, etc.
  - Ideal para containers (Container Apps, AKS) com Managed Identity
  - Não requer credenciais hardcoded em produção

## Instalação Padrão

```bash
# Clonar o repositório
git clone <repository-url>
cd <project-name>

# Instalar dependências
poetry install

# Ativar ambiente virtual
poetry shell

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais
```


## Tratamento de Erros Padrão

Implementar tratamento abrangente para:
- Variáveis de ambiente ausentes ou inválidas
- Problemas de conectividade de rede
- Falhas de autenticação
- Recursos não encontrados
- Permissões insuficientes
- Falhas nas operações principais

## Sistema de Logs com Loguru

Implementar logs estruturados com **Loguru**:
- Níveis de saída com cores no console
- Mensagens de erro detalhadas com stacktrace
- Indicadores de sucesso e falha
- Acompanhamento de progresso das operações
- Persistência em arquivo e stdout
- Rotação diária automática
- Compressão de logs antigos
- Retenção configurável (padrão: 30 dias)

### Template de Configuração de Logs

Criar diretório `log_config/` e configurar no início da aplicação:

```python
# Remove o handler padrão
logger.remove()

# 1) Saída padrão (console)
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
    level="INFO",
)

# 2) Arquivo com rotação diária + compressão + retenção
logger.add(
    "logs/app.log",
    rotation="00:00",          # cria um novo arquivo todo dia à meia-noite
    retention="30 days",       # mantém logs por 30 dias
    compression="zip",         # comprime arquivos antigos
    encoding="utf-8",
    enqueue=True,              # seguro para threads/processos
    backtrace=True,            # mostra stacktrace completo
    diagnose=True,             # ajuda a depurar erros complexos
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
           "{name}:{function}:{line} - {message}",
)
```

**Estrutura de Logs:**
- `logs/app.log` - Arquivo principal com todas as mensagens
- `logs/app.YYYY-MM-DD.log.zip` - Arquivos comprimidos de dias anteriores

## Configuração com Pydantic Settings

Template para gerenciamento de configurações com **pydantic-settings**:

**Estrutura:**
- Diretório: `src/<project_name>/config/`
- Arquivo único: `__init__.py` (não criar outros arquivos)
- Classe simples sem uso excessivo de `Field`

**Template de Código:**

```python
class EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    # Configurações da Aplicação
    debug: bool = False
    log_level: str = "INFO"
    
    # Adicionar outras variáveis conforme necessário
    # ...

settings = EnvironmentSettings()
```

**Observações:**
- Configurações são carregadas do `.env` automaticamente
- Argumentos CLI sobrescrevem valores do `.env` (precedência maior)
- Validação automática de tipos via Pydantic
- Implementar no CLI: capturar argumentos e atualizar `settings` antes de usar

### Integração CLI com Settings

Para manter o settings atualizado com valores da CLI, usar **kwargs e setattr**:

```python
def update_settings_from_cli(**kwargs) -> None:
    """
    Atualiza settings dinamicamente com valores CLI.
    
    Usa setattr para evitar modificar a função ao adicionar novos parâmetros.
    """
    # Mapeamento de nomes CLI para atributos do settings
    mapping = {
        "subscription_id": "azure_subscription_id",
        "resource_group": "azure_resource_group",
        "debug": "debug",
        "log_level": "log_level",
    }
    
    for cli_name, settings_attr in mapping.items():
        if cli_name in kwargs:
            value = kwargs[cli_name]
            # Atualizar apenas se não for None (exceto bool e strings obrigatórias)
            if value is not None or cli_name in ("debug", "log_level"):
                setattr(settings, settings_attr, value)
```

**Padrão de uso no CLI:**
```python
@app.command()
def main(
    # Argumento posicional obrigatório (sem flag)
    resource_name: str = typer.Argument(help="Nome do recurso"),
    
    # Options com defaults vinculados ao settings
    subscription_id: Optional[str] = typer.Option(
        settings.azure_subscription_id,  # Default vem do settings
        "--subscription-id",
        "-s",
        help="Azure Subscription ID (sobrescreve .env)",
    ),
    debug: bool = typer.Option(
        settings.debug,
        "--debug",
        "-d",
        help="Ativa modo debug",
    ),
) -> None:
    # Atualizar settings com valores CLI
    update_settings_from_cli(
        subscription_id=subscription_id,
        debug=debug,
    )
    
    # Usar settings como fonte única de verdade
    sub_id = settings.azure_subscription_id
```

**Benefícios:**
- Settings sempre reflete valores atuais (CLI > .env > defaults)
- Defaults do settings aparecem no `--help`
- Função de atualização não precisa mudar ao adicionar parâmetros
- Código mais limpo e manutenível

## Estrutura de Projeto Padrão

```
<project_name>/
├── src/
│   └── <project_name>/
│       ├── __init__.py
│       ├── main.py              # CLI com Typer
│       ├── config/
│       │   └── __init__.py      # EnvironmentSettings
│       ├── log_config/
│       │   └── __init__.py      # Configuração de logs
│       ├── services/
│       │   └── __init__.py      # Lógica de negócio
│       └── utils/
│           └── __init__.py      # Utilitários
├── tests/
│   └── __init__.py
├── logs/                        # Arquivos de log (criado em runtime)
├── .env                         # Variáveis de ambiente (não commitado)
├── .env.example                 # Template de variáveis
├── .gitignore
├── pyproject.toml
├── poetry.lock
└── README.md
```

## Arquivo .gitignore

Criar arquivo `.gitignore` compreensivo:
- Configurado para Python
- Regras de segurança (não commitar `.env`, tokens, senhas)
- Excluir logs, caches, ambientes virtuais

## Dependências para Ambientes sem Poetry

Gerar `requirements.txt` para compatibilidade:

```bash
poetry export -f requirements.txt --without-hashes -o requirements.txt
```

**Benefícios:**
- Mantém `pyproject.toml` como fonte única
- Compatibilidade com pip em qualquer ambiente
- Facilita deploys e builds em ambientes restritos


## Diretrizes para Geração de Código Python por LLM

Esta seção define padrões rigorosos para que uma LLM gere código Python seguindo as melhores práticas de engenharia de software. Todo código produzido deve priorizar **clareza**, **manutenibilidade**, **desacoplamento**, **testabilidade** e **robustez**, evitando complexidade desnecessária.

---

### 1. Princípios Fundamentais

#### **KISS (Keep It Simple, Stupid)**
- Prefira soluções simples e diretas.
- Evite abstrações desnecessárias, sobreengenharia e estruturas complexas.
- Cada função deve ter um propósito claro e único.

#### **DRY (Don't Repeat Yourself)**
- Nunca duplique lógica.
- Extraia comportamentos repetidos para funções utilitárias ou classes reutilizáveis.
- Centralize regras de negócio em um único ponto de verdade.

#### **YAGNI (You Aren’t Gonna Need It)**
- Implemente apenas o que é necessário agora.
- Não adicione funcionalidades “por garantia”.

#### **SOLID (quando aplicável)**
- **S**ingle Responsibility: cada classe/módulo deve ter apenas uma responsabilidade.
- **O**pen/Closed: código deve ser extensível sem modificações internas.
- **L**iskov Substitution: subclasses devem ser substituíveis sem quebrar o sistema.
- **I**nterface Segregation: prefira interfaces pequenas e específicas.
- **D**ependency Inversion: dependa de abstrações, não implementações concretas.
