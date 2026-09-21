# Importação de dados territoriais do IBGE

Este documento descreve como importar unidades federativas, municípios e localidades do IBGE para o PostgreSQL da Agenda.

## 1. O que é importado

As migrações criam as tabelas territoriais:

- `unidades_federacao`: 27 UFs, com código IBGE, nome e sigla;
- `municipios`: municípios com código IBGE de 7 dígitos e vínculo com a UF;
- `localidades`: localidades selecionadas, códigos territoriais, categoria, latitude, longitude e altitude.

Os identificadores internos continuam sendo UUIDv7. Os códigos do IBGE ficam em colunas próprias e não substituem os identificadores internos.

O cadastro de localidades usado pelo importador é uma fonte de 2010. A fonte e o ano de referência ficam registrados em cada localidade (`fonte` e `ano_referencia`).

## 2. Pré-requisitos

Execute os comandos a partir da raiz do projeto, em um ambiente com as dependências instaladas:

```powershell
poetry install
```

O PostgreSQL deve estar em execução e a variável de conexão deve estar configurada no `.env` conforme o ambiente local do projeto.

Confira se a conexão está acessível antes de importar:

```powershell
poetry run alembic current
```

## 3. Aplicar as migrações

Aplique o schema antes de executar qualquer importação:

```powershell
poetry run alembic upgrade head
```

As migrações relevantes são:

- `0016_catalogo_unidades_federacao`: cria e popula as UFs;
- `0017_municipios_localidades`: cria municípios e localidades e adapta bases que já tinham a tabela antiga de UFs.

Se o banco informar que a revisão excede 32 caracteres, confirme que está usando a revisão `0017_municipios_localidades`, que é compatível com o tamanho da tabela `alembic_version` existente.

## 4. Importar municípios

Os municípios são obtidos da API oficial de Localidades do IBGE:

```text
https://servicodados.ibge.gov.br/api/v1/localidades/municipios
```

Execute:

```powershell
poetry run python scripts/importar_localidades_ibge.py --municipios
```

O comando:

- baixa a lista atual de municípios;
- relaciona cada município à UF pelos dois primeiros dígitos do código IBGE;
- atualiza o nome e a UF quando o código já existe;
- não cria duplicatas.

## 5. Importar localidades usando KML

Este é o caminho recomendado no Windows, pois não exige GDAL nem ferramentas do Microsoft Access.

Baixe o KML oficial:

```text
https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/cadastro_de_localidades_selecionadas_2010/Google_KML/BR_Localidades_2010_v1.kml
```

Por exemplo, salve-o como:

```text
C:\dados\ibge\BR_Localidades_2010_v1.kml
```

Execute:

```powershell
poetry run python scripts/importar_localidades_ibge.py `
  --localidades-kml "C:\dados\ibge\BR_Localidades_2010_v1.kml"
```

Para importar municípios e localidades em sequência:

```powershell
poetry run python scripts/importar_localidades_ibge.py `
  --municipios `
  --localidades-kml "C:\dados\ibge\BR_Localidades_2010_v1.kml"
```

O KML contém `Placemark`, `SimpleData` e `Point/coordinates`. O importador utiliza, entre outros, os campos:

- `CD_GEOCODMU`: código IBGE do município;
- `NM_LOCALIDADE`: nome da localidade;
- `LAT`: latitude;
- `LONG`: longitude;
- `ALT`: altitude.

As coordenadas são gravadas em graus decimais. O dicionário do IBGE informa datum SIRGAS 2000.

## 6. Alternativa usando MDB

O cadastro também está disponível em formato Microsoft Access/GeoMedia:

```text
https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/cadastro_de_localidades_selecionadas_2010/Geomedia_MDB/BR_Localidades_2010_v1.mdb
```

A importação MDB exige GDAL/OGR com suporte ao driver Access/GeoMedia. Verifique:

```powershell
ogrinfo --version
ogr2ogr --version
ogrinfo --formats | Select-String "Access|GeoMedia"
```

Depois execute:

```powershell
poetry run python scripts/importar_localidades_ibge.py `
  --localidades-mdb "C:\dados\ibge\BR_Localidades_2010_v1.mdb"
```

Se aparecer `executável 'ogrinfo' não encontrado no PATH`, instale GDAL/OGR, reabra o terminal e repita as verificações acima. No Windows, uma opção disponível é o pacote `GISInternals.GDAL`:

