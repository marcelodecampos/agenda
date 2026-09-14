# Configuração reproduzível do Keycloak

O projeto possui duas formas de configurar o realm `agenda`:

- [config/realm.json](../config/realm.json) + `scripts/bootstrap.py`: configuração declarativa e idempotente via Admin REST API;
- um export completo nesta pasta, para import automático na inicialização do Keycloak.

O bootstrap é a opção recomendada para desenvolvimento porque pode ser executado novamente sem duplicar clients ou roles.

## Política de identidade

Para novos usuários da Agenda, o `username` do Keycloak deve ser o CPF normalizado com 11 dígitos. O nome pode se repetir e não participa da unicidade. O e-mail e o telefone são contatos únicos opcionais; o realm está configurado para não permitir e-mails duplicados.

O `sub` emitido pelo Keycloak continua sendo a referência externa vinculada ao UUIDv7 do usuário interno. CPF, e-mail e telefone não substituem esse vínculo técnico.

Os usuários administrativos declarados no arquivo de desenvolvimento usam seus CPFs como usernames. Como o Keycloak trata `username` como imutável, a migração de um username legado remove e recria o usuário; por isso o `sub` externo pode mudar e o usuário interno da Agenda deve ser reconciliado pelo fluxo de identidade antes de acessar dados existentes.

## Bootstrap via Admin REST API

Defina as credenciais administrativas no ambiente. Elas são as mesmas usadas pelo `docker-compose.yml`:

```powershell
$env:KEYCLOAK_BASE_URL = "http://localhost:8080"
$env:KEYCLOAK_ADMIN = "admin"
$env:KEYCLOAK_ADMIN_PASSWORD = "sua-senha-local"
$env:KEYCLOAK_MARCELO_PASSWORD = "senha-local-do-marcelo"
$env:KEYCLOAK_LEILA_PASSWORD = "senha-local-da-leila"
```

Execute a partir da raiz do projeto:

```powershell
.\.venv\Scripts\python.exe keycloak/scripts/bootstrap.py
```

O script cria ou atualiza:

- o realm `agenda`;
- o client `agenda-api`;
- o client público `agenda-web`;
- o role técnico `platform_admin`.
- os usuários declarados em `config/realm.json`, com o role `platform_admin`.

Papéis e permissões de negócio continuam na Agenda, em `Membership` e `Papel`; não são duplicados no Keycloak.

## Refazer o realm local

O reset é destrutivo e exige confirmação explícita:

```powershell
.\.venv\Scripts\python.exe keycloak/scripts/reset.py --yes
.\.venv\Scripts\python.exe keycloak/scripts/bootstrap.py
```

Não execute o reset em ambientes compartilhados ou de produção.

## Export automático

Se usar `start-dev --import-realm`, coloque um export do realm nesta pasta. O Keycloak importa o realm na criação inicial; alterações posteriores devem ser aplicadas pelo bootstrap idempotente ou pelo Admin Console.

Nunca versione senhas reais, tokens ou secrets de clientes neste diretório.
