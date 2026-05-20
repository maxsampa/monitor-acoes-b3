# Cotação, Dividendos e Dados Financeiros
URL: /docs/acoes.mdx

Endpoints para consulta de dados relacionados a ativos negociados na B3, como Ações, Fundos Imobiliários (FIIs), BDRs, ETFs e Índices (ex: IBOVESPA). Permite buscar cotações atuais, dados históricos, informações fundamentalistas (via módulos) e listagens de ativos disponíveis.

***

title: Cotação, Dividendos e Dados Financeiros
description: >-
Endpoints para consulta de dados relacionados a ativos negociados na B3, como
Ações, Fundos Imobiliários (FIIs), BDRs, ETFs e Índices (ex: IBOVESPA).
Permite buscar cotações atuais, dados históricos, informações fundamentalistas
(via módulos) e listagens de ativos disponíveis.
full: true
keywords: brapi, api, documentação, ações
openGraph:
title: Cotação, Dividendos e Dados Financeiros
description: >-
Endpoints para consulta de dados relacionados a ativos negociados na B3,
como Ações, Fundos Imobiliários (FIIs), BDRs, ETFs e Índices (ex: IBOVESPA).
Permite buscar cotações atuais, dados históricos, informações
fundamentalistas (via módulos) e listagens de ativos disponíveis.
type: website
locale: pt\_BR
lastUpdated: '2025-04-28T01:22:35.251Z'
lang: pt-BR
\_openapi:
method: GET
route: /api/quote/{tickers}
toc:

* depth: 2
  title: Dados de Ações e Ativos Financeiros
  url: '#buscar-cotação-detalhada-de-ativos-financeiros'
  structuredData:
  headings:
  * content: Dados de Ações e Ativos Financeiros
    id: buscar-cotação-detalhada-de-ativos-financeiros
    contents:
  * content: >
    Este endpoint é a principal forma de obter informações detalhadas
    sobre um ou mais ativos financeiros (ações, FIIs, ETFs, BDRs, índices)
    listados na B3, identificados pelos seus respectivos **tickers**.

    ### Funcionalidades Principais:

    * **Cotação Atual:** Retorna o preço mais recente, variação diária,
      máximas, mínimas, volume, etc.

    * **Dados Históricos:** Permite solicitar séries históricas de
      preços usando os parâmetros `range` e `interval`.

    * **Dados Fundamentalistas:** Opcionalmente, inclui dados
      fundamentalistas básicos (P/L, LPA) com o parâmetro
      `fundamental=true`.

    * **Dividendos:** Opcionalmente, inclui histórico de dividendos e
      JCP com `dividends=true`.

    * **Módulos Adicionais:** Permite requisitar conjuntos de dados
      financeiros mais aprofundados através do parâmetro `modules` (veja
      detalhes abaixo).

    ### Autenticação:

    É **obrigatório** fornecer um token de autenticação válido, seja via
    query parameter `token` ou via header `Authorization: Bearer
      seu_token`.

    ### 🧪 Ações de Teste (Sem Autenticação):

    Para facilitar o desenvolvimento e teste, as seguintes **4 ações têm
    acesso irrestrito** e **não requerem autenticação**:

    * **PETR4** (Petrobras PN)

    * **MGLU3** (Magazine Luiza ON)

    * **VALE3** (Vale ON)

    * **ITUB4** (Itaú Unibanco PN)

    **Importante:** Você pode consultar essas ações sem token e com acesso
    a todos os recursos (históricos, módulos, dividendos). Porém, se
    misturar essas ações com outras na mesma requisição, a autenticação
    será obrigatória.

    ### Exemplos de Requisição:

    **1. Cotação simples de PETR4 e VALE3 (ações de teste - sem token):**

    ```bash

    curl -X GET "https://brapi.dev/api/quote/PETR4,VALE3"

    ```

    **2. Cotação de MGLU3 com dados históricos do último mês (ação de
    teste - sem token):**

    ```bash

    curl -X GET
    "https://brapi.dev/api/quote/MGLU3?range=1mo&interval=1d"

    ```

    **3. Cotação de ITUB4 incluindo dividendos e dados fundamentalistas
    (ação de teste - sem token):**

    ```bash

    curl -X GET
    "https://brapi.dev/api/quote/ITUB4?fundamental=true&dividends=true"

    ```

    **4. Cotação de WEGE3 com Resumo da Empresa e Balanço Patrimonial
    Anual (via módulos - requer token):**

    ```bash

    curl -X GET
    "https://brapi.dev/api/quote/WEGE3?modules=summaryProfile,balanceSheetHistory&token=SEU_TOKEN"

    ```

    **5. Exemplo de requisição mista (requer token):**

    ```bash

    curl -X GET
    "https://brapi.dev/api/quote/PETR4,BBAS3?token=SEU_TOKEN"

    ```

    *Nota: Como BBAS3 não é uma ação de teste, toda a requisição requer
    autenticação, mesmo contendo PETR4.*

    ### Parâmetro `modules` (Detalhado):

    O parâmetro `modules` é extremamente poderoso para enriquecer a
    resposta com dados financeiros detalhados. Você pode solicitar um ou
    mais módulos, separados por vírgula.

    **Módulos Disponíveis:**

    * `summaryProfile`: Informações cadastrais da empresa (endereço,
      setor, descrição do negócio, website, número de funcionários).

    * `balanceSheetHistory`: Histórico **anual** do Balanço Patrimonial.

    * `balanceSheetHistoryQuarterly`: Histórico **trimestral** do
      Balanço Patrimonial.

    * `defaultKeyStatistics`: Principais estatísticas da empresa (Valor
      de Mercado, P/L, ROE, Dividend Yield, etc.) - **TTM (Trailing Twelve
      Months)**.

    * `defaultKeyStatisticsHistory`: Histórico **anual** das Principais
      Estatísticas.

    * `defaultKeyStatisticsHistoryQuarterly`: Histórico **trimestral**
      das Principais Estatísticas.

    * `incomeStatementHistory`: Histórico **anual** da Demonstração do
      Resultado do Exercício (DRE).

    * `incomeStatementHistoryQuarterly`: Histórico **trimestral** da
      Demonstração do Resultado do Exercício (DRE).

    * `financialData`: Dados financeiros selecionados (Receita, Lucro
      Bruto, EBITDA, Dívida Líquida, Fluxo de Caixa Livre, Margens) - **TTM
      (Trailing Twelve Months)**.

    * `financialDataHistory`: Histórico **anual** dos Dados Financeiros.

    * `financialDataHistoryQuarterly`: Histórico **trimestral** dos
      Dados Financeiros.

    * `valueAddedHistory`: Histórico **anual** da Demonstração do Valor
      Adicionado (DVA).

    * `valueAddedHistoryQuarterly`: Histórico **trimestral** da
      Demonstração do Valor Adicionado (DVA).

    * `cashflowHistory`: Histórico **anual** da Demonstração do Fluxo de
      Caixa (DFC).

    * `cashflowHistoryQuarterly`: Histórico **trimestral** da
      Demonstração do Fluxo de Caixa (DFC).

    **Exemplo de Uso do `modules`:**

    Para obter a cotação de BBDC4 junto com seu DRE trimestral e Fluxo de
    Caixa anual:

    ```bash

    curl -X GET
    "https://brapi.dev/api/quote/BBDC4?modules=incomeStatementHistoryQuarterly,cashflowHistory&token=SEU_TOKEN"

    ```

    ### Resposta:

    A resposta é um objeto JSON contendo a chave `results`, que é um
    array. Cada elemento do array corresponde a um ticker solicitado e
    contém os dados da cotação e os módulos adicionais requisitados.

    * **Sucesso (200 OK):** Retorna os dados conforme solicitado.

    * **Bad Request (400 Bad Request):** Ocorre se um parâmetro for
      inválido (ex: `range=invalid`) ou se a formatação estiver incorreta.

    * **Unauthorized (401 Unauthorized):** Token inválido ou ausente.

    * **Payment Required (402 Payment Required):** Limite de requisições
      do plano atual excedido.

    * **Not Found (404 Not Found):** Um ou mais tickers solicitados não
      foram encontrados.
      heading: buscar-cotação-detalhada-de-ativos-financeiros

***

Endpoints para consulta de dados relacionados a ativos negociados na B3, como
**Ações**, **Fundos Imobiliários (FIIs)**, **BDRs**, **ETFs** e **Índices** (ex:
IBOVESPA).

Permite buscar cotações atuais, dados históricos, informações fundamentalistas
(via módulos) e listagens de ativos disponíveis.

<DocsQuickInfo>
  <Callout type="info" title="Fontes de Dados">
    **B3** para cotações, **CVM** para demonstrativos financeiros (BP, DRE, DFC, DVA), **BCB** para indicadores econômicos.
  </Callout>

  <AnswerBox
    question="Como obter a cotação de uma ação?"
    answer="GET /api/quote/PETR4 retorna preço, variação e volume. Sem token: PETR4, VALE3, MGLU3, ITUB4."
    relatedEndpoints={[
  { name: "Cotação", path: "/api/quote/{tickers}" },
  { name: "Lista", path: "/api/quote/list" }
]}
    codeExample={`const quote = await client.quote.retrieve('PETR4');
console.log(quote.results[0].regularMarketPrice);`}
    note="Múltiplas: /api/quote/PETR4,VALE3. Módulos: ?modules=summaryProfile"
  />
</DocsQuickInfo>





## Swagger Documentation

# Brapi - API do Mercado Financeiro Brasileiro - /api/quote/{tickers}

Single endpoint documentation for /api/quote/{tickers}

## Base URLs

- `https://brapi.dev` - Servidor principal da API Brapi
- `http://localhost:3000` - Servidor local para desenvolvimento

## GET /api/quote/{tickers}

**Summary:** Buscar Cotação Detalhada de Ativos Financeiros

Este endpoint é a principal forma de obter informações detalhadas sobre um ou mais ativos financeiros (ações, FIIs, ETFs, BDRs, índices) listados na B3, identificados pelos seus respectivos **tickers**.

### Funcionalidades Principais:

*   **Cotação Atual:** Retorna o preço mais recente, variação diária, máximas, mínimas, volume, etc.
*   **Dados Históricos:** Permite solicitar séries históricas de preços usando os parâmetros `range` e `interval`.
*   **Dados Fundamentalistas:** Opcionalmente, inclui dados fundamentalistas básicos (P/L, LPA) com o parâmetro `fundamental=true`.
*   **Dividendos:** Opcionalmente, inclui histórico de dividendos e JCP com `dividends=true`.
*   **Módulos Adicionais:** Permite requisitar conjuntos de dados financeiros mais aprofundados através do parâmetro `modules` (veja detalhes abaixo).

### 🧪 Ações de Teste (Sem Autenticação):

Para facilitar o desenvolvimento e teste, as seguintes **4 ações têm acesso irrestrito** e **não requerem autenticação**:

*   **PETR4** (Petrobras PN)
*   **MGLU3** (Magazine Luiza ON)  
*   **VALE3** (Vale ON)
*   **ITUB4** (Itaú Unibanco PN)

**Importante:** Você pode consultar essas ações sem token e com acesso a todos os recursos (históricos, módulos, dividendos). Porém, se misturar essas ações com outras na mesma requisição, a autenticação será obrigatória.

### Autenticação:

Para **outras ações** (além das 4 de teste), é **obrigatório** fornecer um token de autenticação válido, seja via query parameter `token` ou via header `Authorization: Bearer seu_token`.

### Exemplos de Requisição:

**1. Cotação simples de PETR4 e VALE3 (ações de teste - sem token):**

```bash
curl -X GET "https://brapi.dev/api/quote/PETR4,VALE3"
```

**2. Cotação de MGLU3 com dados históricos do último mês (ação de teste - sem token):**

```bash
curl -X GET "https://brapi.dev/api/quote/MGLU3?range=1mo&interval=1d"
```

**3. Cotação de ITUB4 incluindo dividendos e dados fundamentalistas (ação de teste - sem token):**

```bash
curl -X GET "https://brapi.dev/api/quote/ITUB4?fundamental=true&dividends=true"
```

