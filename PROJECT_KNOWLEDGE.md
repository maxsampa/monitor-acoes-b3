# Meu Monitor — Base de Conhecimento Completa (Oracle)

**Gerado:** 2026-02-24 | **Atualizado:** 2026-02-25
**Projeto:** Monitor de preços B3 com alertas Telegram
**Arquivo principal:** monitor.py (produção Railway)
**Python:** 3.10+

---

## 1. VISÃO GERAL

Sistema automatizado de monitoramento de ações da B3 que:
- Detecta quedas ≥ 3% via brapi.dev API
- Envia alertas Telegram com IA (Perplexity Sonar)
- Registra compras/vendas via botões Telegram
- Calcula IR (day-trade 20% / swing-trade 15%)
- Oferece análise de portfólio via `/datascience` (senha)
- Mantém histórico em JSON para rastreamento de performance

---

## 2. ARQUIVOS PRINCIPAIS

| Arquivo | Propósito | Status |
|---------|-----------|--------|
| `monitor.py` | Bot principal — produção Railway | ATUAL |
| `analyze.py` | Análise histórica + gráficos | ESTÁVEL |
| `watchlist.json` | Lista dinâmica de tickers (auto-criado no boot) | LIVE |
| `posicoes.json` | Posições abertas/fechadas com IR (auto-criado) | LIVE |
| `historico.json` | Snapshots de preço + registros de trades (auto-criado) | LIVE |
| `.env` | API keys (NUNCA expor) | SEGURO |

### Dependências
```
brapi==1.2.0          # SDK oficial B3
openai==2.22.0        # Cliente Perplexity (usa base_url override)
requests==2.32.5      # HTTP para Telegram e brapi direto
pytz==2025.2          # Timezone America/Sao_Paulo
pandas==3.0.1         # Análise de dados (analyze.py, /datascience)
matplotlib==3.10.8    # Gráficos (analyze.py)
python-dotenv==1.2.1  # Carrega .env
```

---

## 3. ARQUITETURA: SEÇÕES DO MONITOR

### SEÇÃO 1 — Imports, Constantes e Watchlist
**Funções principais:**
- `carregar_watchlist()` → Carrega tickers do watchlist.json
- `salvar_watchlist(tickers)` → Persiste tickers em JSON
- `validar_tickers_em_lote(tickers, apenas_acoes)` → Validação em lote (1 chamada HTTP)

**Constantes-chave:**
```python
LIMIAR_QUEDA_PCT              = -3.0      # Threshold de alerta
WATCHLIST_MAX                 = 60        # Limite seguro plano free brapi
FILTRO_QUALIDADE_ATIVO        = True      # Toggle do filtro
VOLUME_MINIMO_MULTIPLICADOR   = 1.5       # Volume mín vs média 20d
CACHE_SONAR_TTL_SEGUNDOS      = 21600     # 6 horas
STREAK_ATIVO                  = True
STREAK_REGRAS                 = [(3, -6.0), (4, -8.0)]
PREGAO_HORA_INICIO            = 10
PREGAO_HORA_FIM               = 19
ARQUIVO_POSICOES              = "posicoes.json"
ARQUIVO_WATCHLIST             = "watchlist.json"
ARQUIVO_HISTORICO             = "historico.json"
SEGURANCA_SENHA               = "fabio123"
```

**Estratégia de validação de ticker:**
1. SDK brapi em lote (`quote.retrieve`)
2. Fallback: HTTP direto por ticker
3. Aceita se falha total de rede (não bloqueia usuário)
4. Rejeita se `quoteType ≠ EQUITY` (filtra FIIs, BDRs, ETFs)

---

### SEÇÃO 2 — Detecção de Horário de Mercado (BRT)
**Funções:**
- `_agora_brt()` → Hora atual em BRT
- `checar_mercado_aberto()` → Verifica se mercado aberto (dias úteis 10h–19h + sentinel brapi)
- `calcular_espera_ate_proximo_pregao()` → Calcula sleep até próximo pregão

