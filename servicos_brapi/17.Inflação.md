# Inflação
URL: /docs/inflacao.mdx

Endpoints para acessar dados históricos de Índices de Inflação. Permite consultar a inflação de diferentes países ao longo do tempo e listar os países com dados disponíveis.

***

title: Inflação
description: >-
Endpoints para acessar dados históricos de Índices de Inflação. Permite
consultar a inflação de diferentes países ao longo do tempo e listar os países
com dados disponíveis.
full: true
keywords: brapi, api, documentação, inflação
openGraph:
title: Inflação
description: >-
Endpoints para acessar dados históricos de Índices de Inflação. Permite
consultar a inflação de diferentes países ao longo do tempo e listar os
países com dados disponíveis.
type: website
locale: pt\_BR
lastUpdated: '2025-04-28T01:22:35.255Z'
lang: pt-BR
\_openapi:
method: GET
route: /api/v2/inflation
toc:

* depth: 2
  title: Buscar Dados Históricos de Inflação por País
  url: '#buscar-dados-históricos-de-inflação-por-país'
  structuredData:
  headings:
  * content: Buscar Dados Históricos de Inflação por País
    id: buscar-dados-históricos-de-inflação-por-país
    contents:
  * content: >-
    Obtenha dados históricos sobre índices de inflação para um país
    específico.

    ### Funcionalidades:

    * **Seleção de País:** Especifique o país desejado com o parâmetro
      `country` (padrão: `brazil`).

    * **Filtragem por Período:** Defina um intervalo de datas com
      `start` e `end` (formato DD/MM/YYYY).

    * **Inclusão de Histórico:** O parâmetro `historical` (booleano)
      parece controlar a inclusão de dados históricos (verificar
      comportamento exato, pode ser redundante com `start`/`end`).

    * **Ordenação:** Ordene os resultados por data (`date`) ou valor
      (`value`) usando `sortBy` e `sortOrder`.

    ### Autenticação:

    Requer token de autenticação via `token` (query) ou `Authorization`
    (header).

    ### Exemplo de Requisição:

    **Buscar dados de inflação do Brasil para o ano de 2022, ordenados por
    valor ascendente:**

    ```bash

    curl -X GET
    "https://brapi.dev/api/v2/inflation?country=brazil&start=01/01/2022&end=31/12/2022&sortBy=value&sortOrder=asc&token=SEU_TOKEN"

    ```

    **Buscar os dados mais recentes de inflação (sem período definido,
    ordenação padrão):**

    ```bash

    curl -X GET
    "https://brapi.dev/api/v2/inflation?country=brazil&token=SEU_TOKEN"

    ```

    ### Resposta:

    A resposta contém um array `inflation`, onde cada objeto representa um
    ponto de dado de inflação com sua `date` (DD/MM/YYYY), `value` (o
    índice de inflação como string) e `epochDate` (timestamp UNIX).
    heading: buscar-dados-históricos-de-inflação-por-país

***

Endpoints para acessar dados históricos de **Índices de Inflação**.

Permite consultar a inflação de diferentes países ao longo do tempo e listar os
países com dados disponíveis.

<DocsQuickInfo>
  <Callout type="info" title="Fontes de Dados">
    Dados do **IBGE** (IPCA, INPC) e **BCB** para séries históricas desde 1980.
  </Callout>

  <AnswerBox
    question="Como obter dados de inflação do Brasil?"
    answer="GET /api/v2/inflation?country=brazil retorna série histórica do IPCA."
    relatedEndpoints={[
  { name: "Inflação", path: "/api/v2/inflation" },
  { name: "Países", path: "/api/v2/inflation/available" }
]}
    codeExample={`const inflation = await client.inflation.retrieve({ country: 'brazil' });
console.log(inflation.inflation[0].value);`}
    note="Período: ?start=01/01/2024&end=31/12/2024. Ordenar: ?sortBy=value"
  />
</DocsQuickInfo>





## Swagger Documentation

# Brapi - API do Mercado Financeiro Brasileiro - /api/v2/inflation

Single endpoint documentation for /api/v2/inflation

## Base URLs

- `https://brapi.dev` - Servidor principal da API Brapi
- `http://localhost:3000` - Servidor local para desenvolvimento

## GET /api/v2/inflation

**Summary:** Buscar Dados Históricos de Inflação por País