**4. Cotação de WEGE3 com Resumo da Empresa e Balanço Patrimonial Anual (via módulos - requer token):**

```bash
curl -X GET "https://brapi.dev/api/quote/WEGE3?modules=summaryProfile,balanceSheetHistory&token=SEU_TOKEN"
```

**5. Exemplo de requisição mista (requer token):**

```bash
curl -X GET "https://brapi.dev/api/quote/PETR4,BBAS3?token=SEU_TOKEN"
```

*Nota: Como BBAS3 não é uma ação de teste, toda a requisição requer autenticação, mesmo contendo PETR4.*

### Parâmetro `modules` (Detalhado):

O parâmetro `modules` é extremamente poderoso para enriquecer a resposta com dados financeiros detalhados. Você pode solicitar um ou mais módulos, separados por vírgula.

**Módulos Disponíveis:**

*   `summaryProfile`: Informações cadastrais da empresa (endereço, setor, descrição do negócio, website, número de funcionários).
*   `balanceSheetHistory`: Histórico **anual** do Balanço Patrimonial.
*   `balanceSheetHistoryQuarterly`: Histórico **trimestral** do Balanço Patrimonial.
*   `defaultKeyStatistics`: Principais estatísticas da empresa (Valor de Mercado, P/L, ROE, Dividend Yield, etc.) - **TTM (Trailing Twelve Months)**.
*   `defaultKeyStatisticsHistory`: Histórico **anual** das Principais Estatísticas.
*   `defaultKeyStatisticsHistoryQuarterly`: Histórico **trimestral** das Principais Estatísticas.
*   `incomeStatementHistory`: Histórico **anual** da Demonstração do Resultado do Exercício (DRE).
*   `incomeStatementHistoryQuarterly`: Histórico **trimestral** da Demonstração do Resultado do Exercício (DRE).
*   `financialData`: Dados financeiros selecionados (Receita, Lucro Bruto, EBITDA, Dívida Líquida, Fluxo de Caixa Livre, Margens) - **TTM (Trailing Twelve Months)**.
*   `financialDataHistory`: Histórico **anual** dos Dados Financeiros.
*   `financialDataHistoryQuarterly`: Histórico **trimestral** dos Dados Financeiros.
*   `valueAddedHistory`: Histórico **anual** da Demonstração do Valor Adicionado (DVA).
*   `valueAddedHistoryQuarterly`: Histórico **trimestral** da Demonstração do Valor Adicionado (DVA).
*   `cashflowHistory`: Histórico **anual** da Demonstração do Fluxo de Caixa (DFC).
*   `cashflowHistoryQuarterly`: Histórico **trimestral** da Demonstração do Fluxo de Caixa (DFC).

**Exemplo de Uso do `modules`:**

Para obter a cotação de BBDC4 junto com seu DRE trimestral e Fluxo de Caixa anual:

```bash
curl -X GET "https://brapi.dev/api/quote/BBDC4?modules=incomeStatementHistoryQuarterly,cashflowHistory&token=SEU_TOKEN"
```

### Resposta:

A resposta é um objeto JSON contendo a chave `results`, que é um array. Cada elemento do array corresponde a um ticker solicitado e contém os dados da cotação e os módulos adicionais requisitados.

*   **Sucesso (200 OK):** Retorna os dados conforme solicitado.
*   **Bad Request (400 Bad Request):** Ocorre se um parâmetro for inválido (ex: `range=invalid`) ou se a formatação estiver incorreta.
*   **Unauthorized (401 Unauthorized):** Token inválido ou ausente.
*   **Payment Required (402 Payment Required):** Limite de requisições do plano atual excedido.
*   **Not Found (404 Not Found):** Um ou mais tickers solicitados não foram encontrados.


**Tags:** Ações

### Parameters

- **tickers** (path) *required*: **Obrigatório.** Um ou mais tickers de ativos financeiros (ações, FIIs, índices, etc.) que você deseja consultar. 

*   **Múltiplos Tickers:** Separe-os por vírgula (`,`).
*   **Exemplos:** `PETR4`, `ITSA4,MGLU3`, `^BVSP` (para o índice Ibovespa).
- **undefined** (undefined)
- **range** (query): **Opcional.** Define o período para os dados históricos de preço (`historicalDataPrice`). Se omitido, apenas a cotação mais recente é retornada (a menos que `interval` seja usado).

**Valores Possíveis:**

*   `1d`: Último dia de pregão (intraday se `interval` for minutos/horas).
*   `5d`: Últimos 5 dias.
*   `1mo`: Último mês.
*   `3mo`: Últimos 3 meses.
*   `6mo`: Últimos 6 meses.
*   `1y`: Último ano.
*   `2y`: Últimos 2 anos.
*   `5y`: Últimos 5 anos.
*   `10y`: Últimos 10 anos.
*   `ytd`: Desde o início do ano atual (Year-to-Date).
*   `max`: Todo o período histórico disponível.
- **interval** (query): **Opcional.** Define a granularidade (intervalo) dos dados históricos de preço (`historicalDataPrice`). Requer que `range` também seja especificado.

**Valores Possíveis:**

*   `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`: Intervalos intraday (minutos/horas). **Atenção:** Disponibilidade pode variar conforme o `range` e o ativo.
*   `1d`: Diário (padrão se `range` for especificado e `interval` omitido).
*   `5d`: 5 dias.
*   `1wk`: Semanal.
*   `1mo`: Mensal.
*   `3mo`: Trimestral.
- **fundamental** (query): **Opcional.** Booleano (`true` ou `false`). Se `true`, inclui dados fundamentalistas básicos na resposta, como Preço/Lucro (P/L) e Lucro Por Ação (LPA). 

**Nota:** Para dados fundamentalistas mais completos, utilize o parâmetro `modules`.
- **dividends** (query): **Opcional.** Booleano (`true` ou `false`). Se `true`, inclui informações sobre dividendos e JCP (Juros sobre Capital Próprio) pagos historicamente pelo ativo na chave `dividendsData`.
- **modules** (query): **Opcional.** Uma lista de módulos de dados adicionais, separados por vírgula (`,`), para incluir na resposta. Permite buscar dados financeiros detalhados.

**Exemplos:**

*   `modules=summaryProfile` (retorna perfil da empresa)
*   `modules=balanceSheetHistory,incomeStatementHistory` (retorna histórico anual do BP e DRE)

Veja a descrição principal do endpoint para a lista completa de módulos e seus conteúdos.

### Responses

#### 200

**Sucesso.** A requisição foi bem-sucedida e os dados dos ativos solicitados foram retornados. A estrutura da resposta inclui um array `results` com os detalhes de cada ativo.

**Example Response:**