---

### SEÇÃO 2.5 — Histórico de Cotações e Fechamentos
**Funções:**
- `_carregar_historico()` → Carrega historico.json
- `_salvar_historico(historico)` → Persiste historico.json
- `registrar_cotacao_historico(cotacoes)` → Salva snapshots de preço
- `registrar_fechamento_historico(ticker, resultado_ir, preco_entrada, quantidade)` → Loga fechamento com IR

**Estrutura do historico.json:**
```json
[
  {
    "tipo": "cotacao",
    "data": "2026-02-22 22:32",
    "ticker": "PETR4",
    "preco": 37.97,
    "variacao_pct": 0.42,
    "volume": 51949800.0,
    "variacao_pct_dia_anterior": null
  },
  {
    "tipo": "fechamento",
    "data": "2026-02-23 14:30",
    "ticker": "PETR4",
    "preco_entrada": 36.50,
    "preco_saida": 38.00,
    "quantidade": 100,
    "roi_pct": 4.11,
    "valor_compra": 3650.00,
    "valor_venda": 3800.00,
    "corretagem": 0.0,
    "lucro_bruto": 150.00,
    "lucro_liquido": 150.00,
    "tipo_operacao": "swing-trade",
    "aliquota_pct": 15.0,
    "ir_devido": 22.50,
    "prazo_darf": "03/2026",
    "isento": false
  }
]
```

---

### SEÇÃO 3 — Busca de Cotações
**Função:** `buscar_cotacoes(tickers)` → Batch via SDK brapi

**Retorna por ticker:**
```python
{
  "symbol": "PETR4",
  "preco": 37.97,
  "variacao_pct": 0.42,
  "volume": 51949800.0,
  "nome": "Petróleo Brasileiro",
  "fifty_two_week_low": 26.50,
  "fifty_two_week_high": 41.20
}
```

---

### SEÇÃO 3.2 — Fundamentalistas Básicos
**Função:** `buscar_fundamentalistas(ticker)` → HTTP para `/quote/{ticker}?modules=...`

**Módulos:** `summaryProfile`, `defaultKeyStatistics`, `financialData`

**Retorna:**
```python
{
  "fcf_positivo": True,
  "fcf_valor": 15000000000.0,
  "roe": 22.5,          # já em %, ex: 0.225 → 22.5
  "dy": 9.2,            # já em %
  "volume_medio_20d": 51000000.0
}
```

---

### SEÇÃO 3.3 — Filtro de Qualidade
**Função:** `verificar_filtro_qualidade(ticker, volume_atual, fund)` → `(passes: bool, labels: list[str])`

**Critérios:** Volume ≥ 1.5x média 20d AND FCF positivo
- Dados indisponíveis (None) → passa por padrão
- Labels: `["Volume 2.1x média", "FCF positivo"]`

---

### SEÇÃO 3.4 — Score de Oportunidade (0–10)
**Função:** `calcular_score(variacao_pct, preco_atual, fund, volume_atual, fifty_two_week_low, fifty_two_week_high)`

**Componentes (5 × 2 pts):**
1. % Queda hoje: ≥10% → 2pts, ≥7% → 1.5pts, etc.
2. Distância do mín 52s: ≤5% → 2pts
3. Dividend Yield: ≥10% → 2pts
4. ROE: ≥25% → 2pts
5. Volume vs média 20d: ≥3.0x → 2pts

**Classificação:**
- 8.0+: 🔥 EXCEPCIONAL
- 6.5–7.9: ⭐ FORTE
- 5.0–6.4: 👀 MODERADO
- 3.5–4.9: ⚠️ FRACO
- <3.5: ❌ RUIM

---

### SEÇÃO 3.5 — Perplexity Sonar ("Por que caiu?")
**Funções:**
- `_cache_sonar_valido(ticker)` → Verifica TTL (6h)
- `_salvar_cache_sonar(ticker, texto)` → Salva em `_CACHE_SONAR` (memória)
- `consultar_perplexity(ticker, variacao_pct)` → Query API Sonar