Obtenha dados históricos sobre índices de inflação para um país específico.

### Funcionalidades:

*   **Seleção de País:** Especifique o país desejado com o parâmetro `country` (padrão: `brazil`).
*   **Filtragem por Período:** Defina um intervalo de datas com `start` e `end` (formato DD/MM/YYYY).
*   **Inclusão de Histórico:** O parâmetro `historical` (booleano) parece controlar a inclusão de dados históricos (verificar comportamento exato, pode ser redundante com `start`/`end`).
*   **Ordenação:** Ordene os resultados por data (`date`) ou valor (`value`) usando `sortBy` e `sortOrder`.

### Autenticação:

Requer token de autenticação via `token` (query) ou `Authorization` (header).

### Exemplo de Requisição:

**Buscar dados de inflação do Brasil para o ano de 2022, ordenados por valor ascendente:**

```bash
curl -X GET "https://brapi.dev/api/v2/inflation?country=brazil&start=01/01/2022&end=31/12/2022&sortBy=value&sortOrder=asc&token=SEU_TOKEN"
```

**Buscar os dados mais recentes de inflação (sem período definido, ordenação padrão):**

```bash
curl -X GET "https://brapi.dev/api/v2/inflation?country=brazil&token=SEU_TOKEN"
```

### Resposta:

A resposta contém um array `inflation`, onde cada objeto representa um ponto de dado de inflação com sua `date` (DD/MM/YYYY), `value` (o índice de inflação como string) e `epochDate` (timestamp UNIX).

**Tags:** Inflação

### Parameters

- **country** (query): **Opcional.** Nome do país para o qual buscar os dados de inflação. Use nomes em minúsculas. O padrão é `brazil`. Consulte `/api/v2/inflation/available` para a lista de países suportados.
- **historical** (query): **Opcional.** Booleano (`true` ou `false`). Define se dados históricos devem ser incluídos. O comportamento exato em conjunto com `start`/`end` deve ser verificado. Padrão: `false`.
- **start** (query): **Opcional.** Data de início do período desejado para os dados históricos, no formato `DD/MM/YYYY`. Requerido se `end` for especificado.
- **end** (query): **Opcional.** Data final do período desejado para os dados históricos, no formato `DD/MM/YYYY`. Requerido se `start` for especificado.
- **sortBy** (query): **Opcional.** Campo pelo qual os resultados da inflação serão ordenados.
- **sortOrder** (query): **Opcional.** Direção da ordenação: `asc` (ascendente) ou `desc` (descendente). Padrão: `desc`. Requer que `sortBy` seja especificado.
- **undefined** (undefined)

### Responses

#### 200

**Sucesso.** Retorna os dados históricos de inflação para o país e período solicitados.

#### 400

**Bad Request.** A requisição pode estar malformada, um parâmetro como `start`/`end` pode ter formato inválido, ou o país solicitado pode não ser encontrado.

**Example Response:**

```json
{
  "error": true,
  "message": "Something went wrong while fetching the data"
}
```

#### 401

#### 417

**Expectation Failed.** Valor de parâmetro inválido. Geralmente ocorre se um valor inválido for fornecido para `sortBy` ou `sortOrder`.

**Example Response:**

```json
{
  "error": true,
  "message": "this query value is not available, please use one of the following: asc,desc"
}
```

## Schemas

The following schemas are used by this endpoint:

### ErrorResponse

Schema padrão para respostas de erro da API.

**Properties:**

- **error** (boolean) *(required)*
  Indica se a requisição resultou em erro. Sempre `true` para este schema.

- **message** (string) *(required)*
  Mensagem descritiva do erro ocorrido.


### InflationEntry

Representa um ponto de dado histórico de inflação para um país.

**Properties:**

- **date** (string)
  Data da medição da inflação, no formato `DD/MM/YYYY`.

- **value** (string)
  Valor do índice de inflação para a data especificada (formato string, pode conter `%` ou ser apenas numérico).

- **epochDate** (integer, int64)
  Timestamp UNIX (número de segundos desde 1970-01-01 UTC) correspondente à `date`.


### InflationResponse

Resposta principal do endpoint `/api/v2/inflation`.

**Properties:**

- **inflation** (array)
  Array contendo os registros históricos de inflação para o país e período solicitados.
  Array items:
    Reference to: **InflationEntry**