```json
{
  "results": [
    {
      "currency": "BRL",
      "marketCap": 416355902930,
      "shortName": "PETROBRAS   PN  EDJ N2",
      "longName": "Petróleo Brasileiro S.A. - Petrobras",
      "regularMarketChange": 0.17,
      "regularMarketChangePercent": 0.5499999999999999,
      "regularMarketTime": "2025-08-29T20:07:36.000Z",
      "regularMarketPrice": 31.1,
      "regularMarketDayHigh": 31.35,
      "regularMarketDayRange": "30.85 - 31.35",
      "regularMarketDayLow": 30.85,
      "regularMarketVolume": 27631700,
      "regularMarketPreviousClose": 30.93,
      "regularMarketOpen": 30.54,
      "fiftyTwoWeekRange": "28.86 - 40.76",
      "fiftyTwoWeekLow": 28.86,
      "fiftyTwoWeekHigh": 40.76,
      "symbol": "PETR4",
      "logourl": "https://icons.brapi.dev/icons/PETR4.svg",
      "usedInterval": "1d",
      "usedRange": "5d",
      "historicalDataPrice": [
        {
          "date": 1756126800,
          "open": 30.47,
          "high": 30.78,
          "low": 30.42,
          "close": 30.65,
          "volume": 21075300,
          "adjustedClose": 30.65
        },
        {
          "date": 1756213200,
          "open": 30.48,
          "high": 30.58,
          "low": 30.23,
          "close": 30.43,
          "volume": 21789700,
          "adjustedClose": 30.43
        },
        {
          "date": 1756299600,
          "open": 30.45,
          "high": 30.68,
          "low": 30.36,
          "close": 30.66,
          "volume": 16349100,
          "adjustedClose": 30.66
        },
        {
          "date": 1756386000,
          "open": 30.78,
          "high": 31.13,
          "low": 30.71,
          "close": 30.93,
          "volume": 25802500,
          "adjustedClose": 30.93
        },
        {
          "date": 1756472400,
          "open": 30.93,
          "high": 31.35,
          "low": 30.85,
          "close": 31.1,
          "volume": 27713400,
          "adjustedClose": 31.1
        }
      ],
      "validRanges": [
        "1d",
        "2d",
        "5d",
        "7d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max"
      ],
      "validIntervals": [
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo"
      ],
      "balanceSheetHistory": [
        {
          "symbol": "PETR4",
          "type": "yearly",
          "endDate": "2024-12-31",
          "cash": 20254000000,
          "shortTermInvestments": 26397000000,
          "netReceivables": 22080000000,
          "inventory": 41550000000,
          "otherCurrentAssets": 12756000000,
          "totalCurrentAssets": 135212000000,
          "longTermInvestments": 4081000000,
          "propertyPlantEquipment": 843917000000,
          "otherAssets": 989585000000,
          "totalAssets": 1124797000000,
          "accountsPayable": 37659000000,
          "shortLongTermDebt": 68783000000,
          "otherCurrentLiab": 4418000000,
          "longTermDebt": 304684000000,
          "otherLiab": 3284000000,
          "totalCurrentLiabilities": 194808000000,
          "totalLiab": 1124797000000,
          "commonStock": 205432000000,
          "retainedEarnings": null,
          "treasuryStock": null,
          "otherStockholderEquity": -2457000000,
          "totalStockholderEquity": 367514000000,
          "netTangibleAssets": null,
          "goodWill": null,
          "intangibleAssets": 13961000000,
          "deferredLongTermAssetCharges": null,
          "deferredLongTermLiab": 9100000000,
          "minorityInterest": 1508000000,
          "capitalSurplus": null,
          "taxesToRecover": 12175000000,
          "longTermAssets": 989585000000,
          "longTermRealizableAssets": 127626000000,
          "longTermReceivables": 7777000000,
          "longTermDeferredTaxes": 28011000000,
          "otherNonCurrentAssets": 88233000000,
          "nonCurrentAssets": 1359748000000,
          "provisions": 15501000000,
          "shareholdersEquity": 367514000000,
          "realizedShareCapital": 205432000000,
          "capitalReserves": -2457000000,
          "profitReserves": 95193000000,
          "otherComprehensiveResults": 67838000000,
          "currentLiabilities": 194808000000,
          "socialAndLaborObligations": 9336000000,
          "providers": 37659000000,
          "taxObligations": 8671000000,
          "loansAndFinancing": 68783000000,
          "leaseFinancing": 52896000000,
          "otherObligations": 3256000000,
          "otherCurrentLiabilities": 4418000000,
          "nonCurrentLiabilities": 562475000000,
          "longTermLoansAndFinancing": 304684000000,
          "longTermLeaseFinancing": 177145000000,
          "otherLongTermObligations": 3284000000,
          "longTermProvisions": 245407000000,
          "updatedAt": "2024-12-31"
        }
      ],
      "summaryProfile": {
        "symbol": "PETR4",
        "address1": "Avenida RepUblica do Chile, 65",
        "address2": "Centro",
        "address3": null,
        "city": "Rio De Janeiro",
        "state": "RJ",
        "zip": "20031-912",
        "country": "Brazil",
        "phone": "55 21 96940 2116",
        "fax": null,
        "website": "https://petrobras.com.br",
        "industry": "Oil & Gas Integrated",
        "industryKey": "oil-gas-integrated",
        "industryDisp": "Oil & Gas Integrated",
        "sector": "Energy",
        "sectorKey": "energy",
        "sectorDisp": "Energy",
        "longBusinessSummary": "Petróleo Brasileiro S.A. - Petrobras explores, produces, and sells oil and gas in Brazil and internationally. The company operates through Exploration and Production; Refining, Transportation and Marketing; and Gas and Power. It also engages in prospecting, drilling, refining, processing, trading, and transporting crude oil from producing onshore and offshore oil fields, and shale or other rocks, as well as oil products, natural gas, and other liquid hydrocarbons. The Exploration and Production segment explores, develops, and produces crude oil, natural gas liquids, and natural gas primarily for supplies to the domestic refineries. The Refining, Transportation and Marketing segment engages in the refining, logistics, transport, marketing, and trading of crude oil and oil products; exportation of ethanol; and extraction and processing of shale, as well as holding interests in petrochemical companies. The Gas and Power segment is involved in the logistic and trading of natural gas and electricity; transportation and trading of LNG; generation of electricity through thermoelectric power plants; holding interests in transportation and distribution of natural gas; and fertilizer production and natural gas processing business. In addition, the company produces biodiesel and its co-products, and ethanol; and distributes oil products. Further, it engages in research, development, production, transport, distribution, and trading of energy. Petróleo Brasileiro S.A. - Petrobras was incorporated in 1953 and is headquartered in Rio de Janeiro, Brazil.",
        "fullTimeEmployees": 45149,
        "companyOfficers": [],
        "twitter": null,
        "name": null,
        "startDate": null,
        "description": null,
        "updatedAt": "2024-01-09T23:54:52.487Z"
      },
      "financialData": {
        "symbol": "PETR4",
        "currentPrice": 35.5,
        "ebitda": 204234000000,
        "quickRatio": 0.23947,
        "currentRatio": 0.69408,
        "debtToEquity": 101.6198,
        "revenuePerShare": 38.08202,
        "returnOnAssets": 0.0329,
        "returnOnEquity": 0.1007,
        "earningsGrowth": -0.71767,
        "revenueGrowth": -0.05016,
        "grossMargins": 0.50213,
        "ebitdaMargins": 0.4161,
        "operatingMargins": 0.27953,
        "profitMargins": 0.0754,
        "totalCash": 20254000000,
        "totalCashPerShare": 1.57145,
        "totalDebt": 194808000000,
        "totalRevenue": 490829000000,
        "grossProfits": 246462000000,
        "operatingCashflow": 204037000000,
        "freeCashflow": 131674000000,
        "financialCurrency": "BRL",
        "updatedAt": "2025-03-14",
        "type": "ttm"
      },
      "priceEarnings": 5.180656660725292,
      "earningsPerShare": 6.0030727,
      "dividendsData": {
        "cashDividends": [
          {
            "assetIssued": "BRPETRACNPR6",
            "paymentDate": "2025-02-20T00:00:00.000Z",
            "rate": 0.66,
            "relatedTo": "1º Trimestre/2025",
            "approvedOn": null,
            "isinCode": "BRPETRACNPR6",
            "label": "JCP",
            "lastDatePrior": "2024-12-23T00:00:00.000Z",
            "remarks": ""
          },
          {
            "assetIssued": "BRPETRACNPR6",
            "paymentDate": "2024-12-19T00:00:00.000Z",
            "rate": 0.53,
            "relatedTo": "Dezembro/2024",
            "approvedOn": "2024-08-07T00:00:00.000Z",
            "isinCode": "BRPETRACNPR6",
            "label": "DIVIDENDO",
            "lastDatePrior": "2024-08-20T00:00:00.000Z",
            "remarks": ""
          }
        ],
        "stockDividends": [
          {
            "assetIssued": "BRPETRACNPR6",
            "factor": 2,
            "completeFactor": "2 para 1",
            "approvedOn": "2008-03-24T00:00:00.000Z",
            "isinCode": "BRPETRACNPR6",
            "label": "DESDOBRAMENTO",
            "lastDatePrior": "2008-03-24T00:00:00.000Z",
            "remarks": ""
          }
        ],
        "subscriptions": []
      }
    },
    {
      "currency": "BRL",
      "marketCap": 5470189898,
      "shortName": "MAGAZ LUIZA ON      NM",
      "longName": "Magazine Luiza S.A.",
      "regularMarketChange": 0.35,
      "regularMarketChangePercent": 4.4639999999999995,
      "regularMarketTime": "2025-08-29T20:07:54.000Z",
      "regularMarketPrice": 8.19,
      "regularMarketDayHigh": 8.4,
      "regularMarketDayRange": "7.68 - 8.4",
      "regularMarketDayLow": 7.68,
      "regularMarketVolume": 29307200,
      "regularMarketPreviousClose": 7.84,
      "regularMarketOpen": 6.97,
      "fiftyTwoWeekRange": "5.71 - 12.51",
      "fiftyTwoWeekLow": 5.71,
      "fiftyTwoWeekHigh": 12.51,
      "symbol": "MGLU3",
      "logourl": "https://icons.brapi.dev/icons/MGLU3.svg",
      "usedInterval": "1d",
      "usedRange": "5d",
      "historicalDataPrice": [
        {
          "date": 1756126800,
          "open": 6.96,
          "high": 7.24,
          "low": 6.93,
          "close": 7.12,
          "volume": 15853100,
          "adjustedClose": 7.12
        },
        {
          "date": 1756213200,
          "open": 7.07,
          "high": 7.24,
          "low": 6.98,
          "close": 7,
          "volume": 16124700,
          "adjustedClose": 7
        },
        {
          "date": 1756299600,
          "open": 6.97,
          "high": 7.18,
          "low": 6.88,
          "close": 7.18,
          "volume": 17737000,
          "adjustedClose": 7.18
        },
        {
          "date": 1756386000,
          "open": 7.2,
          "high": 7.97,
          "low": 7.2,
          "close": 7.84,
          "volume": 43622600,
          "adjustedClose": 7.84
        },
        {
          "date": 1756472400,
          "open": 7.77,
          "high": 8.4,
          "low": 7.68,
          "close": 8.19,
          "volume": 29438600,
          "adjustedClose": 8.19
        }
      ],
      "validRanges": [
        "1d",
        "2d",
        "5d",
        "7d",
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y",
        "5y",
        "10y",
        "ytd",
        "max"
      ],
      "validIntervals": [
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo"
      ],
      "balanceSheetHistory": [
        {
          "symbol": "MGLU3",
          "type": "yearly",
          "endDate": "2024-12-31",
          "cash": 1827197000,
          "shortTermInvestments": 337894000,
          "netReceivables": 5833528000,
          "inventory": 7611132000,
          "otherCurrentAssets": 1986827000,
          "totalCurrentAssets": 19550824000,
          "longTermInvestments": 971862000,
          "propertyPlantEquipment": 5070097000,
          "otherAssets": 17761034000,
          "totalAssets": 37311858000,
          "accountsPayable": 10283119000,
          "shortLongTermDebt": 1402168000,
          "longTermDebt": 3179992000,
          "otherLiab": 3217524000,
          "totalCurrentLiabilities": 16710550000,
          "totalLiab": 37311858000,
          "commonStock": 13602498000,
          "retainedEarnings": null,
          "treasuryStock": null,
          "otherStockholderEquity": -3060268000,
          "totalStockholderEquity": 11319262000,
          "netTangibleAssets": null,
          "goodWill": null,
          "intangibleAssets": 4482287000,
          "deferredLongTermAssetCharges": null,
          "deferredLongTermLiab": 74242000,
          "capitalSurplus": null,
          "taxesToRecover": 1954246000,
          "longTermAssets": 17761034000,
          "longTermRealizableAssets": 7236788000,
          "longTermReceivables": 48553000,
          "longTermDeferredTaxes": 3285792000,
          "shareholdings": 971862000,
          "otherNonCurrentAssets": 3902443000,
          "nonCurrentAssets": 17747007000,
          "shareholdersEquity": 11319262000,
          "realizedShareCapital": 13602498000,
          "capitalReserves": -3060268000,
          "profitReserves": 905996000,
          "otherComprehensiveResults": -128964000,
          "currentLiabilities": 16710550000,
          "socialAndLaborObligations": 558572000,
          "providers": 10283119000,
          "nationalSuppliers": 10283119000,
          "taxObligations": 363003000,
          "loansAndFinancing": 1402168000,
          "otherObligations": 3272073000,
          "nonCurrentLiabilities": 9282046000,
          "longTermLoansAndFinancing": 3179992000,
          "otherLongTermObligations": 3217524000,
          "longTermProvisions": 1857353000,
          "profitsAndRevenuesToBeAppropriated": 952935000,
          "updatedAt": "2024-12-31"
        },
        {
          "symbol": "MGLU3",
          "type": "yearly",
          "endDate": "2023-12-31",
          "cash": 2593346000,
          "shortTermInvestments": 779072000,
          "netReceivables": 5885450000,
          "inventory": 7497299000,
          "otherCurrentAssets": 1608461000,
          "totalCurrentAssets": 20221163000,
          "longTermInvestments": 322516000,
          "propertyPlantEquipment": 5184576000,
          "otherAssets": 17233904000,
          "totalAssets": 37455067000,
          "accountsPayable": 9324072000,
          "shortLongTermDebt": 2954347000,
          "longTermDebt": 4400508000,
          "otherLiab": 3208852000,
          "totalCurrentLiabilities": 17408127000,
          "totalLiab": 37455067000,
          "commonStock": 12352498000,
          "retainedEarnings": null,
          "treasuryStock": null,
          "otherStockholderEquity": -3077861000,
          "totalStockholderEquity": 9610534000,
          "netTangibleAssets": null,
          "goodWill": null,
          "intangibleAssets": 4504807000,
          "deferredLongTermAssetCharges": null,
          "deferredLongTermLiab": 105122000,
          "capitalSurplus": null,
          "taxesToRecover": 1857535000,
          "longTermAssets": 17233904000,
          "longTermRealizableAssets": 7222005000,
          "longTermReceivables": 72691000,
          "longTermDeferredTaxes": 2836852000,
          "shareholdings": 322516000,
          "otherNonCurrentAssets": 4312462000,
          "nonCurrentAssets": 17302182000,
          "shareholdersEquity": 9610534000,
          "realizedShareCapital": 12352498000,
          "capitalReserves": -3077861000,
          "profitReserves": 457279000,
          "otherComprehensiveResults": -121382000,
          "currentLiabilities": 17408127000,
          "socialAndLaborObligations": 401867000,
          "providers": 9324072000,
          "nationalSuppliers": 9324072000,
          "taxObligations": 359971000,
          "loansAndFinancing": 2954347000,
          "otherObligations": 3152706000,
          "nonCurrentLiabilities": 10436406000,
          "longTermLoansAndFinancing": 4400508000,
          "otherLongTermObligations": 3208852000,
          "longTermProvisions": 1619166000,
          "profitsAndRevenuesToBeAppropriated": 1102758000,
          "updatedAt": "2023-12-31"
        }
      ],
      "summaryProfile": {
        "symbol": "MGLU3",
        "address1": "Rua Voluntários da, nº 1.465",
        "address2": "Centro",
        "address3": null,
        "city": "Franca",
        "state": "SP",
        "zip": null,
        "country": "Brazil",
        "phone": null,
        "fax": null,
        "website": "https://www.magazineluiza.com.br",
        "industry": "Specialty Retail",
        "industryKey": "specialty-retail",
        "industryDisp": "Specialty Retail",
        "sector": "Consumer Cyclical",
        "sectorKey": "consumer-cyclical",
        "sectorDisp": "Consumer Cyclical",
        "longBusinessSummary": "Magazine Luiza S.A. engages in the retail sale of consumer goods. It operates through Retail, Financial Operations, Insurance Operations, and Other Services segments. The company also grants credit and provides extended warranties for its products. In addition, it is involved in the provision of consortium management services; and e-commerce of perfumes, cosmetics, sports, and fashion products, as well as product delivery management and software development services. Further, the company provides integration, logistics, and technological solutions; and manages relation between merchants and marketplaces. The company was founded in 1957 and is headquartered in Franca, Brazil. Magazine Luiza S.A. operates as a subsidiary of LTD Administração e Participação S.A.",
        "fullTimeEmployees": null,
        "companyOfficers": [],
        "twitter": null,
        "name": null,
        "startDate": null,
        "description": null,
        "updatedAt": "2024-01-10T01:41:50.950Z"
      },
      "financialData": {
        "symbol": "MGLU3",
        "currentPrice": 9.6,
        "ebitda": 2895720000,
        "quickRatio": 0.12956,
        "currentRatio": 1.16997,
        "debtToEquity": 40.48108,
        "revenuePerShare": 51.47268,
        "returnOnAssets": 0.01203,
        "returnOnEquity": 0.03964,
        "earningsGrowth": 0.42651,
        "revenueGrowth": 0.02278,
        "grossMargins": 0.30567,
        "ebitdaMargins": 0.07613,
        "operatingMargins": 0.04108,
        "profitMargins": 0.0118,
        "totalCash": 1827197000,
        "totalCashPerShare": 2.47254,
        "totalDebt": 16710550000,
        "totalRevenue": 38038068000,
        "grossProfits": 11627256000,
        "operatingCashflow": 15835331000,
        "freeCashflow": 14544725000,
        "financialCurrency": "BRL",
        "updatedAt": "2025-03-14",
        "type": "ttm"
      },
      "priceEarnings": 15.656662206079142,
      "earningsPerShare": 0.5238851,
      "dividendsData": {
        "cashDividends": [
          {
            "assetIssued": "BRMGLUACNOR2",
            "paymentDate": "2022-05-06T00:00:00.000Z",
            "rate": 0.02,
            "relatedTo": "2º Trimestre/2022",
            "approvedOn": "2022-04-26T00:00:00.000Z",
            "isinCode": "BRMGLUACNOR2",
            "label": "JCP",
            "lastDatePrior": "2021-07-05T00:00:00.000Z",
            "remarks": ""
          },
          {
            "assetIssued": "BRMGLUACNOR2",
            "paymentDate": "2022-05-05T00:00:00.000Z",
            "rate": 0.02,
            "relatedTo": "2º Trimestre/2022",
            "approvedOn": "2021-06-29T00:00:00.000Z",
            "isinCode": "BRMGLUACNOR2",
            "label": "JCP",
            "lastDatePrior": "2021-07-04T00:00:00.000Z",
            "remarks": ""
          }
        ],
        "stockDividends": [
          {
            "assetIssued": "BRMGLUACNOR2",
            "factor": 0.1,
            "completeFactor": "1 para 10",
            "approvedOn": "2024-05-27T00:00:00.000Z",
            "isinCode": "BRMGLUACNOR2",
            "label": "GRUPAMENTO",
            "lastDatePrior": "2024-05-27T00:00:00.000Z",
            "remarks": ""
          }
        ],
        "subscriptions": []
      }
    }
  ],
  "requestedAt": "2025-08-30T15:53:07.499Z",
  "took": "0ms"
}
```