**Cache:** `_CACHE_SONAR = {"PETR4": {"texto": str, "ts": float}, ...}`
**Modelo:** `sonar` (rápido, acesso real-time à web)
**Timeout:** 20 segundos

---

### SEÇÃO 3.6 — Perplexity para /datascience
**Função:** `consultar_perplexity_datascience(resumo_texto)` → Comentário buy-and-hold

---

### SEÇÃO 3.7 — Comando /datascience
**Funções:**
- `_capturar_analise()` → Extrai dados do portfólio
- `executar_datascience(chat_id, texto_original)` → Processa comando

**monitor.py:** Retorna dict estruturado → 5 mensagens separadas:
1. Header + Cotações recentes
2. Quedas ≥3%
3. Posições fechadas + abertas
4. Resumo executivo (ROI, Lucro, IR)
5. Comentário Perplexity + Disclaimer

---

### SEÇÃO 3.2b — Fundamentalistas Completos para /check
**Função:** `_obter_fundamentalistas_completo(ticker)` → 1 chamada HTTP

**Módulos:** `financialData`, `defaultKeyStatistics`, `balanceSheetHistoryQuarterly`, `incomeStatementHistoryQuarterly`, `cashflowStatementHistoryQuarterly`, `summaryProfile`

**Retorna dict completo:**
```python
{
  # Valores únicos
  "fcf_positivo": bool,
  "fcf_valor": float,
  "roe": float,              # já em %
  "dy": float,               # já em %
  "receita_ttm": float,
  "margem_bruta": float,     # %
  "margem_liquida": float,   # %
  "pl": float,
  "divida_liq_ebitda": float,
  "ebitda": float,
  "divida_liquida": float,
  "preco_atual": float,
  "timestamp_cotacao": "dd/mm/YYYY HH:MM",
  "ticker_validado": bool,
  "nome": str,

  # Séries trimestrais (últimos 4 trimestres)
  "receita_4t": [{"periodo": "3T23", "valor": 137.5e9}, ...],
  "fcf_4t": [{"periodo": "3T23", "valor": 22.5e9}, ...],
  "margem_bruta_4t": [{"periodo": "3T23", "valor": 35.0}, ...],
  "margem_liquida_4t": [{"periodo": "3T23", "valor": 16.4}, ...]
}
```

---

### SEÇÃO 3.8 — Streak de Quedas Cumulativas
**Função:** `_calcular_streak(ticker, historico)` → `(ativou: bool, soma_pct: float, n_dias: int)`

**Regras:**
- 3 dias ≤ -6% cumulativo → Alerta
- 4 dias ≤ -8% cumulativo → Alerta

---

### SEÇÃO 3.9b — Resolução de Ticker por Nome
**Função:** `_resolver_ticker_por_nome(texto)` → `(tipo: str, tickers: list[str])`
- `("direto", ["PETR4"])` → ticker reconhecido
- `("nome", ["PETR3", "PETR4"])` → nome de empresa encontrado
- `("nenhum", [])` → não reconhecido

**Dict `_MAPA_NOMES`:** 30+ mapeamentos empresa → ticker(s)

---

### SEÇÃO 3.9 — Comando /check
**Função:** `executar_check(chat_id, ticker)` → Relatório fundamental completo

**Processo:**
1. Resolve ticker (direto ou por nome)
2. Busca fundamentalistas completos (1 chamada HTTP)
3. Calcula veredito buy-and-hold (5 critérios, +1/5 cada):
   - FCF positivo
   - DL/EBITDA < 1.8
   - ROE ≥ 12%
   - Margem Bruta > 0
   - DY ≥ 5%
4. Formata tabela evolutiva trimestral
5. Envia via Telegram (fatiado se >4000 chars)

---

