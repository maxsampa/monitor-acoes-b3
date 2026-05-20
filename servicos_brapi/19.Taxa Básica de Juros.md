# Taxa Básica de Juros
URL: /docs/taxa-basica-de-juros.mdx

Endpoints para consulta de Taxas Básicas de Juros (SELIC) de diferentes países. Permite a obtenção de taxas atuais e séries históricas das taxas básicas de juros, com personalização por país, período e opções de ordenação.

***

title: Taxa Básica de Juros
description: >-
Endpoints para consulta de Taxas Básicas de Juros (SELIC) de diferentes
países. Permite a obtenção de taxas atuais e séries históricas das taxas
básicas de juros, com personalização por país, período e opções de ordenação.
full: true
keywords: brapi, api, documentação, taxa de juros, selic, prime rate
openGraph:
title: Taxa Básica de Juros
description: >-
Endpoints para consulta de Taxas Básicas de Juros (SELIC) de diferentes
países. Permite a obtenção de taxas atuais e séries históricas das taxas
básicas de juros, com personalização por país, período e opções de
ordenação.
type: website
locale: pt\_BR
lastUpdated: '2025-04-29T10:30:45.123Z'
lang: pt-BR
\_openapi:
method: GET
route: /api/v2/prime-rate
toc:

* depth: 2
  title:
  Buscar Taxa Básica de Juros (SELIC) de um País por um Período
  Determinado
  url: '#buscar-taxa-básica-de-juros-selic-de-um-país-por-um-período-determinado'
  structuredData:
  headings:
  * content:
    Buscar Taxa Básica de Juros (SELIC) de um País por um Período
    Determinado
    id: buscar-taxa-básica-de-juros-selic-de-um-país-por-um-período-determinado
    contents:
  * content: >-
    Obtenha informações atualizadas sobre a taxa básica de juros (SELIC)
    de um país por um período determinado.

    ### Funcionalidades:

    * **Seleção por País:** Especifique o país desejado usando o
      parâmetro `country` (padrão: brazil).

    * **Período Customizado:** Defina datas de início e fim com `start`
      e `end` para consultar um intervalo específico.

    * **Ordenação:** Ordene os resultados por data ou valor com os
      parâmetros `sortBy` e `sortOrder`.

    * **Dados Históricos:** Solicite o histórico completo ou apenas o
      valor mais recente com o parâmetro `historical`.

    ### Autenticação:

    Requer token de autenticação via `token` (query) ou `Authorization`
    (header).

    ### Exemplo de Requisição:

    **Taxa de juros do Brasil entre dezembro/2021 e janeiro/2022:**

    ```bash

    curl -X GET
    "https://brapi.dev/api/v2/prime-rate?country=brazil&start=01/12/2021&end=01/01/2022&sortBy=date&sortOrder=desc&token=SEU_TOKEN"

    ```

    **Buscar a taxa básica de juros atual do Brasil:**

    ```bash

    curl -X GET
    "https://brapi.dev/api/v2/prime-rate?country=brazil&token=SEU_TOKEN"

    ```

    ### Resposta:

    A resposta contém um array `prime-rate`, onde cada objeto representa
    um ponto de dado da taxa básica de juros com sua `date` (DD/MM/YYYY),
    `value` (o valor da taxa como string) e `epochDate` (timestamp em
    milissegundos).
    heading: buscar-taxa-básica-de-juros-selic-de-um-país-por-um-período-determinado

***

Endpoints para consulta de **Taxas Básicas de Juros (SELIC)** de diferentes
países.

Permite a obtenção de taxas atuais e séries históricas das taxas básicas de
juros, com personalização por país, período e opções de ordenação.

<DocsQuickInfo>
  <Callout type="info" title="Fonte de Dados">
    Taxa SELIC obtida do **BCB** via Sistema Gerenciador de Séries Temporais (SGS).
  </Callout>

  <AnswerBox
    question="Como obter a taxa SELIC atual?"
    answer="GET /api/v2/prime-rate?country=brazil retorna SELIC atual e histórico."
    relatedEndpoints={[
  { name: "Taxa de Juros", path: "/api/v2/prime-rate" },
  { name: "Países", path: "/api/v2/prime-rate/available" }
]}
    codeExample={`const selic = await client.primeRate.retrieve({ country: 'brazil' });
console.log(selic.primeRate[0].value);`}
    note="Histórico: ?start=01/01/2020&end=31/12/2024. COPOM define a cada 45 dias."
  />