```powershell
winget search GDAL
winget install --id GISInternals.GDAL -e
```

O KML continua sendo a alternativa mais simples quando o objetivo é importar os pontos das localidades.

## 7. Validar a importação no PostgreSQL

Confira as quantidades gerais:

```sql
SELECT COUNT(*) AS total_ufs FROM unidades_federacao;
SELECT COUNT(*) AS total_municipios FROM municipios;
SELECT COUNT(*) AS total_localidades FROM localidades;
```

O resultado esperado para as UFs é `27`. A API de Localidades consultada durante a implementação retornou `5.571` municípios; esse total pode mudar em versões futuras da base oficial.

Confira a distribuição de municípios por UF:

```sql
SELECT
    uf.sigla,
    uf.nome,
    COUNT(m.id) AS total_municipios
FROM unidades_federacao uf
LEFT JOIN municipios m
    ON m.unidade_federacao_id = uf.id
GROUP BY uf.id, uf.sigla, uf.nome
ORDER BY uf.sigla;
```

Confira localidades com coordenadas:

```sql
SELECT
    l.nome,
    m.nome AS municipio,
    uf.sigla,
    l.latitude,
    l.longitude,
    l.altitude_metros
FROM localidades l
JOIN municipios m ON m.id = l.municipio_id
JOIN unidades_federacao uf ON uf.id = m.unidade_federacao_id
WHERE l.latitude IS NOT NULL
  AND l.longitude IS NOT NULL
ORDER BY uf.sigla, m.nome, l.nome
LIMIT 20;
```

Confira localidades sem município correspondente:

```sql
SELECT COUNT(*) AS localidades_sem_municipio
FROM localidades l
LEFT JOIN municipios m ON m.id = l.municipio_id
WHERE m.id IS NULL;
```

Esse último resultado deve ser `0`, pois o importador ignora localidades cujo código de município não foi carregado.

## 8. Idempotência e atualização

Os comandos podem ser executados novamente:

- municípios são atualizados por `codigo_ibge`;
- localidades não são duplicadas quando possuem o mesmo `codigo_setor`;
- a importação não apaga registros existentes.

Para atualizar uma fonte, baixe o novo arquivo, confira o ano de referência e execute o importador novamente. A fonte de localidades de 2010 não deve ser confundida com uma atualização automática da divisão territorial atual.

## 9. Relação com a administração

A administração da Agenda acessa esses dados pela API FastAPI, não diretamente pelo PostgreSQL. Os endpoints usam paginação server-side:

```text
GET /admin/unidades-federacao?page=1&page_size=20
GET /admin/municipios?busca=paul&page=1&page_size=20
GET /admin/municipios?unidade_federacao_id=<uf-id>&page=1&page_size=20
GET /admin/localidades?municipio_id=<municipio-id>&page=1&page_size=20
```

O frontend não carrega as mais de 20 mil localidades de uma vez. A busca de município para filtros e formulários começa a consultar a API a partir do terceiro caractere digitado e retorna no máximo 20 opções.

## 10. Fontes oficiais

- [API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)
- [Cadastro de localidades selecionadas 2010](https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/cadastro_de_localidades_selecionadas_2010/)
- [Página do cadastro KML](https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/localidades/cadastro_de_localidades_selecionadas_2010/Google_KML/)
- [Divisão Territorial Brasileira 2025](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/23701-divisao-territorial-brasileira.html)

## 11. CEP e preenchimento de endereço

O sistema não mantém uma tabela local de CEP. Para melhorar o preenchimento,
o backend oferece:

```text
GET /admin/enderecos/cep/{cep}
```

Esse endpoint consulta o [ViaCEP](https://viacep.com.br/), serviço gratuito
para consultas moderadas, e devolve logradouro, bairro, município e UF. O
frontend usa o retorno para preencher os campos do endereço, mas mantém a
possibilidade de edição manual.

O CEP não deve ser tratado como chave definitiva de endereço: pode atender
faixas de logradouro, mudar por atualização postal e não fornece latitude e
longitude. Para coordenadas, o sistema continua usando geocodificação ou os
dados territoriais do IBGE.

Em produção, recomenda-se adicionar cache, rate limit específico e tratamento
de indisponibilidade do ViaCEP. O cadastro deve continuar funcionando mesmo
quando a consulta externa falhar.