### SEÇÃO 4 — Mensagens Telegram
**Funções:**
- `_enviar_mensagem(chat_id, texto, reply_markup)` → Envia com botões inline opcionais
- `_enviar_mensagem_fatiada(chat_id, texto, tamanho_max)` → Divide em blocos ≤4000 chars
- `enviar_alerta_queda(...)` → Formata alerta de queda
- `enviar_alerta_streak(...)` → Formata alerta de streak
- `_responder_callback(callback_query_id, texto)` → Responde clique de botão

**Formato:** Texto simples monospace, sem Markdown/HTML
**Separador:** `─` (chr 9472) × 30
**Botão inline:** "✅ Comprei" → callback `comprei|{ticker}`

---

### SEÇÃO 5 — Cálculo de IR
**Função:** `calcular_ir(preco_entrada, preco_saida, quantidade, data_entrada, data_saida)`

**Regras:**
- Day-trade (mesmo dia ou T+1): 20% sobre lucro líquido
- Swing-trade (>T+1): 15% sobre lucro líquido
- Isento: lucro <R$20k/mês e não day-trade
- Prazo DARF: 3 meses após mês da operação

---

### SEÇÃO 6 — Persistência de Posições
**Funções:**
- `carregar_posicoes()` → Carrega posicoes.json
- `salvar_posicao(ticker, preco_entrada, quantidade, data_entrada, status)`
- `fechar_posicao(ticker, preco_saida, data_saida, resultado_ir)`

**Estrutura posicoes.json:**
```json
[
  {
    "ticker": "PETR4",
    "preco_entrada": 36.50,
    "quantidade": 100,
    "data_entrada": "2026-02-23 10:35",
    "status": "aberta",
    "ir_devido": null
  },
  {
    "ticker": "VALE3",
    "preco_entrada": 80.00,
    "quantidade": 50,
    "preco_saida": 86.00,
    "data_entrada": "2025-10-01 11:00",
    "data_saida": "2026-02-23 14:30",
    "status": "fechada",
    "lucro_bruto": 300.00,
    "lucro_liquido": 300.00,
    "roi_pct": 7.50,
    "ir_devido": 45.00,
    "tipo_operacao": "swing-trade",
    "aliquota_pct": 15.0,
    "prazo_darf": "03/2026",
    "isento_ir": false
  }
]
```

---

### SEÇÃO 7 — Processamento de Updates Telegram
**Funções:**
- `processar_update(update)` → Trata mensagem/callback do Telegram
- `processar_comando(chat_id, texto)` → Despacha para handler do comando

**Comandos disponíveis:**
- `/check TICKER` → Relatório fundamental
- `/datascience SENHA` → Análise de portfólio (protegida por senha)
- Callback `comprei|{ticker}` → Registra compra (2 etapas: preço → quantidade)

---

### SEÇÃO 8 — Loop Principal de Monitoramento
**Função:** `loop_monitoramento()` → Loop infinito com intervalos de 15 min

**Fluxo a cada iteração:**
1. Verifica se mercado está aberto (BRT + sentinel)
2. Dorme até abertura se fechado
3. Busca cotações em batch
4. Registra cotações em historico.json
5. Para cada ticker com queda ≥ -3%:
   a. Busca fundamentalistas
   b. Aplica filtro de qualidade
   c. Calcula score de oportunidade
   d. Verifica streak cumulativo
   e. Consulta Perplexity (ou usa cache)
   f. Envia alerta Telegram com botão
6. Faz polling de updates Telegram
7. Dorme 15 minutos

---

## 4. WATCHLIST ATUAL (watchlist.json)

14 tickers: PETR4, VALE3, ITUB4, BBAS3, WEGE3, TAEE11, CPLE6, ELET3, PRIO3, EQTL3, RAIL3, B3SA3, MGLU3, AXIA3

---

## 5. HISTÓRICO DE VERSÕES