</DocsQuickInfo>





## Swagger Documentation

# Brapi - API do Mercado Financeiro Brasileiro - /api/v2/prime-rate

Single endpoint documentation for /api/v2/prime-rate

## Base URLs

- `https://brapi.dev` - Servidor principal da API Brapi
- `http://localhost:3000` - Servidor local para desenvolvimento

## GET /api/v2/prime-rate

**Summary:** Buscar Taxa Básica de Juros (SELIC) de um País por um Período Determinado

Obtenha informações atualizadas sobre a taxa básica de juros (SELIC) de um país por um período determinado.

### Funcionalidades:

*   **Seleção por País:** Especifique o país desejado usando o parâmetro `country` (padrão: brazil).
*   **Período Customizado:** Defina datas de início e fim com `start` e `end` para consultar um intervalo específico.
*   **Ordenação:** Ordene os resultados por data ou valor com os parâmetros `sortBy` e `sortOrder`.
*   **Dados Históricos:** Solicite o histórico completo ou apenas o valor mais recente com o parâmetro `historical`.

### Autenticação:

Requer token de autenticação via `token` (query) ou `Authorization` (header).

### Exemplo de Requisição:

**Taxa de juros do Brasil entre dezembro/2021 e janeiro/2022:**

```bash
curl -X GET "https://brapi.dev/api/v2/prime-rate?country=brazil&start=01/12/2021&end=01/01/2022&sortBy=date&sortOrder=desc&token=SEU_TOKEN"
```

**Tags:** Taxa de Juros

### Parameters

- **country** (query): **Opcional.** O país do qual você deseja obter informações sobre a taxa básica de juros. Por padrão, o país é definido como brazil. Você pode consultar a lista de países disponíveis através do endpoint `/api/v2/prime-rate/available`.
- **historical** (query): **Opcional.** Define se os dados históricos serão retornados. Se definido como `true`, retorna a série histórica completa. Se `false` (padrão) ou omitido, retorna apenas o valor mais recente.
- **start** (query): **Opcional.** Data inicial do período para busca no formato DD/MM/YYYY. Útil quando `historical=true` para restringir o período da série histórica.
- **end** (query): **Opcional.** Data final do período para busca no formato DD/MM/YYYY. Por padrão é a data atual. Útil quando `historical=true` para restringir o período da série histórica.
- **sortBy** (query): **Opcional.** Campo pelo qual os resultados serão ordenados. Por padrão, ordena por `date` (data).
- **sortOrder** (query): **Opcional.** Define se a ordenação será crescente (`asc`) ou decrescente (`desc`). Por padrão, é `desc` (decrescente).
- **undefined** (undefined)

### Responses

#### 200

**Sucesso.** Retorna os dados da taxa básica de juros (SELIC) conforme os parâmetros fornecidos.

#### 400

**Bad Request.** A requisição está malformada ou um dos parâmetros fornecidos é inválido.

**Example Response:**

```json
{
  "error": true,
  "message": "Something went wrong while fetching the data"
}
```

#### 401

#### 417

**Expectation Failed.** Um valor de parâmetro fornecido é inválido ou não está disponível.

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


### PrimeRateEntry

Representa um registro individual de taxa básica de juros (SELIC) para uma data específica.

**Properties:**

- **date** (string)
  Data do registro no formato DD/MM/YYYY.

- **value** (string)
  Valor da taxa básica de juros (SELIC) para a data correspondente.

- **epochDate** (integer, int64)
  Timestamp em milissegundos (formato epoch) correspondente à data do registro.


### PrimeRateResponse

Resposta principal do endpoint `/api/v2/prime-rate`.

**Properties:**

- **prime-rate** (array)
  Array contendo os registros históricos de taxa básica de juros (SELIC) para o país e período solicitados.
  Array items:
    Reference to: **PrimeRateEntry**