#### 400

**Bad Request.** A requisição foi malformada ou continha parâmetros inválidos. Verifique a sintaxe dos tickers e os valores dos parâmetros `range`, `interval`, `fundamental`, `dividends` e `modules`.

**Example Response:**

```json
{
  "error": true,
  "message": "Campo 'range' inválido. Ranges válidos: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max"
}
```

#### 401

#### 402

**Payment Required.** O limite de requisições associado ao seu token/plano foi atingido. Considere um upgrade ou aguarde a renovação do limite.

**Example Response:**

```json
{
  "error": true,
  "message": "Você atingiu o limite de requisições para o seu plano. Por favor, considere fazer um upgrade para um plano melhor em brapi.dev/dashboard"
}
```

#### 404

**Not Found.** Um ou mais tickers informados no path não correspondem a nenhum ativo conhecido pela API.

**Example Response:**

```json
{
  "error": true,
  "message": "Não encontramos a ação G3X"
}
```

## Schemas

The following schemas are used by this endpoint:

### BalanceSheetEntry

Representa os dados de um Balanço Patrimonial para um período específico (anual ou trimestral).

**Properties:**

- **symbol** (string)
  Ticker do ativo ao qual o balanço se refere.

- **type** (string) - Options: `yearly`, `quarterly`
  Indica a periodicidade do balanço: `yearly` (anual) ou `quarterly` (trimestral).

- **endDate** (string, date)
  Data de término do período fiscal ao qual o balanço se refere (YYYY-MM-DD).

- **cash** (number, int64) *(nullable)*
  Caixa e equivalentes de caixa.

- **shortTermInvestments** (number, int64) *(nullable)*
  Aplicações financeiras de curto prazo.

- **netReceivables** (number, int64) *(nullable)*
  Contas a receber líquidas (clientes).

- **inventory** (number, int64) *(nullable)*
  Estoques.

- **otherCurrentAssets** (number, int64) *(nullable)*
  Outros ativos circulantes.

- **totalCurrentAssets** (number, int64) *(nullable)*
  Total do ativo circulante.

- **longTermInvestments** (number, int64) *(nullable)*
  Investimentos de longo prazo.

- **propertyPlantEquipment** (number, int64) *(nullable)*
  Imobilizado (propriedades, instalações e equipamentos).

- **otherAssets** (number, int64) *(nullable)*
  Outros ativos não circulantes.

- **totalAssets** (number, int64) *(nullable)*
  Total do ativo.

- **accountsPayable** (number, int64) *(nullable)*
  Contas a pagar (fornecedores).

- **shortLongTermDebt** (number, int64) *(nullable)*
  Dívida de curto prazo (empréstimos e financiamentos circulantes).

- **otherCurrentLiab** (number, int64) *(nullable)*
  Outros passivos circulantes.

- **longTermDebt** (number, int64) *(nullable)*
  Dívida de longo prazo (empréstimos e financiamentos não circulantes).

- **otherLiab** (number, int64) *(nullable)*
  Outros passivos não circulantes.

- **totalCurrentLiabilities** (number, int64) *(nullable)*
  Total do passivo circulante.

- **totalLiab** (number, int64) *(nullable)*
  Total do passivo (circulante + não circulante).

- **commonStock** (number, int64) *(nullable)*
  Capital social realizado.

- **retainedEarnings** (number, int64) *(nullable)*
  Lucros/Prejuízos acumulados.

- **treasuryStock** (number, int64) *(nullable)*
  Ações em tesouraria.

- **otherStockholderEquity** (number, int64) *(nullable)*
  Outros componentes do patrimônio líquido.

- **totalStockholderEquity** (number, int64) *(nullable)*
  Total do patrimônio líquido.

- **netTangibleAssets** (number, int64) *(nullable)*
  Ativos tangíveis líquidos (Ativo Total - Intangíveis - Passivo Total).

- **goodWill** (number, int64) *(nullable)*
  Ágio por expectativa de rentabilidade futura (Goodwill).

- **intangibleAssets** (number, int64) *(nullable)*
  Ativos intangíveis (marcas, patentes, etc.).

- **deferredLongTermAssetCharges** (number, int64) *(nullable)*
  Encargos diferidos de ativos de longo prazo.

- **deferredLongTermLiab** (number, int64) *(nullable)*
  Passivos fiscais diferidos (longo prazo).

- **minorityInterest** (number, int64) *(nullable)*
  Participação de não controladores (no patrimônio líquido).

- **capitalSurplus** (number, int64) *(nullable)*
  Reservas de capital.

- **taxesToRecover** (number, int64) *(nullable)*
  Impostos a recuperar.

- **longTermAssets** (number, int64) *(nullable)*
  Total do ativo não circulante (agregado).

- **longTermRealizableAssets** (number, int64) *(nullable)*
  Ativo realizável a longo prazo.

- **longTermReceivables** (number, int64) *(nullable)*
  Contas a receber de longo prazo.

- **longTermDeferredTaxes** (number, int64) *(nullable)*
  Tributos diferidos (Ativo Não Circulante).

- **otherNonCurrentAssets** (number, int64) *(nullable)*
  Outros ativos não circulantes (detalhamento).

- **nonCurrentAssets** (number, int64) *(nullable)*
  Total do ativo não circulante (sinônimo de `longTermAssets`).

- **provisions** (number, int64) *(nullable)*
  Provisões (passivo).

- **shareholdersEquity** (number, int64) *(nullable)*
  Patrimônio líquido (sinônimo de `totalStockholderEquity`).

- **realizedShareCapital** (number, int64) *(nullable)*
  Capital social realizado (sinônimo de `commonStock`).

- **capitalReserves** (number, int64) *(nullable)*
  Reservas de capital (sinônimo de `capitalSurplus`).

- **profitReserves** (number, int64) *(nullable)*
  Reservas de lucros.

- **otherComprehensiveResults** (number, int64) *(nullable)*
  Outros resultados abrangentes.

- **currentLiabilities** (number, int64) *(nullable)*
  Total do passivo circulante (sinônimo de `totalCurrentLiabilities`).

- **socialAndLaborObligations** (number, int64) *(nullable)*
  Obrigações sociais e trabalhistas.

- **providers** (number, int64) *(nullable)*
  Fornecedores (sinônimo de `accountsPayable`).

- **taxObligations** (number, int64) *(nullable)*
  Obrigações fiscais (passivo circulante).

- **loansAndFinancing** (number, int64) *(nullable)*
  Empréstimos e financiamentos (circulante).

- **leaseFinancing** (number, int64) *(nullable)*
  Financiamento por arrendamento mercantil (circulante).

- **otherObligations** (number, int64) *(nullable)*
  Outras obrigações (circulante).

- **otherCurrentLiabilities** (number, int64) *(nullable)*
  Outros passivos circulantes (sinônimo de `otherCurrentLiab`).

- **nonCurrentLiabilities** (number, int64) *(nullable)*
  Total do passivo não circulante.

- **longTermLoansAndFinancing** (number, int64) *(nullable)*
  Empréstimos e financiamentos (não circulante).

- **longTermLeaseFinancing** (number, int64) *(nullable)*
  Financiamento por arrendamento mercantil (não circulante).

- **otherLongTermObligations** (number, int64) *(nullable)*
  Outras obrigações (passivo não circulante).

- **longTermProvisions** (number, int64) *(nullable)*
  Provisões (passivo não circulante).

- **updatedAt** (string, date) *(nullable)*
  Data da última atualização deste registro (YYYY-MM-DD).

- **financialAssets** (number, int64) *(nullable)*
  Ativos financeiros (agregado de instrumentos financeiros no ativo).

- **centralBankCompulsoryDeposit** (number, int64) *(nullable)*
  Depósitos compulsórios no Banco Central.

- **financialAssetsMeasuredAtFairValueThroughProfitOrLoss** (number, int64) *(nullable)*
  Ativos financeiros mensurados a valor justo por meio do resultado (FVTPL).

- **currentAndDeferredTaxes** (number, int64) *(nullable)*
  Tributos correntes e diferidos no ativo.

- **investments** (number, int64) *(nullable)*
  Investimentos (participações e outros).

- **financialAssetsMeasuredAtFairValueThroughOtherComprehensiveIncome** (number, int64) *(nullable)*
  Ativos financeiros mensurados a valor justo por outros resultados abrangentes (FVOCI).

- **financialAssetsAtAmortizedCost** (number, int64) *(nullable)*
  Ativos financeiros ao custo amortizado.

- **accountsReceivableFromClients** (number, int64) *(nullable)*
  Contas a receber de clientes (bruto).

- **otherAccountsReceivable** (number, int64) *(nullable)*
  Outras contas a receber.

- **biologicalAssets** (number, int64) *(nullable)*
  Ativos biológicos.

- **prepaidExpenses** (number, int64) *(nullable)*
  Despesas antecipadas.

- **longTermAccountsReceivableFromClients** (number, int64) *(nullable)*
  Contas a receber de clientes - longo prazo.

- **longTermInventory** (number, int64) *(nullable)*
  Estoques de longo prazo.

- **longTermBiologicalAssets** (number, int64) *(nullable)*
  Ativos biológicos de longo prazo.

- **longTermPrepaidExpenses** (number, int64) *(nullable)*
  Despesas antecipadas de longo prazo.

- **creditsWithRelatedParties** (number, int64) *(nullable)*
  Créditos com partes relacionadas.

- **shareholdings** (number, int64) *(nullable)*
  Participações societárias.

- **investmentProperties** (number, int64) *(nullable)*
  Propriedades para investimento.

- **otherLongTermReceivables** (number, int64) *(nullable)*
  Outros créditos/recebíveis de longo prazo.

