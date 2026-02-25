# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Leia este arquivo inteiro antes de propor qualquer alteração.

---

## 1. Visão geral do projeto

Bot Telegram + monitor de preços para ações da B3 (bolsa brasileira).
Roda em Python 3.10+ num servidor Linux (ou Raspberry Pi / VPS).

**Arquivo principal:** `monitor.py`
Quando criar versão nova para teste, use `monitor_v2.py`, `monitor_v3.py`, etc.
Nunca sobrescreva o arquivo atual — sempre gere uma cópia nova numerada.

---

## 2. Como rodar

```bash
# Ativar ambiente virtual
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# Instalar dependências
pip install -r requirements.txt

# Rodar o bot principal
python monitor.py

# Rodar análise histórica
python analyze.py
```

Verificar sintaxe sem executar:
```bash
python -c "import ast; ast.parse(open('monitor.py', encoding='utf-8').read()); print('OK')"
```

---

## 3. Stack e dependências

```
Python          3.10+
brapi==1.2.0    SDK brapi.dev (cotações B3)
openai==2.22.0  Cliente Perplexity Sonar (via base_url alternativa)
requests        HTTP direto para Telegram Bot API
pytz            Timezone America/Sao_Paulo
matplotlib      Gráficos de desempenho
pandas          Análise de dados históricos
python-dotenv   Carregamento de .env
```

**NÃO adicione** dependências novas sem avisar o usuário. Pergunte antes.

---

## 4. Arquivos do projeto

| Arquivo | Papel | Pode editar? |
|---|---|---|
| `monitor.py` | Bot principal (produção Railway) | ✅ gera cópia nova |
| `analyze.py` | Análise histórica e gráficos | ✅ gera cópia nova |
| `historico.json` | Snapshots de preços + trades | ⚠️ só leitura |
| `posicoes.json` | Posições abertas em carteira | ⚠️ só leitura |
| `watchlist.json` | Tickers monitorados | ⚠️ só leitura |
| `.env` | API keys (NUNCA exiba o conteúdo) | ❌ não toque |
| `CLAUDE.md` | Este arquivo | ❌ não modifique |

---

## 5. Variáveis de ambiente (.env)

```
BRAPI_API_KEY=...
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
PERPLEXITY_API_KEY=...
```

**Regra absoluta:** nunca imprima, logue ou exponha essas variáveis.
Se precisar debugar autenticação, use apenas os primeiros 4 caracteres: `key[:4]`.

---

## 6. Arquitetura do monitor.py

O arquivo está dividido em seções numeradas com comentários `# SEÇÃO N`:

```
SEÇÃO 1   — Imports, constantes globais e watchlist (JSON)
SEÇÃO 2   — Detecção de horário de mercado (BRT)
SEÇÃO 2.5 — Histórico de cotações e rastreamento de fechamentos
SEÇÃO 3   — Busca de cotações, fundamentalistas, filtro de qualidade e score
SEÇÃO 3.5 — Integração Perplexity Sonar ("por que caiu?", cache 6h)
SEÇÃO 3.6-3.7 — Comando datascience (análise de portfólio)
SEÇÃO 3.2b — _obter_fundamentalistas_completo() → TTM + 4 trimestres
SEÇÃO 3.8  — Streak de quedas cumulativas (3/4 dias)
SEÇÃO 3.9  — executar_check() → tabela trimestral via Telegram
SEÇÃO 4   — Envio de mensagens Telegram
SEÇÃO 5   — Cálculo de IR (day-trade 20% / swing-trade 15%)
SEÇÃO 6   — Persistência de posições (posicoes.json)
SEÇÃO 7   — Processamento de updates e comandos Telegram (polling)
SEÇÃO 8   — Loop principal de monitoramento
```

**Fluxo principal (loop a cada 15 min):**
```
brapi API → cotações em lote → filtro de qualidade → score (0-10)
→ Perplexity Sonar (cache) → alerta Telegram → historico.json
```