| Versão | Status | Mudanças principais |
|--------|--------|---------------------|
| `monitor_v8_6.py` | REMOVIDO | `/datascience` com 1 mensagem grande (`io.StringIO`) |
| `monitor_v8_7.py` | REMOVIDO | `/datascience` com 5 mensagens separadas; helpers `_fb()`, `_fp()` |
| `monitor.py` | **PRODUÇÃO** | Igual ao v8.7 — renomeado para deploy Railway |

### Comportamento do primeiro boot (Railway)
- `watchlist.json` → criado automaticamente com 12 tickers padrão (PETR4, VALE3, ITUB4...)
- `historico.json` → criado na primeira cotação registrada
- `posicoes.json` → criado na primeira compra registrada via Telegram

---

## 6. REFERÊNCIA RÁPIDA: FUNÇÕES POR SEÇÃO

| Seção | Funções-chave | Propósito |
|-------|---------------|-----------|
| 1 | `carregar_watchlist()`, `validar_tickers_em_lote()` | Carregar/validar tickers |
| 2 | `checar_mercado_aberto()`, `_agora_brt()` | Horário de mercado |
| 2.5 | `registrar_cotacao_historico()`, `registrar_fechamento_historico()` | Log de histórico |
| 3 | `buscar_cotacoes()` | Buscar cotações |
| 3.2 | `buscar_fundamentalistas()` | Fundamentalistas básicos |
| 3.3 | `verificar_filtro_qualidade()` | Filtro de qualidade |
| 3.4 | `calcular_score()`, `_classificar_score()` | Score de oportunidade |
| 3.5 | `consultar_perplexity()`, `_cache_sonar_valido()` | Integração Perplexity |
| 3.6 | `consultar_perplexity_datascience()` | Comentário portfólio |
| 3.7 | `executar_datascience()`, `_capturar_analise()` | Comando /datascience |
| 3.2b | `_obter_fundamentalistas_completo()` | Fundamentais completos p/ /check |
| 3.8 | `_calcular_streak()` | Detecção de streak |
| 3.9b | `_resolver_ticker_por_nome()` | Nome → ticker |
| 3.9 | `executar_check()` | Comando /check |
| 4 | `_enviar_mensagem()`, `enviar_alerta_queda()` | Mensagens Telegram |
| 5 | `calcular_ir()` | Cálculo de IR |
| 6 | `carregar_posicoes()`, `salvar_posicao()`, `fechar_posicao()` | Gestão de posições |
| 7 | `processar_update()`, `processar_comando()` | Dispatch de comandos |
| 8 | `loop_monitoramento()` | Loop principal |

---

## 7. GLOSSÁRIO

- **BRT:** Horário de Brasília (UTC-3)
- **Pregão:** Sessão de negociação
- **DARF:** Documento de Arrecadação de Receitas Federais (imposto)
- **DY:** Dividend Yield (rendimento de dividendos %)
- **ROE:** Return on Equity (retorno sobre patrimônio %)
- **FCF:** Free Cash Flow (fluxo de caixa livre)
- **DL/EBITDA:** Dívida Líquida / EBITDA (alavancagem)
- **TTM:** Trailing Twelve Months (últimos 12 meses)
- **Streak:** Queda cumulativa por N dias
- **Isento:** Isento de IR (lucro <R$20k/mês, não day-trade)

---

## 8. IDEIAS PENDENTES (do diretório Ideias/)

1. Relatório mensal automático (todo dia 1)
2. Detector de drawdown (-15% cumulativo = oportunidade rara)
3. Regras de sizing de posição (% máximo por ativo/setor)
4. Planejamento fiscal (sugestão de timing ótimo de venda)
5. Criptografia do historico.json (Fernet)
6. Watchlist condicional (alerta "só abaixo de R$35")
7. Registro de tese de investimento junto ao trade
8. Análise de tempo de hold (histograma)

---

*Fim do PROJECT_KNOWLEDGE.md — Atualizado em 2026-02-24*