- **creditsFromOperations** (number, int64) *(nullable)*
  Créditos oriundos de operações (instituições financeiras/seguradoras).

- **securitiesAndCreditsReceivable** (number, int64) *(nullable)*
  Títulos e créditos a receber.

- **otherValuesAndAssets** (number, int64) *(nullable)*
  Outros valores e bens.

- **compulsoryLoansAndDeposits** (number, int64) *(nullable)*
  Empréstimos e depósitos compulsórios.

- **deferredSellingExpenses** (number, int64) *(nullable)*
  Despesas de comercialização diferidas.

- **longTermFinancialInvestmentsMeasuredAtFairValueThroughIncome** (number, int64) *(nullable)*
  Investimentos financeiros de longo prazo mensurados a valor justo por meio do resultado.

- **financialInvestmentsMeasuredAtFairValueThroughOtherComprehensiveIncome** (number, int64) *(nullable)*
  Investimentos financeiros mensurados a valor justo por outros resultados abrangentes.

- **financialInvestmentsMeasuredAtAmortizedCost** (number, int64) *(nullable)*
  Investimentos financeiros mensurados ao custo amortizado.

- **intangibleAsset** (number, int64) *(nullable)*
  Ativo intangível (valor agregado).

- **deferredTaxes** (number, int64) *(nullable)*
  Tributos diferidos no ativo.

- **otherOperations** (number, int64) *(nullable)*
  Outras contas operacionais no ativo.

- **totalLiabilities** (number, int64) *(nullable)*
  Total do passivo.

- **financialLiabilitiesMeasuredAtFairValueThroughIncome** (number, int64) *(nullable)*
  Passivos financeiros mensurados a valor justo por meio do resultado.

- **financialLiabilitiesAtAmortizedCost** (number, int64) *(nullable)*
  Passivos financeiros ao custo amortizado.

- **taxLiabilities** (number, int64) *(nullable)*
  Obrigações fiscais (passivo).

- **otherLiabilities** (number, int64) *(nullable)*
  Outros passivos.

- **controllerShareholdersEquity** (number, int64) *(nullable)*
  Patrimônio líquido atribuível aos controladores.

- **nonControllingShareholdersEquity** (number, int64) *(nullable)*
  Participação dos não controladores no patrimônio líquido.

- **revaluationReserves** (number, int64) *(nullable)*
  Reservas de reavaliação.

- **accumulatedProfitsOrLosses** (number, int64) *(nullable)*
  Lucros ou prejuízos acumulados.

- **equityValuationAdjustments** (number, int64) *(nullable)*
  Ajustes de avaliação patrimonial.

- **cumulativeConversionAdjustments** (number, int64) *(nullable)*
  Ajustes acumulados de conversão.

- **nationalSuppliers** (number, int64) *(nullable)*
  Fornecedores nacionais.

- **foreignSuppliers** (number, int64) *(nullable)*
  Fornecedores estrangeiros.

- **loansAndFinancingInNationalCurrency** (number, int64) *(nullable)*
  Empréstimos e financiamentos em moeda nacional (circulante).

- **loansAndFinancingInForeignCurrency** (number, int64) *(nullable)*
  Empréstimos e financiamentos em moeda estrangeira (circulante).

- **debentures** (number, int64) *(nullable)*
  Debêntures (passivo circulante).

- **longTermLoansAndFinancingInNationalCurrency** (number, int64) *(nullable)*
  Empréstimos e financiamentos em moeda nacional (não circulante).

- **longTermLoansAndFinancingInForeignCurrency** (number, int64) *(nullable)*
  Empréstimos e financiamentos em moeda estrangeira (não circulante).

- **longTermDebentures** (number, int64) *(nullable)*
  Debêntures (passivo não circulante).

- **otherNonCurrentLiabilities** (number, int64) *(nullable)*
  Outros passivos não circulantes.

- **profitsAndRevenuesToBeAppropriated** (number, int64) *(nullable)*
  Lucros e receitas a apropriar.

- **debitsFromOperations** (number, int64) *(nullable)*
  Débitos oriundos de operações.

- **debitsFromInsuranceAndReinsurance** (number, int64) *(nullable)*
  Débitos de operações de seguros e resseguros.

- **debitsFromComplementaryPension** (number, int64) *(nullable)*
  Débitos de operações de previdência complementar.

- **thirdPartyDeposits** (number, int64) *(nullable)*
  Depósitos de terceiros.

- **technicalProvisions** (number, int64) *(nullable)*
  Provisões técnicas (seguradoras/previdência).

- **insuranceAndReinsurance** (number, int64) *(nullable)*
  Provisões/obrigações de seguros e resseguros.

- **complementaryPension** (number, int64) *(nullable)*
  Obrigações de previdência complementar.

- **capitalization** (number, int64) *(nullable)*
  Obrigações de capitalização.

- **otherDebits** (number, int64) *(nullable)*
  Outros débitos.

- **longTermLiabilities** (number, int64) *(nullable)*
  Total do passivo de longo prazo.

- **longTermAccountsPayable** (number, int64) *(nullable)*
  Fornecedores/contas a pagar de longo prazo.

- **longTermDebitsFromOperations** (number, int64) *(nullable)*
  Débitos de operações (longo prazo).

- **longTermTechnicalProvisions** (number, int64) *(nullable)*
  Provisões técnicas de longo prazo.

- **longTermInsuranceAndReinsurance** (number, int64) *(nullable)*
  Obrigações de seguros e resseguros de longo prazo.

- **longTermComplementaryPension** (number, int64) *(nullable)*
  Obrigações de previdência complementar de longo prazo.

- **longTermCapitalization** (number, int64) *(nullable)*
  Obrigações de capitalização de longo prazo.

- **otherLongTermProvisions** (number, int64) *(nullable)*
  Outras provisões de longo prazo.

- **debitsFromCapitalization** (number, int64) *(nullable)*
  Débitos de operações de capitalização.

- **debitsFromOtherOperations** (number, int64) *(nullable)*
  Débitos de outras operações.

- **otherProvisions** (number, int64) *(nullable)*
  Outras provisões (diversas).

- **advanceForFutureCapitalIncrease** (number, int64) *(nullable)*
  Adiantamento para futuro aumento de capital (AFAC).


### CashDividend

Detalhes sobre um pagamento de provento em dinheiro (Dividendo ou JCP).

**Properties:**

- **assetIssued** (string)
  Ticker do ativo que pagou o provento (ex: `ITSA4`). Pode incluir sufixos específicos relacionados ao evento.

- **paymentDate** (string, date-time) *(nullable)*
  Data efetiva em que o pagamento foi realizado (ou está previsto). Formato ISO 8601.

- **rate** (number, float)
  Valor bruto do provento pago por unidade do ativo (por ação, por cota).

- **relatedTo** (string) *(nullable)*
  Descrição do período ou evento ao qual o provento se refere (ex: `1º Trimestre/2023`, `Resultado 2022`).

- **approvedOn** (string, date-time)
  Data em que o pagamento do provento foi aprovado pela empresa. Pode ser uma estimativa em alguns casos. Formato ISO 8601.

- **isinCode** (string) *(nullable)*
  Código ISIN (International Securities Identification Number) do ativo relacionado ao provento.

- **label** (string)
  Tipo do provento em dinheiro. Geralmente `DIVIDENDO` ou `JCP` (Juros sobre Capital Próprio).

- **lastDatePrior** (string, date-time)
  Data Com (Ex-Date). Último dia em que era necessário possuir o ativo para ter direito a receber este provento. Pode ser uma estimativa. Formato ISO 8601.

- **remarks** (string) *(nullable)*
  Observações adicionais ou informações relevantes sobre o provento.


### CashflowEntry

Representa os dados de uma Demonstração do Fluxo de Caixa (DFC) para um período específico (anual ou trimestral).

**Properties:**

- **symbol** (string)
  Ticker do ativo ao qual a DFC se refere.

- **type** (string) - Options: `yearly`, `quarterly`
  Indica a periodicidade da DFC: `yearly` (anual) ou `quarterly` (trimestral).

- **endDate** (string, date)
  Data de término do período fiscal ao qual a DFC se refere (YYYY-MM-DD).

- **operatingCashFlow** (number, int64) *(nullable)*
  Fluxo de Caixa das Atividades Operacionais (FCO).

- **incomeFromOperations** (number, int64) *(nullable)*
  Caixa Gerado nas Operações (antes das variações de ativos/passivos).

- **netIncomeBeforeTaxes** (number, int64) *(nullable)*
  Lucro líquido antes dos impostos (base para reconciliação pelo método indireto).

- **adjustmentsToProfitOrLoss** (number, int64) *(nullable)*
  Ajustes ao lucro/prejuízo (depreciação, amortização, equivalência patrimonial, variações não caixa).

- **changesInAssetsAndLiabilities** (number, int64) *(nullable)*
  Variações em Ativos e Passivos Operacionais (Clientes, Estoques, Fornecedores, etc.).

- **otherOperatingActivities** (number, int64) *(nullable)*
  Outras Atividades Operacionais (Juros pagos/recebidos, Impostos pagos, etc.).

- **investmentCashFlow** (number, int64) *(nullable)*
  Fluxo de Caixa das Atividades de Investimento (FCI) (Compra/Venda de Imobilizado, Investimentos).

- **financingCashFlow** (number, int64) *(nullable)*
  Fluxo de Caixa das Atividades de Financiamento (FCF) (Captação/Pagamento de Empréstimos, Emissão/Recompra de Ações, Dividendos pagos).

- **exchangeVariationWithoutCash** (number, int64) *(nullable)*
  Variação cambial sem efeito caixa (ajuste de conversão).

- **foreignExchangeRateWithoutCash** (number, int64) *(nullable)*
  Efeito da Variação Cambial sobre o Caixa e Equivalentes.

- **increaseOrDecreaseInCash** (number, int64) *(nullable)*
  Aumento ou Redução Líquida de Caixa e Equivalentes (FCO + FCI + FCF + Variação Cambial).

- **initialCashBalance** (number, int64) *(nullable)*
  Saldo Inicial de Caixa e Equivalentes no início do período.

- **finalCashBalance** (number, int64) *(nullable)*
  Saldo Final de Caixa e Equivalentes no final do período.

- **cashGeneratedInOperations** (number, int64) *(nullable)*
  Caixa gerado nas operações (após variações no capital de giro).

- **updatedAt** (string, date)
  Data da última atualização deste registro específico na fonte de dados (YYYY-MM-DD).


### DefaultKeyStatisticsEntry

Representa um conjunto de principais indicadores e estatísticas financeiras para um período (TTM, anual ou trimestral).

**Properties:**

- **type** (string) - Options: `yearly`, `quarterly`, `ttm`
  Periodicidade dos dados: `yearly` (anual), `quarterly` (trimestral), `ttm` (Trailing Twelve Months - últimos 12 meses).

- **symbol** (string)
  Ticker do ativo ao qual as estatísticas se referem.

- **enterpriseValue** (number, float) *(nullable)*
  Valor da Firma (Enterprise Value - EV): Market Cap + Dívida Total - Caixa.

- **forwardPE** (number, float) *(nullable)*
  Preço / Lucro Projetado (Forward P/E): Preço da Ação / LPA estimado para o próximo período.

- **profitMargins** (number, float) *(nullable)*
  Margem de Lucro Líquida (Lucro Líquido / Receita Líquida). Geralmente em base TTM ou anual.

- **floatShares** (number, int64) *(nullable)*
  Ações em livre circulação (free float).

- **sharesOutstanding** (number, int64) *(nullable)*
  Número total de ações ordinárias em circulação.

- **heldPercentInsiders** (number, float) *(nullable)*
  Percentual de ações detidas por insiders (administradores, controladores).

- **heldPercentInstitutions** (number, float) *(nullable)*
  Percentual de ações detidas por instituições (fundos, investidores institucionais).

- **beta** (number, float) *(nullable)*
  Beta da ação (sensibilidade em relação ao mercado).

- **impliedSharesOutstanding** (number, int64) *(nullable)*
  Ações implícitas em circulação (considerando diluição/derivativos).