**Constantes-chave:**
```python
LIMIAR_QUEDA_PCT            = -3.0      # Alerta quando queda >= 3%
WATCHLIST_MAX               = 60        # Limite seguro do plano brapi free
STREAK_ATIVO                = True      # Detecção de queda cumulativa
STREAK_REGRAS               = [(3,-6.0),(4,-8.0)]
FILTRO_QUALIDADE_ATIVO      = True      # Bloqueia ativos de baixa qualidade
CACHE_SONAR_TTL_SEGUNDOS    = 21600     # Cache Sonar: 6 horas
PREGAO_HORA_INICIO          = 10        # Início pregão (BRT)
PREGAO_HORA_FIM             = 17        # Fim pregão (BRT)
```

---

## 7. Módulos brapi usados no /check

A função `_obter_fundamentalistas_completo()` faz **1 chamada HTTP** com estes módulos:

```python
modules = (
    "financialData,"
    "defaultKeyStatistics,"
    "balanceSheetHistoryQuarterly,"
    "incomeStatementHistoryQuarterly,"
    "cashflowStatementHistoryQuarterly,"
    "summaryProfile"
)
```

O dict retornado contém: `fcf_positivo`, `fcf_valor`, `roe`, `dy`, `receita_ttm`,
`margem_bruta`, `margem_liquida`, `pl`, `divida_liq_ebitda`, `ebitda`,
`divida_liquida`, `preco_atual`, `timestamp_cotacao`, `receita_4t`, `fcf_4t`,
`margem_bruta_4t`, `margem_liquida_4t`, `ticker_validado`, `nome`.

---

## 8. Validação de tickers (v8.5+)

`validar_tickers_em_lote(tickers, apenas_acoes=True)` usa 2 camadas:
1. SDK brapi em lote (`client.quote.retrieve`)
2. HTTP direto por ticker se o SDK não retornou `symbol`

- Ticker inexistente → lista `invalidos` → erro no Telegram
- Falha total de rede → aceita por padrão (não bloqueia usuário)
- `quoteType ≠ EQUITY` → rejeitado (FIIs, BDRs, ETFs)

---

## 9. Formato de mensagens Telegram

Todas as mensagens usam **texto simples monospace** — sem Markdown, sem HTML.
Separador padrão: `chr(9472) * 32` (caractere `─`).
Mensagens longas: `_enviar_mensagem_fatiada()` divide em blocos ≤ 4000 chars.

**Não altere o layout da mensagem do `/check`** sem avisar o usuário —
o formato foi calibrado para leitura em celular.

---

## 10. Convenções de código

- **Idioma dos comentários:** português
- **Idioma das mensagens Telegram:** português
- **Nomenclatura:** snake_case; funções privadas com prefixo `_`
- **F-strings com backslash:** proibido em Python ≤ 3.11
  - ❌ `f"{'─' * 30}\n"` → SyntaxWarning
  - ✅ `sep = "─" * 30; f"{sep}\n"`
- **Logging:** use `print(f"  [seção] mensagem")` — não use o módulo `logging`
- **Timeout em requests:** sempre `timeout=10` ou `timeout=20` para brapi

---

## 11. O que NÃO fazer

- ❌ Não refatore tudo de uma vez — faça patches cirúrgicos
- ❌ Não troque `requests` por `httpx` ou `aiohttp` sem avisar
- ❌ Não adicione `async/await` — o bot roda síncrono por design
- ❌ Não remova seções de fallback (ex: fallback TTM no /check)
- ❌ Não mude nomes de campos nos dicts persistidos em JSON
  (quebra `historico.json` e `posicoes.json` existentes)
- ❌ Não exponha API keys em logs, prints ou outputs

---

## 12. Como propor mudanças

1. Descreva o que vai mudar e **por que**
2. Mostre o trecho antigo e o novo lado a lado
3. Confirme que `python3 -c "import ast; ast.parse(open('arquivo.py').read())"` passa
4. Liste quais seções do arquivo foram afetadas
5. Pergunte antes de tocar em mais de 1 seção por vez

---

## 13. Contexto do usuário

- Engenheiro Eletricista, novato em programação — explique o raciocínio passo a passo
- Usa Cursor + Claude Code para edição local
- Usa Claude.ai (Sonnet/Opus) para análises e geração de patches maiores
- **Não presuma conhecimento** de Python avançado

@PROJECT_KNOWLEDGE.md

Sempre que precisar de contexto do projeto, pergunte primeiro para o oracle:
"Use the oracle agent to explain..."
ou
"Use oracle to answer about..."

Isso economiza tokens porque o oracle já sabe tudo.