- **bookValue** (number, float) *(nullable)*
  Valor Patrimonial por Ação (VPA): Patrimônio Líquido / Ações em Circulação.

- **priceToBook** (number, float) *(nullable)*
  Preço sobre Valor Patrimonial (P/VP): Preço da Ação / VPA.

- **lastFiscalYearEnd** (string, date) *(nullable)*
  Data de encerramento do último ano fiscal (YYYY-MM-DD).

- **nextFiscalYearEnd** (string, date) *(nullable)*
  Data de encerramento do próximo ano fiscal (YYYY-MM-DD).

- **mostRecentQuarter** (string, date) *(nullable)*
  Data de término do trimestre mais recente considerado nos cálculos (YYYY-MM-DD).

- **earningsQuarterlyGrowth** (number, float) *(nullable)*
  Crescimento percentual do lucro líquido no último trimestre em relação ao mesmo trimestre do ano anterior (YoY).

- **earningsAnnualGrowth** (number, float) *(nullable)*
  Crescimento percentual do lucro líquido no último ano fiscal completo em relação ao ano anterior.

- **netIncomeToCommon** (number, int64) *(nullable)*
  Lucro Líquido atribuível aos acionistas ordinários (controladores).

- **trailingEps** (number, float) *(nullable)*
  Lucro Por Ação (LPA) dos Últimos 12 Meses (TTM).

- **forwardEps** (number, float) *(nullable)*
  Lucro Por Ação projetado (próximo período).

- **pegRatio** (number, float) *(nullable)*
  Índice PEG (P/E dividido pelo crescimento esperado dos lucros).

- **lastSplitFactor** (string) *(nullable)*
  Fator do último desdobramento/grupamento (ex.: 2:1, 1:10).

- **lastSplitDate** (number, int64) *(nullable)*
  Data do último desdobramento/grupamento (timestamp UNIX em segundos).

- **enterpriseToRevenue** (number, float) *(nullable)*
  Múltiplo EV/Receita (Enterprise Value / Receita Líquida TTM).

- **enterpriseToEbitda** (number, float) *(nullable)*
  Múltiplo EV/EBITDA (Enterprise Value / EBITDA TTM).

- **52WeekChange** (number, float) *(nullable)*
  Variação percentual do preço da ação nas últimas 52 semanas.

- **SandP52WeekChange** (number, float) *(nullable)*
  Variação percentual do índice S&P 500 nas últimas 52 semanas (para referência).

- **lastDividendValue** (number, float) *(nullable)*
  Valor do último dividendo ou JCP pago por ação.

- **lastDividendDate** (string, date) *(nullable)*
  Data de pagamento (ou 'Data Com') do último dividendo/JCP (YYYY-MM-DD).

- **dividendYield** (number, float) *(nullable)*
  Dividend Yield (provento anualizado sobre o preço atual).

- **ytdReturn** (number, float) *(nullable)*
  Retorno percentual do preço da ação desde o início do ano atual (Year-to-Date).

- **totalAssets** (number, int64) *(nullable)*
  Valor total dos ativos registrado no último balanço (anual ou trimestral).

- **updatedAt** (string, date) *(nullable)*
  Data da última atualização deste registro específico na fonte de dados (YYYY-MM-DD).


### DividendsData

Agrupa informações sobre proventos e eventos corporativos. Retornado quando `dividends=true` é solicitado.

**Properties:**

- **cashDividends** (array)
  Lista de proventos pagos em dinheiro (Dividendos e JCP).
  Array items:
    Reference to: **CashDividend**

- **stockDividends** (array)
  Lista de eventos corporativos (Desdobramento, Grupamento, Bonificação).
  Array items:
    Reference to: **StockDividend**

- **subscriptions** (array)
  Lista de eventos de subscrição de ações (estrutura não detalhada aqui).
  Array items:


### ErrorResponse

Schema padrão para respostas de erro da API.

**Properties:**

- **error** (boolean) *(required)*
  Indica se a requisição resultou em erro. Sempre `true` para este schema.

- **message** (string) *(required)*
  Mensagem descritiva do erro ocorrido.


### FinancialDataEntry

Representa um conjunto de dados e indicadores financeiros calculados para um período (TTM, anual ou trimestral).

**Properties:**

- **symbol** (string)
  Ticker do ativo ao qual os dados se referem.

- **currentPrice** (number, float) *(nullable)*
  Preço atual da ação (pode ser ligeiramente defasado).

- **targetHighPrice** (number, float) *(nullable)*
  Preço-alvo mais alto estimado por analistas.

- **targetLowPrice** (number, float) *(nullable)*
  Preço-alvo mais baixo estimado por analistas.

- **targetMeanPrice** (number, float) *(nullable)*
  Preço-alvo médio estimado por analistas.

- **targetMedianPrice** (number, float) *(nullable)*
  Preço-alvo mediano estimado por analistas.

- **recommendationMean** (number, float) *(nullable)*
  Média de recomendações dos analistas (1=Compra Forte, 5=Venda Forte).

- **recommendationKey** (string) *(nullable)*
  Resumo da recomendação (ex.: strong_buy, buy, hold, sell, strong_sell).

- **numberOfAnalystOpinions** (number, int32) *(nullable)*
  Número de opiniões de analistas consideradas.

- **ebitda** (number, int64) *(nullable)*
  Lucro Antes de Juros, Impostos, Depreciação e Amortização (LAJIDA ou EBITDA). Geralmente TTM.

- **quickRatio** (number, float) *(nullable)*
  Índice de Liquidez Seca ((Ativo Circulante - Estoques) / Passivo Circulante).

- **currentRatio** (number, float) *(nullable)*
  Índice de Liquidez Corrente (Ativo Circulante / Passivo Circulante).

- **debtToEquity** (number, float) *(nullable)*
  Índice Dívida Líquida / Patrimônio Líquido.

- **revenuePerShare** (number, float) *(nullable)*
  Receita Líquida por Ação (Receita Líquida TTM / Ações em Circulação).

- **returnOnAssets** (number, float) *(nullable)*
  Retorno sobre Ativos (ROA): Lucro Líquido TTM / Ativo Total Médio.

- **returnOnEquity** (number, float) *(nullable)*
  Retorno sobre Patrimônio Líquido (ROE): Lucro Líquido TTM / Patrimônio Líquido Médio.

- **earningsGrowth** (number, float) *(nullable)*
  Crescimento do Lucro Líquido (geralmente trimestral YoY, como `earningsQuarterlyGrowth`).

- **revenueGrowth** (number, float) *(nullable)*
  Crescimento da Receita Líquida (geralmente trimestral YoY).

- **grossMargins** (number, float) *(nullable)*
  Margem Bruta (Lucro Bruto TTM / Receita Líquida TTM).

- **ebitdaMargins** (number, float) *(nullable)*
  Margem EBITDA (EBITDA TTM / Receita Líquida TTM).

- **operatingMargins** (number, float) *(nullable)*
  Margem Operacional (EBIT TTM / Receita Líquida TTM).

- **profitMargins** (number, float) *(nullable)*
  Margem Líquida (Lucro Líquido TTM / Receita Líquida TTM). Sinônimo do campo de mesmo nome em `DefaultKeyStatisticsEntry`.

- **totalCash** (number, int64) *(nullable)*
  Caixa e Equivalentes de Caixa + Aplicações Financeiras de Curto Prazo (último balanço).

- **totalCashPerShare** (number, float) *(nullable)*
  Caixa Total por Ação (Caixa Total / Ações em Circulação).

- **totalDebt** (number, int64) *(nullable)*
  Dívida Bruta Total (Dívida de Curto Prazo + Dívida de Longo Prazo - último balanço).

- **totalRevenue** (number, int64) *(nullable)*
  Receita Líquida Total (geralmente TTM).

- **grossProfits** (number, int64) *(nullable)*
  Lucro Bruto (geralmente TTM).

- **operatingCashflow** (number, int64) *(nullable)*
  Fluxo de Caixa das Operações (FCO) - (geralmente TTM).

- **freeCashflow** (number, int64) *(nullable)*
  Fluxo de Caixa Livre (FCO - CAPEX) - (geralmente TTM).

- **financialCurrency** (string) *(nullable)*
  Moeda na qual os dados financeiros são reportados (ex: `BRL`, `USD`).

- **updatedAt** (string, date)
  Data da última atualização deste registro específico na fonte de dados (YYYY-MM-DD).

- **type** (string) - Options: `yearly`, `quarterly`, `ttm`
  Periodicidade dos dados: `yearly` (anual), `quarterly` (trimestral), `ttm` (Trailing Twelve Months).


### HistoricalDataPrice

Representa um ponto na série histórica de preços de um ativo.

**Properties:**

- **date** (integer, int64)
  Data do pregão ou do ponto de dados, representada como um timestamp UNIX (número de segundos desde 1970-01-01 UTC).

- **open** (number, float)
  Preço de abertura do ativo no intervalo (dia, semana, mês, etc.).

- **high** (number, float)
  Preço máximo atingido pelo ativo no intervalo.

- **low** (number, float)
  Preço mínimo atingido pelo ativo no intervalo.

- **close** (number, float)
  Preço de fechamento do ativo no intervalo.

- **volume** (integer, int64)
  Volume financeiro negociado no intervalo.

- **adjustedClose** (number, float)
  Preço de fechamento ajustado para proventos (dividendos, JCP, bonificações, etc.) e desdobramentos/grupamentos.


### IncomeStatementEntry

Representa os dados de uma Demonstração do Resultado do Exercício (DRE) para um período específico (anual ou trimestral).

**Properties:**

- **id** (string)
  Identificador único deste registro de DRE (interno).

- **symbol** (string)
  Ticker do ativo ao qual a DRE se refere.

- **type** (string) - Options: `yearly`, `quarterly`
  Indica a periodicidade da DRE: `yearly` (anual) ou `quarterly` (trimestral).

- **endDate** (string, date)
  Data de término do período fiscal ao qual a DRE se refere (YYYY-MM-DD).

- **totalRevenue** (number, int64) *(nullable)*
  Receita Operacional Líquida.

- **costOfRevenue** (number, int64) *(nullable)*
  Custo dos Produtos Vendidos (CPV) ou Custo dos Serviços Prestados (CSP).

- **grossProfit** (number, int64) *(nullable)*
  Lucro Bruto (Receita Líquida - CPV/CSP).

- **researchDevelopment** (number, int64) *(nullable)*
  Despesas com Pesquisa e Desenvolvimento.

- **sellingGeneralAdministrative** (number, int64) *(nullable)*
  Despesas com Vendas, Gerais e Administrativas.

- **nonRecurring** (number, int64) *(nullable)*
  Itens Não Recorrentes (pode incluir outras despesas/receitas operacionais).

- **otherOperatingExpenses** (number, int64) *(nullable)*
  Outras Despesas Operacionais.

- **totalOperatingExpenses** (number, int64) *(nullable)*
  Total das Despesas Operacionais (P&D + SG&A + Outras).

- **operatingIncome** (number, int64) *(nullable)*
  Lucro Operacional (EBIT - Earnings Before Interest and Taxes). Lucro Bruto - Despesas Operacionais.

- **totalOtherIncomeExpenseNet** (number, int64) *(nullable)*
  Resultado Financeiro Líquido + Outras Receitas/Despesas.

- **ebit** (number, int64) *(nullable)*
  Lucro Antes dos Juros e Impostos (LAJIR ou EBIT). Geralmente igual a `operatingIncome`.

- **interestExpense** (number, int64) *(nullable)*
  Despesas Financeiras (Juros pagos). Note que este campo é negativo.

- **incomeBeforeTax** (number, int64) *(nullable)*
  Lucro Antes do Imposto de Renda e Contribuição Social (LAIR). EBIT + Resultado Financeiro.

- **incomeTaxExpense** (number, int64) *(nullable)*
  Imposto de Renda e Contribuição Social sobre o Lucro.

- **minorityInterest** (number, int64) *(nullable)*
  Participação de Acionistas Não Controladores (no Lucro Líquido).

- **netIncomeFromContinuingOps** (number, int64) *(nullable)*
  Lucro Líquido das Operações Continuadas.

- **discontinuedOperations** (number, int64) *(nullable)*
  Resultado Líquido das Operações Descontinuadas.

- **extraordinaryItems** (number, int64) *(nullable)*
  Itens Extraordinários.

- **effectOfAccountingCharges** (number, int64) *(nullable)*
  Efeito de Mudanças Contábeis.

- **otherItems** (number, int64) *(nullable)*
  Outros Itens.

- **netIncome** (number, int64) *(nullable)*
  Lucro Líquido Consolidado do Período.

- **netIncomeApplicableToCommonShares** (number, int64) *(nullable)*
  Lucro Líquido Atribuível aos Acionistas Controladores (Ações Ordinárias).

- **salesExpenses** (number, int64) *(nullable)*
  Despesas com Vendas (detalhamento, pode estar contido em SG&A).

- **lossesDueToNonRecoverabilityOfAssets** (number, int64) *(nullable)*
  Perdas por Não Recuperabilidade de Ativos (Impairment).

- **otherOperatingIncome** (number, int64) *(nullable)*
  Outras Receitas Operacionais (detalhamento).

- **equityIncomeResult** (number, int64) *(nullable)*
  Resultado de Equivalência Patrimonial.

- **financialResult** (number, int64) *(nullable)*
  Resultado Financeiro Líquido.

- **financialIncome** (number, int64) *(nullable)*
  Receitas Financeiras.

- **financialExpenses** (number, int64) *(nullable)*
  Despesas Financeiras (valor positivo aqui, diferente de `interestExpense`).

- **currentTaxes** (number, int64) *(nullable)*
  Imposto de Renda e Contribuição Social Correntes.

- **deferredTaxes** (number, int64) *(nullable)*
  Imposto de Renda e Contribuição Social Diferidos.

- **incomeBeforeStatutoryParticipationsAndContributions** (number, int64) *(nullable)*
  Resultado Antes das Participações Estatutárias.

- **basicEarningsPerCommonShare** (number, float) *(nullable)*
  Lucro Básico por Ação Ordinária (ON).

- **dilutedEarningsPerCommonShare** (number, float) *(nullable)*
  Lucro Diluído por Ação Ordinária (ON).

- **basicEarningsPerPreferredShare** (number, float) *(nullable)*
  Lucro Básico por Ação Preferencial (PN).

- **profitSharingAndStatutoryContributions** (number, int64) *(nullable)*
  Participações nos Lucros e Contribuições Estatutárias.

- **dilutedEarningsPerPreferredShare** (number, float) *(nullable)*
  Lucro Diluído por Ação Preferencial (PN).

- **claimsAndOperationsCosts** (number, int64) *(nullable)*
  Custos com Sinistros e Operações (específico para Seguradoras).

- **administrativeCosts** (number, int64) *(nullable)*
  Despesas Administrativas (detalhamento, pode estar contido em SG&A).

- **otherOperatingIncomeAndExpenses** (number, int64) *(nullable)*
  Outras Receitas e Despesas Operacionais (agregado).

- **earningsPerShare** (number, float) *(nullable)*
  Lucro por Ação (LPA) - Geral (pode ser básico ou diluído, verificar contexto).

- **basicEarningsPerShare** (number, float) *(nullable)*
  Lucro Básico por Ação (LPA Básico) - Geral.

- **dilutedEarningsPerShare** (number, float) *(nullable)*
  Lucro Diluído por Ação (LPA Diluído) - Geral.

- **insuranceOperations** (number, int64) *(nullable)*
  Resultado de Operações de Seguros (específico para Seguradoras).

- **reinsuranceOperations** (number, int64) *(nullable)*
  Resultado de Operações de Resseguros (específico para Seguradoras).

- **complementaryPensionOperations** (number, int64) *(nullable)*
  Resultado de Operações de Previdência Complementar (específico para Seguradoras/Previdência).

- **capitalizationOperations** (number, int64) *(nullable)*
  Resultado de Operações de Capitalização (específico para Seguradoras).

- **updatedAt** (string, date) *(nullable)*
  Data da última atualização deste registro específico na fonte de dados (YYYY-MM-DD).


### QuoteResponse

Resposta principal do endpoint `/api/quote/{tickers}`.

**Properties:**

- **results** (array)
  Array contendo os resultados detalhados para cada ticker solicitado.
  Array items:
    Reference to: **QuoteResult**

- **requestedAt** (string, date-time)
  Timestamp indicando quando a requisição foi recebida pelo servidor. Formato ISO 8601.

- **took** (string)
  Tempo aproximado que o servidor levou para processar a requisição, em formato de string (ex: `746ms`).


### QuoteResult

Contém os dados detalhados de um ativo específico retornado pelo endpoint `/api/quote/{tickers}`.

**Properties:**

- **symbol** (string)
  Ticker (símbolo) do ativo (ex: `PETR4`, `^BVSP`).

- **currency** (string)
  Moeda na qual os valores monetários são expressos (geralmente `BRL`).

- **twoHundredDayAverage** (number, float) *(nullable)*
  Média móvel simples dos preços de fechamento dos últimos 200 dias.

- **twoHundredDayAverageChange** (number, float) *(nullable)*
  Variação absoluta entre o preço atual e a média de 200 dias.

- **twoHundredDayAverageChangePercent** (number, float) *(nullable)*
  Variação percentual entre o preço atual e a média de 200 dias.

- **marketCap** (number, int64) *(nullable)*
  Capitalização de mercado total do ativo (Preço Atual x Ações em Circulação).

- **shortName** (string) *(nullable)*
  Nome curto ou abreviado da empresa ou ativo.

- **longName** (string) *(nullable)*
  Nome longo ou completo da empresa ou ativo.

- **regularMarketChange** (number, float) *(nullable)*
  Variação absoluta do preço no dia atual em relação ao fechamento anterior.

- **regularMarketChangePercent** (number, float) *(nullable)*
  Variação percentual do preço no dia atual em relação ao fechamento anterior.

- **regularMarketTime** (string, date-time) *(nullable)*
  Data e hora da última atualização da cotação (último negócio registrado). Formato ISO 8601.

- **regularMarketPrice** (number, float) *(nullable)*
  Preço atual ou do último negócio registrado.

- **regularMarketDayHigh** (number, float) *(nullable)*
  Preço máximo atingido no dia de negociação atual.

- **regularMarketDayRange** (string) *(nullable)*
  String formatada mostrando o intervalo de preço do dia (Mínimo - Máximo).

- **regularMarketDayLow** (number, float) *(nullable)*
  Preço mínimo atingido no dia de negociação atual.

- **regularMarketVolume** (number, int64) *(nullable)*
  Volume financeiro negociado no dia atual.

- **regularMarketPreviousClose** (number, float) *(nullable)*
  Preço de fechamento do pregão anterior.

- **regularMarketOpen** (number, float) *(nullable)*
  Preço de abertura no dia de negociação atual.

- **averageDailyVolume3Month** (number, int64) *(nullable)*
  Média do volume financeiro diário negociado nos últimos 3 meses.

- **averageDailyVolume10Day** (number, int64) *(nullable)*
  Média do volume financeiro diário negociado nos últimos 10 dias.

- **fiftyTwoWeekLowChange** (number, float) *(nullable)*
  Variação absoluta entre o preço atual e o preço mínimo das últimas 52 semanas.

- **fiftyTwoWeekRange** (string) *(nullable)*
  String formatada mostrando o intervalo de preço das últimas 52 semanas (Mínimo - Máximo).

- **fiftyTwoWeekHighChange** (number, float) *(nullable)*
  Variação absoluta entre o preço atual e o preço máximo das últimas 52 semanas.

- **fiftyTwoWeekHighChangePercent** (number, float) *(nullable)*
  Variação percentual entre o preço atual e o preço máximo das últimas 52 semanas.

- **fiftyTwoWeekLow** (number, float) *(nullable)*
  Preço mínimo atingido nas últimas 52 semanas.

- **fiftyTwoWeekHigh** (number, float) *(nullable)*
  Preço máximo atingido nas últimas 52 semanas.

- **priceEarnings** (number, float) *(nullable)*
  Indicador Preço/Lucro (P/L): Preço Atual / Lucro Por Ação (LPA) TTM. Retornado se `fundamental=true`.

- **earningsPerShare** (number, float) *(nullable)*
  Lucro Por Ação (LPA) dos últimos 12 meses (TTM). Retornado se `fundamental=true`.

- **logourl** (string, url)
  URL da imagem do logo do ativo/empresa.

- **updatedAt** (string, date-time) *(nullable)*
  Timestamp da última atualização dos dados do índice na fonte (aplicável principalmente a índices, como `^BVSP`). Formato ISO 8601.

- **usedInterval** (string) *(nullable)*
  O intervalo (`interval`) efetivamente utilizado pela API para retornar os dados históricos, caso solicitado.

- **usedRange** (string) *(nullable)*
  O período (`range`) efetivamente utilizado pela API para retornar os dados históricos, caso solicitado.

- **historicalDataPrice** (array) *(nullable)*
  Array contendo a série histórica de preços, retornado apenas se os parâmetros `range` e/ou `interval` forem especificados na requisição.
  Array items:
    Reference to: **HistoricalDataPrice**

- **validRanges** (array)
  Lista dos valores válidos que podem ser utilizados no parâmetro `range` para este ativo específico.
  Array items:
    **Type:** string


- **validIntervals** (array)
  Lista dos valores válidos que podem ser utilizados no parâmetro `interval` para este ativo específico.
  Array items:
    **Type:** string


- **dividendsData** *(nullable)*
  Objeto contendo informações sobre dividendos, JCP e outros eventos corporativos. Retornado apenas se `dividends=true` for especificado na requisição.
  Reference to: **DividendsData**

- **summaryProfile** *(nullable)*
  Resumo do perfil da empresa. Retornado apenas se `modules` incluir `summaryProfile`.
  Reference to: **SummaryProfile**

- **balanceSheetHistory** (array) *(nullable)*
  Histórico **anual** do Balanço Patrimonial. Retornado apenas se `modules` incluir `balanceSheetHistory`.
  Array items:
    Reference to: **BalanceSheetEntry**

- **balanceSheetHistoryQuarterly** (array) *(nullable)*
  Histórico **trimestral** do Balanço Patrimonial. Retornado apenas se `modules` incluir `balanceSheetHistoryQuarterly`.
  Array items:
    Reference to: **BalanceSheetEntry**

- **defaultKeyStatistics** *(nullable)*
  Principais estatísticas financeiras atuais/TTM. Retornado apenas se `modules` incluir `defaultKeyStatistics`.
  Reference to: **DefaultKeyStatisticsEntry**

- **defaultKeyStatisticsHistory** (array) *(nullable)*
  Histórico **anual** das principais estatísticas. Retornado apenas se `modules` incluir `defaultKeyStatisticsHistory`.
  Array items:
    Reference to: **DefaultKeyStatisticsEntry**

- **defaultKeyStatisticsHistoryQuarterly** (array) *(nullable)*
  Histórico **trimestral** das principais estatísticas. Retornado apenas se `modules` incluir `defaultKeyStatisticsHistoryQuarterly`.
  Array items:
    Reference to: **DefaultKeyStatisticsEntry**

- **incomeStatementHistory** (array) *(nullable)*
  Histórico **anual** da Demonstração do Resultado (DRE). Retornado apenas se `modules` incluir `incomeStatementHistory`.
  Array items:
    Reference to: **IncomeStatementEntry**

- **incomeStatementHistoryQuarterly** (array) *(nullable)*
  Histórico **trimestral** da Demonstração do Resultado (DRE). Retornado apenas se `modules` incluir `incomeStatementHistoryQuarterly`.
  Array items:
    Reference to: **IncomeStatementEntry**

- **financialData** *(nullable)*
  Dados financeiros e indicadores TTM. Retornado apenas se `modules` incluir `financialData`.
  Reference to: **FinancialDataEntry**

- **financialDataHistory** (array) *(nullable)*
  Histórico **anual** de dados financeiros e indicadores. Retornado apenas se `modules` incluir `financialDataHistory`.
  Array items:
    Reference to: **FinancialDataEntry**

- **financialDataHistoryQuarterly** (array) *(nullable)*
  Histórico **trimestral** de dados financeiros e indicadores. Retornado apenas se `modules` incluir `financialDataHistoryQuarterly`.
  Array items:
    Reference to: **FinancialDataEntry**

- **valueAddedHistory** (array) *(nullable)*
  Histórico **anual** da Demonstração do Valor Adicionado (DVA). Retornado apenas se `modules` incluir `valueAddedHistory`.
  Array items:
    Reference to: **ValueAddedEntry**

- **valueAddedHistoryQuarterly** (array) *(nullable)*
  Histórico **trimestral** da Demonstração do Valor Adicionado (DVA). Retornado apenas se `modules` incluir `valueAddedHistoryQuarterly`.
  Array items:
    Reference to: **ValueAddedEntry**

- **cashflowHistory** (array) *(nullable)*
  Histórico **anual** da Demonstração do Fluxo de Caixa (DFC). Retornado apenas se `modules` incluir `cashflowHistory`.
  Array items:
    Reference to: **CashflowEntry**

- **cashflowHistoryQuarterly** (array) *(nullable)*
  Histórico **trimestral** da Demonstração do Fluxo de Caixa (DFC). Retornado apenas se `modules` incluir `cashflowHistoryQuarterly`.
  Array items:
    Reference to: **CashflowEntry**


### StockDividend

Detalhes sobre um evento corporativo que afeta a quantidade de ações (Desdobramento/Split, Grupamento/Inplit, Bonificação).

**Properties:**

- **assetIssued** (string)
  Ticker do ativo afetado pelo evento.

- **factor** (number, float)
  Fator numérico do evento. 
* **Bonificação:** Percentual (ex: 0.1 para 10%).
* **Desdobramento/Grupamento:** Fator multiplicativo ou divisor.

- **completeFactor** (string)
  Descrição textual do fator (ex: `1 / 10`, `10 / 1`).

- **approvedOn** (string, date-time)
  Data em que o evento foi aprovado. Formato ISO 8601.

- **isinCode** (string) *(nullable)*
  Código ISIN do ativo.

- **label** (string)
  Tipo do evento: `DESDOBRAMENTO`, `GRUPAMENTO`, `BONIFICACAO`.

- **lastDatePrior** (string, date-time)
  Data Com (Ex-Date). Último dia para possuir o ativo nas condições antigas. Formato ISO 8601.

- **remarks** (string) *(nullable)*
  Observações adicionais sobre o evento.


### SummaryProfile

Contém informações cadastrais e descritivas sobre a empresa. Retornado via `modules=summaryProfile`.

**Properties:**

- **address1** (string) *(nullable)*
  Linha 1 do endereço da sede da empresa.

- **address2** (string) *(nullable)*
  Linha 2 do endereço da sede da empresa (complemento).

- **city** (string) *(nullable)*
  Cidade da sede da empresa.

- **state** (string) *(nullable)*
  Estado ou província da sede da empresa.

- **zip** (string) *(nullable)*
  Código Postal (CEP) da sede da empresa.

- **country** (string) *(nullable)*
  País da sede da empresa.

- **phone** (string) *(nullable)*
  Número de telefone principal da empresa.

- **website** (string) *(nullable)*
  URL do website oficial da empresa.

- **industry** (string) *(nullable)*
  Nome da indústria em que a empresa atua.

- **industryKey** (string) *(nullable)*
  Chave interna ou código para a indústria.

- **industryDisp** (string) *(nullable)*
  Nome de exibição formatado para a indústria.

- **sector** (string) *(nullable)*
  Nome do setor de atuação da empresa.

- **sectorKey** (string) *(nullable)*
  Chave interna ou código para o setor.

- **sectorDisp** (string) *(nullable)*
  Nome de exibição formatado para o setor.

- **longBusinessSummary** (string) *(nullable)*
  Descrição longa e detalhada sobre as atividades e o negócio da empresa.

- **fullTimeEmployees** (integer) *(nullable)*
  Número estimado de funcionários em tempo integral.

- **companyOfficers** (array) *(nullable)*
  Lista de diretores e executivos principais da empresa (estrutura interna do objeto não detalhada aqui).
  Array items:


### ValueAddedEntry

Representa os dados de uma Demonstração do Valor Adicionado (DVA) para um período específico (anual ou trimestral). A DVA mostra como a riqueza gerada pela empresa foi distribuída.

**Properties:**

- **symbol** (string)
  Ticker do ativo ao qual a DVA se refere.

- **type** (string) - Options: `yearly`, `quarterly`
  Indica a periodicidade da DVA: `yearly` (anual) ou `quarterly` (trimestral).

- **endDate** (string, date)
  Data de término do período fiscal ao qual a DVA se refere (YYYY-MM-DD).

- **revenue** (number, int64) *(nullable)*
  Receitas (Venda de Mercadorias, Produtos e Serviços, etc.). Item 1 da DVA.

- **financialIntermediationRevenue** (number, int64) *(nullable)*
  Receita de Intermediação Financeira (específico para bancos).

- **revenueFromTheProvisionOfServices** (number, int64) *(nullable)*
  Receita da Prestação de Serviços (detalhamento).

- **provisionOrReversalOfExpectedCreditRiskLosses** (number, int64) *(nullable)*
  Provisão/Reversão de Perdas com Risco de Crédito (PCLD).

- **otherRevenues** (number, int64) *(nullable)*
  Outras Receitas.

- **financialIntermediationExpenses** (number, int64) *(nullable)*
  Despesas de Intermediação Financeira (específico para bancos).

- **suppliesPurchasedFromThirdParties** (number, int64) *(nullable)*
  Insumos Adquiridos de Terceiros (Custo de Mercadorias, Matérias-Primas). Item 2 da DVA.

- **materialsEnergyAndOthers** (number, int64) *(nullable)*
  Custos com Materiais, Energia, Serviços de Terceiros e Outros.

- **services** (number, int64) *(nullable)*
  Serviços de Terceiros (detalhamento).

- **lossOrRecoveryOfAssetValues** (number, int64) *(nullable)*
  Perda / Recuperação de Valores de Ativos (Impairment).

- **otherSupplies** (number, int64) *(nullable)*
  Outros Insumos.

- **grossAddedValue** (number, int64) *(nullable)*
  Valor Adicionado Bruto (Receitas - Insumos). Item 3 da DVA.

- **retentions** (number, int64) *(nullable)*
  Retenções (Depreciação, Amortização e Exaustão). Item 4 da DVA.

- **depreciationAndAmortization** (number, int64) *(nullable)*
  Depreciação e Amortização.

- **otherRetentions** (number, int64) *(nullable)*
  Outras Retenções (Exaustão, etc.).

- **netAddedValue** (number, int64) *(nullable)*
  Valor Adicionado Líquido Produzido pela Entidade (Bruto - Retenções). Item 5 da DVA.

- **addedValueReceivedByTransfer** (number, int64) *(nullable)*
  Valor Adicionado Recebido em Transferência (Resultado de Equivalência Patrimonial, Receitas Financeiras, etc.). Item 6 da DVA.

- **equityIncomeResult** (number, int64) *(nullable)*
  Resultado de Equivalência Patrimonial (como receita na DVA).

- **otherValuesReceivedByTransfer** (number, int64) *(nullable)*
  Outros Valores Recebidos (Receitas Financeiras, Aluguéis, etc.).

- **addedValueToDistribute** (number, int64) *(nullable)*
  Valor Adicionado Total a Distribuir (Líquido Produzido + Recebido em Transferência). Item 7 da DVA.

- **distributionOfAddedValue** (number, int64) *(nullable)*
  Distribuição do Valor Adicionado (Soma dos itens seguintes). Item 8 da DVA.

- **teamRemuneration** (number, int64) *(nullable)*
  Pessoal e Encargos (Salários, Benefícios, FGTS).

- **taxes** (number, int64) *(nullable)*
  Impostos, Taxas e Contribuições (Federais, Estaduais, Municipais).

- **federalTaxes** (number, int64) *(nullable)*
  Impostos Federais (IRPJ, CSLL, PIS, COFINS, IPI).

- **stateTaxes** (number, int64) *(nullable)*
  Impostos Estaduais (ICMS).

- **municipalTaxes** (number, int64) *(nullable)*
  Impostos Municipais (ISS).

- **remunerationOfThirdPartyCapitals** (number, int64) *(nullable)*
  Remuneração de Capitais de Terceiros (Juros, Aluguéis).

- **equityRemuneration** (number, int64) *(nullable)*
  Remuneração de Capitais Próprios (JCP, Dividendos, Lucros Retidos).

- **interestOnOwnEquity** (number, int64) *(nullable)*
  Juros sobre o Capital Próprio (JCP).

- **dividends** (number, int64) *(nullable)*
  Dividendos Distribuídos.

- **retainedEarningsOrLoss** (number, int64) *(nullable)*
  Lucros Retidos ou Prejuízo do Exercício.

- **nonControllingShareOfRetainedEarnings** (number, int64) *(nullable)*
  Participação dos Não Controladores nos Lucros Retidos.

- **otherDistributions** (number, int64) *(nullable)*
  Outras Distribuições.

- **productSales** (number, int64) *(nullable)*
  Venda de Produtos e Serviços (detalhamento).

- **constructionOfOwnAssets** (number, int64) *(nullable)*
  Construção de Ativos Próprios.

- **provisionOrReversalOfDoubtfulAccounts** (number, int64) *(nullable)*
  Provisão/Reversão para Créditos de Liquidação Duvidosa (PCLD - como receita/despesa na DVA).

- **costsWithProductsSold** (number, int64) *(nullable)*
  Custos dos Produtos, Mercadorias e Serviços Vendidos (detalhamento).

- **thirdPartyMaterialsAndServices** (number, int64) *(nullable)*
  Materiais, Energia, Serviços de Terceiros.

- **lossOrRecoveryOfAssets** (number, int64) *(nullable)*
  Perda/Recuperação de Valores de Ativos (Impairment - como custo/receita).

- **netAddedValueProduced** (number, int64) *(nullable)*
  Valor Adicionado Líquido Produzido (sinônimo de `netAddedValue`).

- **addedValueReceivedOnTransfer** (number, int64) *(nullable)*
  Valor Adicionado Recebido em Transferência (sinônimo de `addedValueReceivedByTransfer`).

- **financialIncome** (number, int64) *(nullable)*
  Receitas Financeiras (como valor recebido em transferência).

- **insuranceOperationsRevenue** (number, int64) *(nullable)*
  Receita com Operações de Seguros (específico para Seguradoras).

- **complementaryPensionOperationsRevenue** (number, int64) *(nullable)*
  Receita com Operações de Previdência Complementar.

- **feesRevenue** (number, int64) *(nullable)*
  Receita com Taxas e Comissões.

- **variationsOfTechnicalProvisions** (number, int64) *(nullable)*
  Variações das Provisões Técnicas (específico para Seguradoras).

- **insuranceOperationsVariations** (number, int64) *(nullable)*
  Variações de Operações de Seguros.

- **pensionOperationsVariations** (number, int64) *(nullable)*
  Variações de Operações de Previdência.

- **otherVariations** (number, int64) *(nullable)*
  Outras Variações.

- **netOperatingRevenue** (number, int64) *(nullable)*
  Receita Operacional Líquida (detalhamento).

- **claimsAndBenefits** (number, int64) *(nullable)*
  Sinistros Retidos e Benefícios.

- **variationInDeferredSellingExpenses** (number, int64) *(nullable)*
  Variação nas Despesas de Comercialização Diferidas.

- **resultsOfCededReinsuranceOperations** (number, int64) *(nullable)*
  Resultados de Operações de Resseguros Cedidos.

- **resultOfCoinsuranceOperationsAssigned** (number, int64) *(nullable)*
  Resultado de Operações de Cosseguros Cedidos.

- **totalAddedValueToDistribute** (number, int64) *(nullable)*
  Valor Adicionado Total a Distribuir (sinônimo de `addedValueToDistribute`).

- **ownEquityRemuneration** (number, int64) *(nullable)*
  Remuneração de Capitais Próprios (sinônimo de `equityRemuneration`).

- **updatedAt** (string, date)
  Data da última atualização deste registro específico na fonte de dados (YYYY-MM-DD).


