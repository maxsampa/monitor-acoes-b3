# ============================================================
# monitor.py — Monitor de Quedas B3 com Alertas no Telegram
# Projeto: Mauá Engenharia Industrial & IA
# Autor: gerado via Claude Sonnet 4.6
# Versão: 8.7 — /datascience estético mobile (mensagens separadas)
#
# Novidades v8.0:
#   - FILTRO DE QUALIDADE: alerta só dispara se volume > 1.5x
#     média 20 dias E FCF positivo nos últimos 4 trimestres
#     (dados via brapi indicadores fundamentalistas)
#   - SCORE DE OPORTUNIDADE (0-10): calculado a partir de
#     % queda, distância da mínima 52 semanas, DY, ROE, volume
#   - CACHE SONAR (em memória, TTL 6h): evita re-consultar
#     a Perplexity para o mesmo ticker no mesmo pregão
#   - ALERTA ENRIQUECIDO: mostra "Score: 7.8/10 | Volume alto
#     | FCF positivo" antes do motivo Perplexity
#   - Filtro de qualidade configurável via FILTRO_QUALIDADE_ATIVO
#     (True/False) — pode desligar para debug sem perder código
#
# Mantido da v7.0:
#   - Comando "datascience SENHA" via Telegram com senha oculta
#   - Executa análises do analyze.py diretamente (sem Streamlit)
#   - Integração Perplexity Sonar para motivo de queda
#   - Resposta única para registro de compra ("38.50 100")
#   - Máximo 3 tentativas em caso de formato inválido
#   - Sleep em fatias de 5s (resposta rápida ao botão Comprei)
#   - IR automático na venda (day-trade 20% / swing 15%)
#   - Histórico em historico.json + posições em posicoes.json
#   - Detecção inteligente de pregão via timestamps brapi
#
# Versões anteriores:
#   v7.0 — comando datascience + análise via Telegram
#   v6.0 — integração Perplexity Sonar para motivo de queda
#   v5.1 — sleep 30s → 5s no polling
#   v5.0 — fluxo em 2 etapas (preco → quantidade separados)
#   v4.0 — detecção inteligente de pregão via timestamps brapi
#   v3.x — rastreamento de posições + cálculo de IR
# ============================================================

import os
import io
import re
import sys
import json
import time
import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # backend sem janela — obrigatório em servidor
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from brapi import Brapi
import pytz

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

BRAPI_API_KEY      = os.environ.get("BRAPI_API_KEY")
TELEGRAM_TOKEN     = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")

# ============================================================
# SENHA DE SEGURANÇA — comando "datascience"
# Definida no .env como SEGURANCA_SENHA=...  Nunca deixe visível no Telegram.
# ============================================================
SEGURANCA_SENHA = os.getenv("SEGURANCA_SENHA", "")

# Modelo Perplexity usado para busca de motivos de queda
# sonar = modelo rápido/barato com acesso à web em tempo real
PERPLEXITY_MODEL = "sonar"

# Limiar de queda para disparar alerta (em %)
LIMIAR_QUEDA_PCT = -2.5

# Arquivos de persistência
ARQUIVO_POSICOES  = "posicoes.json"
ARQUIVO_WATCHLIST = "watchlist.json"   # v8.1: trocado de .txt para .json
ARQUIVO_HISTORICO = "historico.json"

# Limite máximo de tickers na watchlist (free tier brapi seguro)
WATCHLIST_MAX = 60

# ============================================================
# CONFIGURAÇÕES v8.2 — STREAK DE QUEDAS CUMULATIVAS
# ============================================================

# Liga/desliga detecção de streak
STREAK_ATIVO = True

# Regras: (janela_dias, limiar_pct)
# soma dos últimos N dias <= limiar → alerta STREAK
STREAK_REGRAS = [
    (3, -6.0),   # 3 dias acumulados <= -6%
    (4, -8.0),   # 4 dias acumulados <= -8%
]


# Corretagem padrão por operação em R$ (0.0 = isenta)
CORRETAGEM_PADRAO = 0.0

# Fuso horário oficial da B3
TZ_BRT = pytz.timezone("America/Sao_Paulo")

# Horário de pregão B3 (seg-sex)
PREGAO_HORA_INICIO = 10   # 10h BRT
PREGAO_HORA_FIM    = 17   # 17h BRT (cobrindo after-market)

# Ticker sentinela: usado para checar se o pregão está ativo
TICKER_SENTINELA = "PETR4"

# ============================================================
# CONFIGURAÇÕES v8.0 — FILTRO DE QUALIDADE E SCORE
# ============================================================

# Liga/desliga filtro de qualidade (False = alerta sempre, útil para debug)
FILTRO_QUALIDADE_ATIVO = True

# Multiplicador de volume sobre média 20 dias para considerar "volume alto"
VOLUME_MINIMO_MULTIPLICADOR = 1.5

# TTL do cache Perplexity em segundos (6 horas = 21600s)
CACHE_SONAR_TTL_SEGUNDOS = 6 * 3600

# ============================================================
# ESTADO DE CONVERSA — máquina de estados em memória
# ============================================================
ESTADO_CONVERSA: dict = {}

# Offset do Telegram getUpdates
_ULTIMO_UPDATE_ID: int = 0

# ============================================================
# CACHE SONAR — dicionário em memória {ticker: (texto, timestamp)}
# Evita re-consultar Perplexity para o mesmo ticker no mesmo pregão.
# Estrutura: { "PETR4": {"texto": "...", "ts": 1710000000.0} }
# ============================================================
_CACHE_SONAR: dict = {}

# ============================================================
# CONTROLE DE ALERTAS — limita ruído de notificações
# ============================================================

# Contador de alertas de queda simples por dia, por ticker.
# Estrutura: { "PETR4": {"data": "2026-03-04", "count": 2} }
# Reset automático quando a data muda (meia-noite BRT).
_CONTAGEM_ALERTAS_QUEDA: dict = {}

# Tickers com streak cumulativo já alertado no ciclo atual.
# Entrada removida automaticamente quando o streak termina
# (variação volta ao positivo), permitindo alertar o próximo streak.
_STREAKS_ALERTADOS: set = set()


# ============================================================
# SEÇÃO 1 — WATCHLIST (v8.1: JSON + gerenciamento dinâmico)
# ============================================================

def carregar_watchlist() -> list:
    """
    Carrega a watchlist do arquivo watchlist.json.
    Formato: lista JSON de strings maiúsculas — ["PETR4", "VALE3", ...]
    Se o arquivo não existir, cria automaticamente com a lista fixa padrão.
    """
    lista_fixa = [
        "PETR4", "VALE3", "ITUB4", "BBAS3",
        "WEGE3", "TAEE11", "CPLE6", "ELET3",
        "PRIO3", "EQTL3", "RAIL3", "B3SA3"
    ]

    if os.path.exists(ARQUIVO_WATCHLIST):
        try:
            with open(ARQUIVO_WATCHLIST, "r", encoding="utf-8") as f:
                tickers = json.load(f)
            # Garante strings únicas em maiúsculas
            tickers = list(dict.fromkeys(
                t.strip().upper() for t in tickers
                if isinstance(t, str) and t.strip()
            ))
            if tickers:
                print(f"  Watchlist carregada: {len(tickers)} tickers "
                      f"de {ARQUIVO_WATCHLIST}")
                return tickers
        except (json.JSONDecodeError, Exception) as erro:
            print(f"  Aviso: erro ao ler {ARQUIVO_WATCHLIST} ({erro}). "
                  f"Usando lista fixa.")

    # Arquivo não existe ou inválido → cria com lista fixa
    print(f"  {ARQUIVO_WATCHLIST} não encontrado. "
          f"Criando com lista fixa padrão ({len(lista_fixa)} tickers).")
    salvar_watchlist(lista_fixa)
    return lista_fixa


def salvar_watchlist(tickers: list):
    """
    Persiste a watchlist em watchlist.json.
    Remove duplicatas e garante maiúsculas antes de salvar.
    """
    tickers_limpos = list(dict.fromkeys(
        t.strip().upper() for t in tickers
        if isinstance(t, str) and t.strip()
    ))
    with open(ARQUIVO_WATCHLIST, "w", encoding="utf-8") as f:
        json.dump(tickers_limpos, f, indent=2, ensure_ascii=False)
    print(f"  Watchlist salva: {len(tickers_limpos)} tickers "
          f"→ {ARQUIVO_WATCHLIST}")


def _validar_ticker_brapi(ticker: str) -> bool:
    """Compat: valida 1 ticker. Usa validar_tickers_em_lote internamente."""
    validos, _ = validar_tickers_em_lote([ticker])
    return ticker.upper() in validos


def validar_tickers_em_lote(
    tickers: list,
    apenas_acoes: bool = True,
) -> tuple:
    """
    Valida N tickers em UMA única chamada HTTP à brapi.

    Estratégia de validação (em ordem):
    1. Chama brapi.quote.retrieve(tickers="T1,T2,...") via SDK
    2. Verifica se cada ticker retornou 'symbol' preenchido
    3. Se SDK falhou OU não retornou symbol → tenta HTTP direto por ticker
    4. Só em falha TOTAL de rede aceita por padrão (não bloqueia usuário)

    Parâmetros
    ----------
    tickers      : lista de strings (ex: ["PETR4", "VALE3", "CARA3"])
    apenas_acoes : se True, rejeita quoteType != EQUITY (FIIs, BDRs, ETFs)

    Retorna
    -------
    (validos: list[str], invalidos: list[str])
    """
    if not tickers:
        return [], []

    tickers_upper = [t.strip().upper() for t in tickers if t.strip()]
    tickers_str   = ",".join(tickers_upper)
    print(f"  [Validação] Consultando brapi: {tickers_str}")

    # ── Passo 1: chamada em lote via SDK ─────────────────────
    mapa     = {}   # symbol → objeto resultado
    sdk_ok   = False
    try:
        client   = Brapi(api_key=BRAPI_API_KEY)
        resposta = client.quote.retrieve(tickers=tickers_str)
        results  = resposta.results or []
        for r in results:
            sym = (getattr(r, "symbol", None) or "").upper().strip()
            if sym:
                mapa[sym] = r
        sdk_ok = True
        print(f"  [Validação] SDK retornou {len(mapa)} symbol(s)")
    except Exception as erro:
        print(f"  [Validação] SDK erro: {erro} — tentando HTTP direto")

    # ── Passo 2: para tickers sem resultado no SDK, tenta HTTP ─
    sem_resultado = [t for t in tickers_upper if t not in mapa]
    if sem_resultado:
        for t in sem_resultado:
            try:
                url_t = f"https://brapi.dev/api/quote/{t}"
                r_t   = requests.get(
                    url_t,
                    params={"token": BRAPI_API_KEY},
                    timeout=10
                )
                if r_t.status_code == 200:
                    data_t   = r_t.json()
                    results_t = data_t.get("results", [])
                    if results_t:
                        sym_t = (results_t[0].get("symbol") or "").upper().strip()
                        if sym_t:
                            # Cria objeto simples com os campos necessários
                            class _Obj:
                                pass
                            obj = _Obj()
                            obj.symbol    = sym_t
                            obj.quoteType = results_t[0].get("quoteType", "")
                            mapa[sym_t]   = obj
                            print(f"  [Validação] {t}: OK via HTTP direto")
                        else:
                            print(f"  [Validação] {t}: sem symbol no HTTP — inválido")
                    else:
                        print(f"  [Validação] {t}: results vazio no HTTP — inválido")
                elif r_t.status_code == 404:
                    print(f"  [Validação] {t}: 404 — ticker inválido")
                else:
                    print(f"  [Validação] {t}: HTTP {r_t.status_code} — assumindo inválido")
            except Exception as e2:
                print(f"  [Validação] {t}: falha de rede ({e2})")
                # Falha de rede: aceita este ticker por padrão
                class _Obj:
                    pass
                obj = _Obj()
                obj.symbol    = t
                obj.quoteType = ""
                mapa[t] = obj

    # ── Passo 3: classifica válidos / inválidos ───────────────
    validos   = []
    invalidos = []

    for t in tickers_upper:
        if t not in mapa:
            # Não apareceu em nenhuma fonte → inválido
            invalidos.append(t)
            print(f"  [Validação] {t}: INVÁLIDO (não encontrado)")
            continue

        obj = mapa[t]

        # Checagem de tipo: aceita EQUITY ou vazio (desconhecido)
        if apenas_acoes:
            tipo = (
                getattr(obj, "quoteType", None)
                or getattr(obj, "quote_type", None)
                or ""
            )
            if isinstance(tipo, str):
                tipo = tipo.upper()
            if tipo and tipo not in ("EQUITY", ""):
                invalidos.append(t)
                print(f"  [Validação] {t}: tipo={tipo} — não é ação, rejeitado")
                continue

        validos.append(t)
        print(f"  [Validação] {t}: VÁLIDO ✓")

    print(f"  [Validação] Resultado: {len(validos)} válidos, {len(invalidos)} inválidos")
    return validos, invalidos


# ============================================================
# SEÇÃO 2 — DETECÇÃO INTELIGENTE DE PREGÃO
# ============================================================

def _agora_brt() -> datetime:
    return datetime.now(tz=TZ_BRT)


def _extrair_timestamp_brt(acao) -> datetime:
    ts = getattr(acao, "regular_market_time", None)
    if ts is None:
        ts = getattr(acao, "regular_market_previous_close_time", None)
    if ts is None:
        return None

    if isinstance(ts, (int, float)):
        dt_utc = datetime.fromtimestamp(ts, tz=pytz.utc)
        return dt_utc.astimezone(TZ_BRT)

    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        return ts.astimezone(TZ_BRT)

    return None


def checar_mercado_aberto():
    agora = _agora_brt()

    if agora.weekday() >= 5:
        print(f"  Fim de semana ({agora.strftime('%A %d/%m')}).")
        return False, None

    if not (PREGAO_HORA_INICIO <= agora.hour < PREGAO_HORA_FIM):
        print(f"  Fora do horário de pregão ({agora.strftime('%H:%M')} BRT).")
        return False, None

    try:
        client   = Brapi(api_key=BRAPI_API_KEY)
        resposta = client.quote.retrieve(tickers=TICKER_SENTINELA)

        if not resposta.results:
            print("  brapi retornou lista vazia na checagem de sentinela.")
            return False, None

        dt_brt = _extrair_timestamp_brt(resposta.results[0])

        if dt_brt is None:
            print("  Aviso: timestamp indisponível na brapi. Assumindo aberto.")
            return True, None

        if dt_brt.date() == agora.date():
            print(f"  Timestamp brapi: {dt_brt.strftime('%d/%m/%Y %H:%M')} BRT "
                  f"→ mercado ABERTO hoje.")
            return True, dt_brt
        else:
            print(f"  Preços congelados. Último update: "
                  f"{dt_brt.strftime('%d/%m/%Y %H:%M')} BRT "
                  f"!= hoje ({agora.date().strftime('%d/%m/%Y')}).")
            return False, dt_brt

    except Exception as erro:
        print(f"  Erro ao checar sentinela brapi: {erro}")
        return False, None


def calcular_espera_ate_proximo_pregao() -> float:
    agora   = _agora_brt()
    proximo = agora.replace(hour=PREGAO_HORA_INICIO,
                            minute=0, second=0, microsecond=0)

    if agora >= proximo:
        proximo += timedelta(days=1)

    while proximo.weekday() >= 5:
        proximo += timedelta(days=1)

    segundos = (proximo - agora).total_seconds()
    horas    = segundos / 3600
    print(f"  Dormindo {horas:.1f}h até próximo pregão: "
          f"{proximo.strftime('%d/%m/%Y %H:%M')} BRT")
    return segundos


# ============================================================
# SEÇÃO 2.5 — HISTÓRICO DE COTAÇÕES E FECHAMENTOS
# ============================================================

def _carregar_historico() -> list:
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _salvar_historico(historico: list):
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


def registrar_cotacao_historico(cotacoes: list):
    historico = _carregar_historico()
    agora     = _agora_brt().strftime("%Y-%m-%d %H:%M")

    ultimo_preco: dict = {}
    for reg in historico:
        if reg.get("tipo") == "cotacao" and reg.get("preco") is not None:
            ultimo_preco[reg["ticker"]] = reg["preco"]

    for ativo in cotacoes:
        ticker      = ativo.get("symbol", "?")
        preco_atual = ativo.get("preco")

        preco_ant = ultimo_preco.get(ticker)
        if preco_ant is not None and preco_ant != 0 and preco_atual is not None:
            var_dia_ant = round((preco_atual - preco_ant) / preco_ant * 100, 4)
        else:
            var_dia_ant = None

        historico.append({
            "tipo"                     : "cotacao",
            "data"                     : agora,
            "ticker"                   : ticker,
            "preco"                    : preco_atual,
            "variacao_pct"             : ativo.get("variacao_pct"),
            "volume"                   : ativo.get("volume"),
            "variacao_pct_dia_anterior": var_dia_ant,
        })

    _salvar_historico(historico)
    print(f"  → {len(cotacoes)} cotações salvas em historico.json")


def registrar_fechamento_historico(ticker: str, resultado_ir: dict,
                                   preco_entrada: float, quantidade: int):
    historico   = _carregar_historico()
    preco_saida = resultado_ir["preco_saida"]
    roi_pct     = ((preco_saida - preco_entrada) / preco_entrada) * 100

    historico.append({
        "tipo"          : "fechamento",
        "data"          : _agora_brt().strftime("%Y-%m-%d %H:%M"),
        "ticker"        : ticker,
        "preco_entrada" : preco_entrada,
        "preco_saida"   : preco_saida,
        "quantidade"    : quantidade,
        "roi_pct"       : round(roi_pct, 2),
        "valor_compra"  : resultado_ir["valor_compra"],
        "valor_venda"   : resultado_ir["valor_venda"],
        "corretagem"    : resultado_ir["corretagem"],
        "lucro_bruto"   : resultado_ir["lucro_bruto"],
        "lucro_liquido" : resultado_ir["lucro_liquido"],
        "tipo_operacao" : resultado_ir["tipo_operacao"],
        "aliquota_pct"  : resultado_ir["aliquota_pct"],
        "ir_devido"     : resultado_ir["ir_devido"],
        "prazo_darf"    : resultado_ir["prazo_darf"],
        "isento"        : resultado_ir["isento"],
    })

    _salvar_historico(historico)
    print(f"  → Fechamento {ticker} salvo em historico.json "
          f"(ROI: {roi_pct:+.2f}% | IR: R$ {resultado_ir['ir_devido']:,.2f})")


# ============================================================
# SEÇÃO 3 — COTAÇÕES (brapi.dev SDK oficial)
# ============================================================

def _buscar_cotacao_individual(ticker: str) -> dict | None:
    """
    Busca cotação de 1 ticker via HTTP direto (plano free brapi).
    Retorna dict no mesmo formato de buscar_cotacoes(), ou None em erro.
    """
    url    = f"https://brapi.dev/api/quote/{ticker}"
    params = {"token": BRAPI_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            print(f"  [Cotação] HTTP {resp.status_code} para {ticker}")
            return None
        results = resp.json().get("results", [])
        if not results:
            return None
        a = results[0]
        return {
            "symbol"             : a.get("symbol", ticker),
            "preco"              : a.get("regularMarketPrice"),
            "variacao_pct"       : a.get("regularMarketChangePercent"),
            "volume"             : a.get("regularMarketVolume"),
            "nome"               : a.get("shortName") or a.get("longName"),
            "fifty_two_week_low" : a.get("fiftyTwoWeekLow"),
            "fifty_two_week_high": a.get("fiftyTwoWeekHigh"),
        }
    except Exception as erro:
        print(f"  [Cotação] Erro individual {ticker}: {erro}")
        return None


def buscar_cotacoes(tickers: list) -> list:
    """
    Busca cotações em lote via SDK brapi.
    Plano gratuito só permite 1 ativo por requisição — se o batch
    retornar menos de metade dos tickers, faz chamadas individuais
    como fallback automático.
    """
    client      = Brapi(api_key=BRAPI_API_KEY)
    tickers_str = ",".join(tickers)

    resultados_batch = []
    try:
        resposta = client.quote.retrieve(tickers=tickers_str)
        for acao in resposta.results:
            resultados_batch.append({
                "symbol"             : acao.symbol,
                "preco"              : acao.regular_market_price,
                "variacao_pct"       : acao.regular_market_change_percent,
                "volume"             : acao.regular_market_volume,
                "nome"               : acao.short_name,
                "fifty_two_week_low" : getattr(acao, "fifty_two_week_low",  None),
                "fifty_two_week_high": getattr(acao, "fifty_two_week_high", None),
            })
    except Exception as erro:
        print(f"  [Cotação] Erro no batch brapi SDK: {erro}")

    # Plano gratuito só retorna 1 resultado por chamada batch
    # → se retornou menos de metade, usa fallback individual
    limite_batch = max(1, len(tickers) // 2)
    if len(resultados_batch) >= limite_batch:
        return resultados_batch

    print(
        f"  [Cotação] Batch retornou {len(resultados_batch)}/{len(tickers)} tickers. "
        f"Assumindo plano free → buscando individualmente..."
    )
    resultados = []
    for tk in tickers:
        dado = _buscar_cotacao_individual(tk)
        if dado:
            resultados.append(dado)
    print(f"  [Cotação] Individual: {len(resultados)}/{len(tickers)} obtidos.")
    return resultados


# ============================================================
# SEÇÃO 3.2 — DADOS FUNDAMENTALISTAS (brapi.dev)
# Plano gratuito: apenas ROE e volume médio disponíveis.
# FCF, DY, EBITDA, DL/EBITDA requerem plano pago — não buscados.
# ============================================================

def buscar_fundamentalistas(ticker: str) -> dict:
    """
    Retorna ROE e volume médio 20 dias para score e filtro de qualidade.
    Usa apenas defaultKeyStatistics (disponível no plano gratuito brapi).

    Campos retornados (None se indisponível):
        roe              : float — Return on Equity (%)
        volume_medio_20d : float — volume médio 20 pregões
    """
    url    = f"https://brapi.dev/api/quote/{ticker}"
    params = {
        "token"  : BRAPI_API_KEY,
        "modules": "defaultKeyStatistics,financialData",
    }

    resultado_padrao = {
        "roe"             : None,
        "volume_medio_20d": None,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"  [Fundamentos] Erro HTTP {resp.status_code} para {ticker}")
            return resultado_padrao

        data    = resp.json()
        results = data.get("results", [])
        if not results:
            print(f"  [Fundamentos] Sem results para {ticker}")
            return resultado_padrao

        ativo = results[0]
        fd    = ativo.get("financialData",        {}) or {}
        ks    = ativo.get("defaultKeyStatistics", {}) or {}

        # ── ROE ──────────────────────────────────────────────────
        roe_raw = fd.get("returnOnEquity") or ks.get("returnOnEquity")
        roe     = None
        if roe_raw is not None:
            if isinstance(roe_raw, dict):
                roe_raw = roe_raw.get("raw")
            if roe_raw is not None:
                roe = round(float(roe_raw) * 100, 2)  # brapi devolve 0.18 → 18%

        # ── Volume médio 20 dias ──────────────────────────────────
        vol_raw = (
            ativo.get("averageDailyVolume10Day")
            or ativo.get("averageVolume")
        )
        volume_medio_20d = None
        if vol_raw is not None:
            if isinstance(vol_raw, dict):
                vol_raw = vol_raw.get("raw")
            if vol_raw is not None:
                volume_medio_20d = float(vol_raw)

        vol_str = f"{volume_medio_20d:,.0f}" if volume_medio_20d else "?"
        print(f"  [Fundamentos] {ticker}: ROE={roe}% VolMed={vol_str}")

        return {
            "roe"             : roe,
            "volume_medio_20d": volume_medio_20d,
        }

    except Exception as erro:
        print(f"  [Fundamentos] Exceção para {ticker}: {erro}")
        return resultado_padrao


# ============================================================
# SEÇÃO 3.3 — FILTRO DE QUALIDADE (v8.0)
# Critério único (plano free brapi): Volume > 1.5x média 20 dias.
# FCF removido — requer plano pago brapi e sempre retornava None.
# Se dados indisponíveis (None), o filtro passa por padrão.
# ============================================================

def verificar_filtro_qualidade(
    ticker: str,
    volume_atual: float,
    fund: dict
) -> tuple[bool, list]:
    """
    Retorna (passa: bool, labels: list[str]).

    passa  = True se deve enviar alerta
    labels = lista de badges para exibir no Telegram
    """
    if not FILTRO_QUALIDADE_ATIVO:
        return True, ["Filtro desativado"]

    labels = []
    bloqueios = []

    # ── Critério: Volume > 1.5x média 20 dias ────────────────
    volume_medio = fund.get("volume_medio_20d")
    if volume_medio and volume_medio > 0 and volume_atual:
        multiplicador = volume_atual / volume_medio
        if multiplicador >= VOLUME_MINIMO_MULTIPLICADOR:
            labels.append(f"Volume {multiplicador:.1f}x média")
        else:
            bloqueios.append(
                f"Volume baixo ({multiplicador:.1f}x < {VOLUME_MINIMO_MULTIPLICADOR}x)"
            )
    else:
        # Dados indisponíveis → passa sem penalidade
        labels.append("Volume: dados indispon.")

    if bloqueios:
        print(f"  [Filtro] {ticker} BLOQUEADO: {' | '.join(bloqueios)}")
        return False, bloqueios

    print(f"  [Filtro] {ticker} APROVADO: {' | '.join(labels)}")
    return True, labels


# ============================================================
# SEÇÃO 3.4 — SCORE DE OPORTUNIDADE (v8.0)
#
# Score 0–10 composto por 4 componentes (2 pontos cada):
#   A) % de queda hoje          (quanto maior a queda, maior o score)
#   B) Distância da mín. 52s    (quão perto está da mínima anual)
#   C) ROE                      (retorno sobre patrimônio)
#   D) Volume vs. média 20 dias (confirmação do movimento)
#
# DY removido — requer plano pago brapi e sempre retornava None.
# Cada componente retorna 0.0–2.0 pontos.
# Componentes sem dados retornam 0.8 (neutro, não penaliza demais).
# ============================================================

def calcular_score(
    variacao_pct: float,
    preco_atual: float,
    fund: dict,
    volume_atual: float,
    fifty_two_week_low: float  = None,
    fifty_two_week_high: float = None,
) -> tuple[float, list]:
    """
    Retorna (score: float 0-10, detalhes: list[str]).

    detalhes = lista de strings com contribuição de cada componente,
               usada para debugar e exibir no alerta Telegram.
    """
    pontos   = 0.0
    detalhes = []

    # ── A) % de queda hoje (0-2 pts) ─────────────────────────
    queda_abs = abs(variacao_pct)
    if queda_abs >= 10:
        pts_a = 2.0
    elif queda_abs >= 7:
        pts_a = 1.5
    elif queda_abs >= 5:
        pts_a = 1.0
    elif queda_abs >= 3:
        pts_a = 0.5
    else:
        pts_a = 0.0
    pontos += pts_a
    detalhes.append(f"Queda {variacao_pct:+.1f}% → {pts_a:.1f}pts")

    # ── B) Distância da mínima 52 semanas (0-2 pts) ───────────
    pts_b = 0.8  # neutro se dados indisponíveis
    if fifty_two_week_low and preco_atual and fifty_two_week_low > 0:
        dist_pct = ((preco_atual - fifty_two_week_low) / fifty_two_week_low) * 100
        if dist_pct <= 5:
            pts_b = 2.0    # muito perto da mínima = oportunidade histórica
        elif dist_pct <= 15:
            pts_b = 1.5
        elif dist_pct <= 30:
            pts_b = 1.0
        elif dist_pct <= 50:
            pts_b = 0.5
        else:
            pts_b = 0.0    # preço ainda alto vs. mínima anual
        detalhes.append(f"Dist mín52s {dist_pct:.0f}% → {pts_b:.1f}pts")
    else:
        detalhes.append(f"Dist mín52s: s/dados → {pts_b:.1f}pts")
    pontos += pts_b

    # ── C) ROE (0-2 pts) — disponível no plano free ───────────
    roe   = fund.get("roe")
    pts_c = 0.8  # neutro
    if roe is not None:
        if roe >= 25:
            pts_c = 2.0
        elif roe >= 15:
            pts_c = 1.5
        elif roe >= 10:
            pts_c = 1.0
        elif roe >= 5:
            pts_c = 0.5
        else:
            pts_c = 0.0
        detalhes.append(f"ROE {roe:.1f}% → {pts_c:.1f}pts")
    else:
        detalhes.append(f"ROE: s/dados → {pts_c:.1f}pts")
    pontos += pts_c

    # ── D) Volume vs. média 20 dias (0-2 pts) ─────────────────
    volume_medio = fund.get("volume_medio_20d")
    pts_d = 0.8  # neutro
    if volume_medio and volume_medio > 0 and volume_atual:
        mult = volume_atual / volume_medio
        if mult >= 3.0:
            pts_d = 2.0
        elif mult >= 2.0:
            pts_d = 1.5
        elif mult >= 1.5:
            pts_d = 1.0
        elif mult >= 1.0:
            pts_d = 0.5
        else:
            pts_d = 0.0
        detalhes.append(f"Volume {mult:.1f}x média → {pts_d:.1f}pts")
    else:
        detalhes.append(f"Volume: s/dados → {pts_d:.1f}pts")
    pontos += pts_d

    # Score final arredondado para 1 casa decimal
    score = round(min(pontos, 10.0), 1)
    return score, detalhes


def _classificar_score(score: float) -> str:
    """Rótulo humano para o score."""
    if score >= 8.0:
        return "🔥 EXCEPCIONAL"
    elif score >= 6.5:
        return "⭐ FORTE"
    elif score >= 5.0:
        return "👀 MODERADO"
    elif score >= 3.5:
        return "⚠️ FRACO"
    else:
        return "❌ RUIM"


# ============================================================
# SEÇÃO 3.5 — PERPLEXITY SONAR: MOTIVO DA QUEDA (com cache)
# ============================================================

def _cache_sonar_valido(ticker: str) -> str | None:
    """
    Verifica se existe cache válido para o ticker.
    Retorna o texto em cache se válido, None caso contrário.
    TTL: CACHE_SONAR_TTL_SEGUNDOS (padrão 6h).
    """
    entrada = _CACHE_SONAR.get(ticker)
    if not entrada:
        return None

    idade = time.time() - entrada["ts"]
    if idade < CACHE_SONAR_TTL_SEGUNDOS:
        horas = idade / 3600
        print(f"  [Cache Sonar] {ticker}: cache válido ({horas:.1f}h atrás). Reutilizando.")
        return entrada["texto"]

    # Cache expirado — remove
    del _CACHE_SONAR[ticker]
    print(f"  [Cache Sonar] {ticker}: cache expirado ({idade/3600:.1f}h). Buscando novo.")
    return None


def _salvar_cache_sonar(ticker: str, texto: str):
    """Salva resultado Perplexity no cache em memória."""
    _CACHE_SONAR[ticker] = {"texto": texto, "ts": time.time()}
    print(f"  [Cache Sonar] {ticker}: resultado salvo (TTL {CACHE_SONAR_TTL_SEGUNDOS/3600:.0f}h).")


def consultar_perplexity(ticker: str, variacao_pct: float) -> str:
    """
    Consulta Perplexity Sonar para o motivo da queda.
    Usa cache em memória (TTL 6h) para evitar re-consultas
    desnecessárias no mesmo pregão.
    """
    # ── Verifica cache primeiro ───────────────────────────────
    cache_hit = _cache_sonar_valido(ticker)
    if cache_hit:
        return cache_hit

    if not PERPLEXITY_API_KEY:
        print("  [Perplexity] PERPLEXITY_API_KEY não configurada — pulando consulta.")
        return "Motivo: consulta Perplexity não configurada (adicione PERPLEXITY_API_KEY ao .env)."

    query = (
        f'{ticker} ("por que as ações" OR "por que a ação" OR '
        f'"o que aconteceu" OR "despenca" OR "derrete" OR '
        f'"tombo" OR "afunda") '
        f'(site:infomoney.com.br OR site:valor.globo.com OR '
        f'site:br.investing.com OR site:suno.com.br OR '
        f'site:moneytimes.com.br OR site:seudinheiro.com OR '
        f'site:einvestidor.estadao.com.br OR site:neofeed.com.br OR '
        f'site:braziljournal.com OR site:exame.com OR '
        f'site:bloomberglinea.com.br)'
    )

    system_prompt = (
        "Você é um analista financeiro objetivo. "
        "Responda APENAS em português brasileiro. "
        "Seja direto: informe o motivo principal da queda da ação em 2-4 frases. "
        "Se não encontrar notícia específica, diga 'Nenhuma notícia relevante encontrada.' "
        "Não invente informações. Não use markdown."
    )

    user_prompt = (
        f"Por que as ações de {ticker} caíram {abs(variacao_pct):.1f}% hoje? "
        f"Busque nas fontes financeiras brasileiras e me dê o motivo principal."
    )

    payload = {
        "model"    : PERPLEXITY_MODEL,
        "messages" : [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "return_citations"     : True,
        "search_recency_filter": "day",
    }

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type" : "application/json",
        "Accept"       : "application/json",
    }

    try:
        print(f"  [Perplexity] Consultando motivo da queda de {ticker}...")
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            json    = payload,
            headers = headers,
            timeout = 20,
        )

        if resp.status_code != 200:
            print(f"  [Perplexity] Erro HTTP {resp.status_code}: {resp.text[:300]}")
            return f"Motivo: consulta Perplexity retornou erro {resp.status_code}."

        data = resp.json()

        uso = data.get("usage", {})
        tok_prompt     = uso.get("prompt_tokens",     "?")
        tok_completion = uso.get("completion_tokens", "?")
        tok_total      = uso.get("total_tokens",      "?")
        print(
            f"  [Perplexity] Tokens consumidos — "
            f"prompt: {tok_prompt} | completion: {tok_completion} | "
            f"total: {tok_total} | modelo: {data.get('model', PERPLEXITY_MODEL)}"
        )

        choices = data.get("choices", [])
        if not choices:
            print("  [Perplexity] Resposta sem 'choices'. Verifique a API.")
            return "Motivo: Perplexity não retornou resposta."

        resumo = choices[0].get("message", {}).get("content", "").strip()
        # Remove marcadores de citação [1], [3][5] etc.
        resumo = re.sub(r"\[\d+\]", "", resumo).strip()

        if not resumo:
            return "Motivo: Perplexity retornou resposta vazia."

        if len(resumo) > 500:
            resumo = resumo[:497] + "..."

        print(f"  [Perplexity] Resumo obtido ({len(resumo)} chars): {resumo[:120]}...")

        # Monta texto final com prefixo e salva no cache
        texto_final = f"Motivo via Perplexity:\n{resumo}"
        _salvar_cache_sonar(ticker, texto_final)
        time.sleep(3)   # cortesia de rate-limit após chamada Sonar
        return texto_final

    except requests.exceptions.Timeout:
        print("  [Perplexity] Timeout na consulta (>20s). Continuando sem motivo.")
        return "Motivo: Perplexity não respondeu a tempo (timeout 20s)."

    except Exception as erro:
        print(f"  [Perplexity] Exceção inesperada: {erro}")
        return f"Motivo: erro ao consultar Perplexity ({type(erro).__name__})."


# ============================================================
# SEÇÃO 3.6 — PERPLEXITY: COMENTÁRIO DE PERFORMANCE DO PORTFÓLIO
# ============================================================

def consultar_perplexity_datascience(resumo_texto: str) -> str:
    """
    Envia o resumo do analyze.py para a Perplexity e pede
    comentários de performance + recomendações buy-and-hold.
    """
    if not PERPLEXITY_API_KEY:
        return "(Perplexity não configurada — sem comentários adicionais.)"

    system_prompt = (
        "Você é um analista buy-and-hold especialista em B3. "
        "Responda SEMPRE em português brasileiro, de forma objetiva e prática. "
        "Máximo 5 frases. Sem markdown. "
        "Foco: performance real, pontos de atenção e 1-2 recomendações táticas. "
        "Seja cético com hype. Priorize fundamentos e margem de segurança."
    )

    resumo_curto = resumo_texto[:1500] if len(resumo_texto) > 1500 else resumo_texto

    user_prompt = (
        f"Analise este resumo do portfólio B3 e comente a performance:\n\n"
        f"{resumo_curto}\n\n"
        f"Contexto atual: mercado B3, perfil buy-and-hold (6-36 meses). "
        f"Dê comentários de performance e 1-2 recomendações práticas."
    )

    payload = {
        "model"    : PERPLEXITY_MODEL,
        "messages" : [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "return_citations"     : True,
        "search_recency_filter": "week",
    }

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type" : "application/json",
        "Accept"       : "application/json",
    }

    try:
        print("  [Perplexity/DS] Gerando comentários de performance...")
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            json    = payload,
            headers = headers,
            timeout = 25,
        )

        if resp.status_code != 200:
            print(f"  [Perplexity/DS] Erro HTTP {resp.status_code}")
            return f"(Erro ao consultar Perplexity: HTTP {resp.status_code})"

        data    = resp.json()
        uso     = data.get("usage", {})
        print(f"  [Perplexity/DS] Tokens: {uso.get('total_tokens','?')}")

        choices = data.get("choices", [])
        if not choices:
            return "(Perplexity não retornou comentários.)"

        comentario = choices[0].get("message", {}).get("content", "").strip()
        # Remove marcadores de citação [1], [3][5] etc.
        comentario = re.sub(r"\[\d+\]", "", comentario).strip()

        if not comentario:
            return "(Perplexity retornou resposta vazia.)"

        if len(comentario) > 800:
            comentario = comentario[:797] + "..."

        return comentario

    except requests.exceptions.Timeout:
        return "(Timeout ao consultar Perplexity para análise — tente novamente.)"
    except Exception as erro:
        return f"(Erro Perplexity: {type(erro).__name__})"


# ============================================================
# SEÇÃO 3.7 — COMANDO DATASCIENCE: ANÁLISE VIA TELEGRAM
# ============================================================

def _capturar_analise() -> dict:
    """
    Processa historico.json e posicoes.json.
    Retorna dict estruturado com dados para formatação no Telegram.
    Não usa print() capturado — gera dados limpos para mensagens separadas.
    """
    resultado = {
        "erro"              : None,
        "gerado_em"         : _agora_brt().strftime("%d/%m/%Y %H:%M"),
        "periodo"           : "",
        "n_registros"       : 0,
        "n_tickers"         : 0,
        "ultimos"           : [],
        "quedas"            : {"total": 0, "media_pct": 0.0, "maior": None, "lista": []},
        "posicoes_fechadas" : [],
        "posicoes_abertas"  : [],
        "roi_medio"         : None,
        "lucro_total"       : 0.0,
        "ir_total"          : 0.0,
        "total_investido"   : 0.0,
    }

    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        resultado["erro"] = "historico.json nao encontrado ou corrompido."
        return resultado

    cotacoes = [d for d in dados if d.get("tipo") == "cotacao"]
    if not cotacoes:
        cotacoes = [d for d in dados if "preco" in d and "ticker" in d]
    if not cotacoes:
        resultado["erro"] = "Nenhum registro de cotacao encontrado."
        return resultado

    df = pd.DataFrame(cotacoes)
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m-%d %H:%M")
    df = df.drop_duplicates(subset=["ticker", "preco", "variacao_pct"])
    df = df.sort_values(["ticker", "data"]).reset_index(drop=True)

    resultado["n_registros"] = len(df)
    resultado["n_tickers"]   = df["ticker"].nunique()
    resultado["periodo"]     = (
        f"{df['data'].min().strftime('%d/%m/%Y')} → "
        f"{df['data'].max().strftime('%d/%m/%Y')}"
    )

    WATCHLIST_DS = [
        "PETR4", "VALE3", "ITUB4", "BBAS3", "WEGE3",
        "TAEE11", "CPLE6", "ELET3", "PRIO3", "EQTL3",
        "RAIL3", "B3SA3"
    ]
    THRESHOLD_DS = 3.0

    # Últimas cotações
    ultimos = (
        df.sort_values("data")
          .groupby("ticker")
          .last()
          .reset_index()
    )
    for _, row in ultimos[ultimos["ticker"].isin(WATCHLIST_DS)].iterrows():
        resultado["ultimos"].append({
            "ticker" : row["ticker"],
            "preco"  : row["preco"],
            "var_pct": row["variacao_pct"],
            "data"   : row["data"].strftime("%d/%m %H:%M"),
        })

    # Quedas >= threshold
    quedas_raw = df[df["variacao_pct"] <= -THRESHOLD_DS].copy()
    if not quedas_raw.empty:
        quedas_raw["dia"] = quedas_raw["data"].dt.date
        quedas_df = (
            quedas_raw.sort_values("variacao_pct")
                      .groupby(["ticker", "dia"])
                      .first()
                      .reset_index()
        )
        resultado["quedas"]["total"]     = len(quedas_df)
        resultado["quedas"]["media_pct"] = round(quedas_df["variacao_pct"].mean(), 2)
        idx_max = quedas_df["variacao_pct"].idxmin()
        resultado["quedas"]["maior"] = {
            "ticker": quedas_df.loc[idx_max, "ticker"],
            "pct"   : round(quedas_df.loc[idx_max, "variacao_pct"], 2),
            "data"  : quedas_df.loc[idx_max, "data"].strftime("%d/%m/%Y"),
        }
        for _, row in quedas_df.iterrows():
            resultado["quedas"]["lista"].append({
                "ticker" : row["ticker"],
                "var_pct": round(row["variacao_pct"], 2),
                "preco"  : row["preco"],
                "data"   : row["data"].strftime("%d/%m/%Y"),
            })

    # Posições
    try:
        with open(ARQUIVO_POSICOES, "r", encoding="utf-8") as f:
            posicoes = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        posicoes = []

    fechadas = [p for p in posicoes if p.get("status") == "fechada"]
    abertas  = [p for p in posicoes if p.get("status") == "aberta"]

    rois, lucro_total, ir_total = [], 0.0, 0.0
    for p in fechadas:
        p_ent = p.get("preco_entrada") or p.get("preco_compra", 0)
        p_sai = p.get("preco_saida")   or p.get("preco_venda",  0)
        qtd   = p.get("quantidade", 1)
        if not p_ent or not p_sai:
            continue
        roi   = p.get("roi_pct")       or ((p_sai - p_ent) / p_ent * 100)
        lucro = p.get("lucro_liquido") or ((p_sai - p_ent) * qtd)
        ir    = p.get("ir_devido")     or 0.0
        rois.append(roi)
        lucro_total += lucro
        ir_total    += ir
        resultado["posicoes_fechadas"].append({
            "ticker" : p["ticker"],
            "entrada": p_ent,
            "saida"  : p_sai,
            "roi_pct": round(roi, 2),
            "lucro"  : round(lucro, 2),
            "ir"     : round(ir, 2),
        })

    if rois:
        resultado["roi_medio"]   = round(sum(rois) / len(rois), 2)
        resultado["lucro_total"] = round(lucro_total, 2)
        resultado["ir_total"]    = round(ir_total, 2)

    total_inv = 0.0
    for p in abertas:
        p_ent = p.get("preco_entrada") or p.get("preco_compra", 0)
        qtd   = p.get("quantidade", 0)
        total = p_ent * qtd
        total_inv += total
        resultado["posicoes_abertas"].append({
            "ticker"  : p["ticker"],
            "entrada" : p_ent,
            "qtd"     : qtd,
            "total"   : round(total, 2),
            "data_ent": p.get("data_entrada", "?"),
        })
    resultado["total_investido"] = round(total_inv, 2)

    return resultado


def _gerar_grafico_portfolio(dados: dict) -> bytes | None:
    """
    Gera gráfico de barras horizontais com ROI% das posições fechadas
    e distribuição de capital das posições abertas.
    Retorna bytes PNG ou None se não houver dados suficientes.
    """
    fechadas = dados.get("posicoes_fechadas", [])
    abertas  = dados.get("posicoes_abertas",  [])

    # Precisa de pelo menos 1 posição para gerar gráfico
    if not fechadas and not abertas:
        return None

    # ── Paleta dark (compatível com fundo escuro do Telegram) ──
    COR_FUNDO   = "#1e1e2e"
    COR_TEXTO   = "#cdd6f4"
    COR_GRADE   = "#313244"
    COR_VERDE   = "#a6e3a1"
    COR_VERM    = "#f38ba8"
    COR_AZUL    = "#89b4fa"

    n_graficos = (1 if fechadas else 0) + (1 if abertas else 0)
    fig, axes  = plt.subplots(
        n_graficos, 1,
        figsize = (7, 3.5 * n_graficos),
        squeeze = False,
    )
    fig.patch.set_facecolor(COR_FUNDO)

    idx = 0

    # ── Gráfico 1: ROI% por posição fechada ─────────────────
    if fechadas:
        ax = axes[idx][0]
        ax.set_facecolor(COR_FUNDO)

        tickers = [p["ticker"]  for p in fechadas]
        rois    = [p["roi_pct"] for p in fechadas]
        cores   = [COR_VERDE if r >= 0 else COR_VERM for r in rois]

        bars = ax.barh(tickers, rois, color=cores, height=0.55)

        # Labels com o valor dentro/fora da barra
        for bar, roi in zip(bars, rois):
            w      = bar.get_width()
            offset = 0.4 if roi >= 0 else -0.4
            ha     = "left" if roi >= 0 else "right"
            ax.text(
                w + offset,
                bar.get_y() + bar.get_height() / 2,
                f"{roi:+.1f}%",
                va="center", ha=ha,
                fontsize=9, fontweight="bold",
                color=COR_VERDE if roi >= 0 else COR_VERM,
            )

        ax.axvline(0, color=COR_GRADE, linewidth=1)
        ax.set_title(
            "ROI por posição fechada",
            color=COR_TEXTO, fontsize=10, fontweight="bold", pad=6,
        )
        ax.set_xlabel("ROI (%)", color=COR_TEXTO, fontsize=8)
        ax.tick_params(colors=COR_TEXTO, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(COR_GRADE)
        ax.xaxis.grid(True, color=COR_GRADE, linewidth=0.5, linestyle="--")
        ax.set_axisbelow(True)
        idx += 1

    # ── Gráfico 2: Capital em aberto por posição ─────────────
    if abertas:
        ax = axes[idx][0]
        ax.set_facecolor(COR_FUNDO)

        tickers_ab = [p["ticker"] for p in abertas]
        totais_ab  = [p["total"]  for p in abertas]

        ax.barh(tickers_ab, totais_ab, color=COR_AZUL, height=0.55)

        for i, (t, total) in enumerate(zip(tickers_ab, totais_ab)):
            ax.text(
                total * 0.02, i,
                f"R${total/1000:.1f}k",
                va="center", ha="left",
                fontsize=9, fontweight="bold", color=COR_FUNDO,
            )

        ax.set_title(
            "Capital investido — posições abertas",
            color=COR_TEXTO, fontsize=10, fontweight="bold", pad=6,
        )
        ax.set_xlabel("Valor investido (R$)", color=COR_TEXTO, fontsize=8)
        ax.tick_params(colors=COR_TEXTO, labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor(COR_GRADE)
        ax.xaxis.grid(True, color=COR_GRADE, linewidth=0.5, linestyle="--")
        ax.set_axisbelow(True)

    plt.tight_layout(pad=1.5)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=COR_FUNDO)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def executar_datascience(chat_id: str, texto_original: str):
    """
    Processa o comando "/datascience SENHA" recebido no Telegram.
    Envia 5 mensagens separadas para melhor legibilidade mobile.
    Senha errada → ignora silenciosamente.
    """
    partes = texto_original.strip().split(maxsplit=1)

    if len(partes) < 2 or not partes[1].strip():
        return

    senha_digitada = partes[1].strip()
    senha_oculta   = "*" * len(senha_digitada)
    print(f"  [DataScience] Comando recebido. Senha: {senha_oculta}")

    if senha_digitada != SEGURANCA_SENHA:
        print("  [DataScience] Senha incorreta. Ignorando silenciosamente.")
        return

    print("  [DataScience] Senha correta. Iniciando análise...")

    _enviar_mensagem(
        chat_id,
        "🔍 Senha correta. Gerando análise do portfólio...\n"
        "Aguarde alguns segundos."
    )

    try:
        d = _capturar_analise()
    except Exception as erro:
        print(f"  [DataScience] Erro ao capturar análise: {erro}")
        _enviar_mensagem(chat_id, f"❌ Erro ao gerar análise: {erro}")
        return

    if d.get("erro"):
        _enviar_mensagem(chat_id, f"❌ {d['erro']}")
        return

    # ── helpers de formatação ─────────────────────────────────
    def _fb(v):
        if v is None:            return "N/D"
        if abs(v) >= 1_000_000: return f"R${v/1_000_000:.2f}M"
        if abs(v) >= 1_000:     return f"R${v/1_000:.1f}k"
        return f"R${v:,.2f}"

    def _fp(v, dec=1):
        if v is None: return "N/D"
        sinal = "+" if v >= 0 else ""
        return f"{sinal}{v:.{dec}f}%"

    # ── MSG 1: Cabeçalho + Cotações ───────────────────────────
    linhas1 = [
        "📊 PORTFÓLIO B3",
        f"Gerado em: {d['gerado_em']} BRT",
        "",
        "💰 ÚLTIMAS COTAÇÕES",
    ]
    for u in d["ultimos"]:
        seta  = "🟢" if (u.get("var_pct") or 0) >= 0 else "🔴"
        var   = _fp(u.get("var_pct"))
        preco = u.get("preco", 0)
        linhas1.append(f"{u['ticker']:<6}  R${preco:.2f}  {seta} {var}")
    if not d["ultimos"]:
        linhas1.append("(sem dados de cotação)")
    _enviar_mensagem(chat_id, "\n".join(linhas1))

    # ── MSG 2: Quedas ─────────────────────────────────────────
    q = d["quedas"]
    linhas2 = ["📉 QUEDAS ≥ 3%"]
    if q["total"] == 0:
        linhas2.append("Nenhuma queda ≥ 3% no período.")
    else:
        linhas2.append(
            f"{q['total']} evento(s)  —  queda média: {_fp(q.get('media_pct'))}"
        )
        if q.get("maior"):
            m = q["maior"]
            linhas2.append(
                f"Maior: {m.get('ticker', '')} {_fp(m.get('pct'))}  em {m.get('data', '')}"
            )
        linhas2.append("")
        for ev in q.get("lista", [])[:10]:
            linhas2.append(
                f"· {ev.get('ticker', ''):<6}  {_fp(ev.get('var_pct'))}  {ev.get('data', '')}"
            )
    _enviar_mensagem(chat_id, "\n".join(linhas2))

    # ── MSG 3: Posições ───────────────────────────────────────
    linhas3 = ["💼 POSIÇÕES FECHADAS"]
    if not d["posicoes_fechadas"]:
        linhas3.append("(nenhuma)")
    else:
        for p in d["posicoes_fechadas"]:
            roi_str = _fp(p.get("roi_pct"))
            seta    = "🟢" if (p.get("roi_pct") or 0) >= 0 else "🔴"
            linhas3.append(
                f"{seta} {p['ticker']:<6}  "
                f"ent {_fb(p.get('entrada'))} → saí {_fb(p.get('saida'))}  "
                f"ROI {roi_str}  lucro {_fb(p.get('lucro'))}"
            )
    linhas3.append("")
    linhas3.append("📂 POSIÇÕES ABERTAS")
    if not d["posicoes_abertas"]:
        linhas3.append("(nenhuma)")
    else:
        for p in d["posicoes_abertas"]:
            linhas3.append(
                f"· {p['ticker']:<6}  "
                f"{_fb(p.get('entrada'))} × {p.get('qtd', 0)}"
                f" = {_fb(p.get('total'))}  desde {p.get('data_ent', '?')}"
            )
    _enviar_mensagem(chat_id, "\n".join(linhas3))

    # ── MSG 4: Resumo ─────────────────────────────────────────
    linhas4 = [
        "📋 RESUMO GERAL",
        f"Período:        {d['periodo']}",
        f"Registros:      {d['n_registros']} em {d['n_tickers']} ticker(s)",
        "",
        f"ROI médio:      {_fp(d.get('roi_medio'))}",
        f"Lucro total:    {_fb(d.get('lucro_total'))}",
        f"IR estimado:    {_fb(d.get('ir_total'))}",
        f"Total invest.:  {_fb(d.get('total_investido'))}",
    ]
    _enviar_mensagem(chat_id, "\n".join(linhas4))

    # ── Gráfico de portfólio ──────────────────────────────────
    try:
        img_bytes = _gerar_grafico_portfolio(d)
        if img_bytes:
            n_f = len(d["posicoes_fechadas"])
            n_a = len(d["posicoes_abertas"])
            legenda = f"Portfólio B3 — {n_f} posição(ões) fechada(s) | {n_a} aberta(s)"
            _enviar_foto(chat_id, img_bytes, legenda)
            print(f"  [DataScience] Gráfico enviado ({len(img_bytes)//1024}KB).")
        else:
            print("  [DataScience] Sem posições para gráfico.")
    except Exception as eg:
        print(f"  [DataScience] Erro ao gerar gráfico: {eg}")

    # ── Prepara texto resumo para Perplexity ──────────────────
    resumo_texto = (
        f"Portfólio B3 — {d['periodo']}\n"
        f"Registros: {d['n_registros']} | Tickers: {d['n_tickers']}\n"
        f"ROI médio: {_fp(d.get('roi_medio'))} | "
        f"Lucro: {_fb(d.get('lucro_total'))} | "
        f"IR: {_fb(d.get('ir_total'))}\n"
        f"Investido: {_fb(d.get('total_investido'))}\n"
        f"Quedas >= 3%: {q['total']} evento(s)\n"
    )
    for u in d["ultimos"]:
        resumo_texto += (
            f"{u['ticker']}: R${u.get('preco', 0):.2f} ({_fp(u.get('var_pct'))})\n"
        )

    comentario_perp = consultar_perplexity_datascience(resumo_texto)

    # ── MSG 5: Perplexity ─────────────────────────────────────
    linhas5 = [
        "💬 COMENTÁRIOS PERPLEXITY",
        "",
        comentario_perp,
    ]
    _enviar_mensagem(chat_id, "\n".join(linhas5))
    print("  [DataScience] 5 mensagens enviadas com sucesso.")




# ============================================================
# SEÇÃO 3.2b — FUNDAMENTALISTAS COMPLETOS PARA /check (v8.2)
# 1 única chamada HTTP: financialData + defaultKeyStatistics
#                       + balanceSheetHistoryQuarterly
# ============================================================

def _obter_fundamentalistas_completo(ticker: str) -> dict:
    """
    Busca indicadores para /check via 1 chamada HTTP.
    Plano gratuito brapi: disponíveis ROE, P/L (defaultKeyStatistics)
    e séries trimestrais de receita/margens (incomeStatementHistoryQuarterly).
    FCF, DY, EBITDA, DL/EBITDA requerem plano pago — removidos.
    """
    url    = f"https://brapi.dev/api/quote/{ticker}"
    params = {
        "token"  : BRAPI_API_KEY,
        "modules": (
            "financialData,"
            "defaultKeyStatistics,"
            "incomeStatementHistoryQuarterly,"
            "summaryProfile"
        ),
    }
    vazio = {
        "roe"              : None,
        "pl"               : None,
        "volume_medio_20d" : None,
        "preco_atual"      : None,
        "timestamp_cotacao": None,
        # Séries trimestrais [{periodo, valor}, ...]
        "receita_4t"        : [],
        "lucro_liquido_4t"  : [],
        "margem_bruta_4t"   : [],
        "margem_liquida_4t" : [],
        "ticker_validado"  : False,
        "nome"             : ticker,
    }

    def _normalizar_modulo(raw, chave_lista: str) -> dict:
        if isinstance(raw, list):
            return {chave_lista: raw}
        if isinstance(raw, dict):
            return raw
        return {}

    def _raw(v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v.get("raw")
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    try:
        resp = requests.get(url, params=params, timeout=20)
        print(f"  [/check] HTTP {resp.status_code} para {ticker}")
        if resp.status_code != 200:
            return vazio
        data    = resp.json()
        results = data.get("results", [])
        if not results:
            print(f"  [/check] Sem results para {ticker} — ticker invalido.")
            return vazio
        ativo = results[0]
        fd    = ativo.get("financialData",        {}) or {}
        ks    = ativo.get("defaultKeyStatistics", {}) or {}

        vazio["ticker_validado"] = True
        vazio["nome"] = ativo.get("longName") or ativo.get("shortName") or ticker

        # ── Preço atual + timestamp da cotação ────────────────
        preco_raw = ativo.get("regularMarketPrice")
        if preco_raw is not None:
            vazio["preco_atual"] = (
                float(preco_raw) if not isinstance(preco_raw, dict) else _raw(preco_raw)
            )
        ts_raw = ativo.get("regularMarketTime")
        if ts_raw is not None:
            try:
                from datetime import datetime as _dt
                ts_val = int(ts_raw) if not isinstance(ts_raw, dict) else int(_raw(ts_raw))
                vazio["timestamp_cotacao"] = _dt.fromtimestamp(
                    ts_val, tz=pytz.timezone("America/Sao_Paulo")
                ).strftime("%d/%m/%Y %H:%M")
            except Exception:
                vazio["timestamp_cotacao"] = str(ts_raw)[:16]

        # ── ROE ──────────────────────────────────────────────────
        roe_raw = _raw(fd.get("returnOnEquity") or ks.get("returnOnEquity"))
        if roe_raw is not None:
            vazio["roe"] = round(roe_raw * 100, 2)

        # ── P/L ──────────────────────────────────────────────────
        pl_raw = _raw(ks.get("trailingPE"))
        if pl_raw is not None:
            vazio["pl"] = round(pl_raw, 1)

        # ── Volume médio ─────────────────────────────────────────
        vol_raw = _raw(
            ativo.get("averageDailyVolume10Day") or ativo.get("averageVolume")
        )
        if vol_raw is not None:
            vazio["volume_medio_20d"] = vol_raw

        # ── Séries trimestrais via incomeStatementHistoryQuarterly ─
        def _raw_val(v):
            if v is None: return None
            if isinstance(v, dict): return v.get("raw")
            try: return float(v)
            except: return None

        def _periodo_fmt(stmt):
            end_raw = stmt.get("endDate") or stmt.get("date") or stmt.get("period", "")
            if isinstance(end_raw, dict):
                end_raw = end_raw.get("fmt", "") or str(end_raw.get("raw", ""))
            s = str(end_raw)[:10]
            try:
                from datetime import datetime as _d
                d = _d.strptime(s, "%Y-%m-%d")
                return f"{(d.month-1)//3+1}T{str(d.year)[2:]}"
            except:
                return s[:5]

        def _extrai_serie(modulo_dict, campo, alt=None, max_t=8):
            stmts = []
            for chave in ("incomeStatementHistory", "statements", "history"):
                if chave in modulo_dict:
                    stmts = modulo_dict[chave]
                    break
            out = []
            for stmt in stmts[:max_t]:
                c   = campo if campo in stmt else (alt or campo)
                val = _raw_val(stmt.get(c))
                if val is not None:
                    out.append({"periodo": _periodo_fmt(stmt), "valor": val})
            return out

        is_q = _normalizar_modulo(
            ativo.get("incomeStatementHistoryQuarterly"),
            "incomeStatementHistory",
        )

        # Receita trimestral
        rec_t = _extrai_serie(is_q, "totalRevenue")
        if rec_t:
            vazio["receita_4t"] = rec_t

        # Margem Bruta: grossProfit / totalRevenue
        gp  = _extrai_serie(is_q, "grossProfit")
        rec = _extrai_serie(is_q, "totalRevenue")
        if gp and rec:
            mr   = {x["periodo"]: x["valor"] for x in rec}
            mb_t = [
                {"periodo": x["periodo"],
                 "valor"  : round(x["valor"] / mr[x["periodo"]] * 100, 1)}
                for x in gp if mr.get(x["periodo"])
            ]
            if mb_t:
                vazio["margem_bruta_4t"] = mb_t

        # Margem Líquida: netIncome / totalRevenue
        ni = _extrai_serie(is_q, "netIncome")
        if ni:
            vazio["lucro_liquido_4t"] = ni          # valores absolutos R$
        if ni and rec:
            mr   = {x["periodo"]: x["valor"] for x in rec}
            ml_t = [
                {"periodo": x["periodo"],
                 "valor"  : round(x["valor"] / mr[x["periodo"]] * 100, 1)}
                for x in ni if mr.get(x["periodo"])
            ]
            if ml_t:
                vazio["margem_liquida_4t"] = ml_t

        n_rec = len(vazio["receita_4t"])
        print(
            f"  [/check] {ticker}: ROE={vazio['roe']}% P/L={vazio['pl']} "
            f"| trim: rec={n_rec}T mgb={len(vazio['margem_bruta_4t'])}T "
            f"mgl={len(vazio['margem_liquida_4t'])}T"
        )
        return vazio
    except Exception as erro:
        print(f"  [/check] Excecao ao buscar {ticker}: {erro}")
        return vazio


# ============================================================
# SEÇÃO 3.8 — STREAK DE QUEDAS CUMULATIVAS (v8.2)
# Regras: 3 dias <= -6% OU 4 dias <= -8% -> alerta STREAK
# ============================================================

def _calcular_streak(ticker: str, historico: list) -> tuple:
    """
    Analisa historico.json e retorna (ativou, soma_pct, n_dias).
    ativou   : True se alguma regra STREAK foi atingida
    soma_pct : variacao acumulada no periodo detectado
    n_dias   : numero de pregoes analisados
    """
    if not STREAK_ATIVO:
        return False, 0.0, 0
    registros = [
        r for r in historico
        if r.get("tipo") == "cotacao"
        and r.get("ticker") == ticker
        and r.get("variacao_pct") is not None
    ]
    if not registros:
        return False, 0.0, 0
    # 1 registro por pregao (mais recente primeiro)
    from collections import OrderedDict
    por_dia: dict = OrderedDict()
    for reg in sorted(registros, key=lambda x: x.get("data", ""), reverse=True):
        dia = reg["data"][:10]
        if dia not in por_dia:
            por_dia[dia] = reg.get("variacao_pct", 0.0)
    variacoes = list(por_dia.values())
    for janela, limiar in STREAK_REGRAS:
        if len(variacoes) < janela:
            continue
        soma = sum(variacoes[:janela])
        if soma <= limiar:
            print(
                f"  [Streak] {ticker}: {janela}d = {soma:+.1f}%"
                f" (<= {limiar}%) — ALERTA STREAK"
            )
            return True, round(soma, 1), janela
    return False, 0.0, 0


def enviar_alerta_streak(
    ticker: str,
    preco_atual: float,
    soma_pct: float,
    n_dias: int,
    score: float,
    score_labels: list,
    filtro_labels: list,
):
    """Envia alerta de queda cumulativa (streak) no Telegram."""
    classificacao = _classificar_score(score)
    badges_str    = " | ".join(filtro_labels)
    score_resumo  = " | ".join(score_labels[:3]) if score_labels else ""
    sep = chr(8212)  # —
    nl  = "\n"
    linha = chr(9472) * 30  # ─────
    mensagem = (
        f"\U0001f4c9 STREAK {sep} {ticker}{nl}"
        f"{linha}{nl}"
        f"Preco  : R$ {preco_atual:.2f}{nl}"
        f"Streak : {soma_pct:+.1f}% em {n_dias} pregoes{nl}{nl}"
        f"Score  : {score:.1f}/10 {classificacao}{nl}"
        f"Filtros: {badges_str}{nl}"
        f"({score_resumo}){nl}{nl}"
        f"Atencao: queda acumulada detectada.{nl}"
        f"Verifique fundamentos antes de decidir."
    )
    teclado = {
        "inline_keyboard": [[
            {"text": "\u2705 Comprei", "callback_data": f"comprei|{ticker}"}
        ]]
    }
    _enviar_mensagem(TELEGRAM_CHAT_ID, mensagem, reply_markup=teclado)
    print(
        f"  Alerta STREAK enviado: {ticker} "
        f"({soma_pct:+.1f}% em {n_dias}d | Score: {score}/10)"
    )


# ============================================================

# ============================================================
# SEÇÃO 3.9b — BUSCA TICKER POR NOME DE EMPRESA (v8.4)
# Permite /check Vale ou /check Petrobras além de /check PETR4
# ============================================================

# Mapa de nomes comuns → tickers (expanda conforme necessário)
_MAPA_NOMES: dict = {
    "petrobras": ["PETR3", "PETR4"],
    "vale":      ["VALE3"],
    "itau":      ["ITUB3", "ITUB4"],
    "bradesco":  ["BBDC3", "BBDC4"],
    "banco do brasil": ["BBAS3"],
    "bb":        ["BBAS3"],
    "weg":       ["WEGE3"],
    "taesa":     ["TAEE11", "TAEE3", "TAEE4"],
    "copel":     ["CPLE3", "CPLE6"],
    "eletrobras":["ELET3", "ELET6"],
    "prio":      ["PRIO3"],
    "equatorial":["EQTL3"],
    "rumo":      ["RAIL3"],
    "b3":        ["B3SA3"],
    "embraer":   ["EMBR3"],
    "gerdau":    ["GGBR3", "GGBR4"],
    "ambev":     ["ABEV3"],
    "localiza":  ["RENT3"],
    "magazine":  ["MGLU3"],
    "magalu":    ["MGLU3"],
    "totvs":     ["TOTS3"],
    "raia drogasil": ["RADL3"],
    "rd":        ["RADL3"],
    "hapvida":   ["HAPV3"],
    "intermédica": ["GNDI3"],
    "suzano":    ["SUZB3"],
    "klabin":    ["KLBN11", "KLBN3", "KLBN4"],
    "lojas renner": ["LREN3"],
    "renner":    ["LREN3"],
    "natura":    ["NTCO3"],
    "multi":     ["MULT3"],
    "multiplan": ["MULT3"],
}

def _resolver_ticker_por_nome(texto: str) -> tuple:
    """
    Tenta resolver 'texto' como ticker direto ou nome de empresa.

    Retorna
    -------
    ("direto",   [ticker])           → ticker reconhecido diretamente
    ("nome",     [t1, t2, ...])      → nome mapeado para 1+ tickers
    ("nenhum",   [])                 → não reconhecido
    """
    texto_clean = texto.strip().upper()

    # 1. Parece ticker direto? (3-6 chars alfanuméricos)
    import re as _re
    if _re.match(r"^[A-Z]{3,6}[0-9]{1,2}$", texto_clean):
        return ("direto", [texto_clean])

    # 2. Busca no mapa de nomes (case-insensitive, partial match)
    texto_lower = texto.strip().lower()
    candidatos  = []
    for chave, tickers in _MAPA_NOMES.items():
        if texto_lower in chave or chave in texto_lower:
            candidatos.extend(tickers)
    # Remove duplicatas mantendo ordem
    candidatos = list(dict.fromkeys(candidatos))
    if candidatos:
        return ("nome", candidatos)

    # 3. Não reconhecido
    return ("nenhum", [])

# SEÇÃO 3.9 — COMANDO /check: ANÁLISE FUNDAMENTALISTA (v8.2)
# ============================================================

def executar_check(chat_id: str, ticker: str):
    """
    /check TICKER — busca fundamentos completos e envia tabela
    de analise no Telegram. 1 chamada HTTP + veredito conservador.
    Aceito somente do TELEGRAM_CHAT_ID autorizado.
    """
    ticker = ticker.strip().upper()
    print(f"  [/check] Iniciando analise: {ticker}")
    _enviar_mensagem(chat_id, f"\U0001f50d Buscando dados de {ticker}... aguarde.")
    fund = _obter_fundamentalistas_completo(ticker)
    if not fund["ticker_validado"]:
        nl = "\n"
        _enviar_mensagem(
            chat_id,
            f"\u274c Ticker {ticker} nao encontrado na brapi.{nl}"
            f"Verifique o codigo (ex: PETR4, VALE3, MXRF11).{nl}"
            f"Tickers de FIIs costumam ter 11 (ex: MXRF11)."
        )
        return

    def fmt_brl(val):
        if val is None: return "N/D"
        if abs(val) >= 1e9: return f"R$ {val/1e9:.1f}B"
        if abs(val) >= 1e6: return f"R$ {val/1e6:.1f}M"
        return f"R$ {val:,.0f}"

    def fmt_pct(val):
        return f"{val:.1f}%" if val is not None else "N/D"

    def fmt_num(val, casas=1):
        return f"{val:.{casas}f}" if val is not None else "N/D"

    # Veredito conservador (buy-and-hold)
    # Usa apenas dados disponíveis no plano gratuito brapi:
    #   1. ROE ≥ 12%           (defaultKeyStatistics)
    #   2. P/L razoável < 30   (defaultKeyStatistics)
    #   3. Margem Bruta > 0    (incomeStatementHistoryQuarterly — média últimos 4T)
    #   4. Margem Líquida > 0  (incomeStatementHistoryQuarterly — média últimos 4T)
    pontos_ok  = 0
    pontos_max = 4
    alertas    = []

    # 1. ROE
    roe = fund["roe"]
    if roe is not None:
        if roe >= 12: pontos_ok += 1
        else:         alertas.append(f"ROE baixo ({roe:.1f}% < 12%)")
    else:
        pontos_max -= 1

    # 2. P/L
    pl = fund["pl"]
    if pl is not None:
        if pl < 30: pontos_ok += 1
        else:       alertas.append(f"P/L elevado ({pl:.1f} > 30) — valuation esticado")
    else:
        pontos_max -= 1

    # 3. Margem Bruta média dos últimos 4 trimestres
    mgb_4t = fund.get("margem_bruta_4t", [])
    if mgb_4t:
        mg_med = sum(x["valor"] for x in mgb_4t[:4]) / min(len(mgb_4t), 4)
        if mg_med > 0: pontos_ok += 1
        else:          alertas.append(f"Margem bruta negativa ({mg_med:.1f}%)")
    else:
        pontos_max -= 1

    # 4. Margem Líquida média dos últimos 4 trimestres
    mgl_4t = fund.get("margem_liquida_4t", [])
    if mgl_4t:
        ml_med = sum(x["valor"] for x in mgl_4t[:4]) / min(len(mgl_4t), 4)
        if ml_med > 0: pontos_ok += 1
        else:          alertas.append(f"Margem liquida negativa ({ml_med:.1f}%)")
    else:
        pontos_max -= 1

    ratio = pontos_ok / pontos_max if pontos_max > 0 else 0
    if ratio >= 0.8:
        veredito_bh = "\u2705 Fundamentalmente ATRATIVO para buy-and-hold"
        veredito_ms = "\u2705 Margem de seguranca: parametros OK"
    elif ratio >= 0.6:
        veredito_bh = "\U0001f440 MODERADO — acompanhar antes de alocar"
        veredito_ms = "\u26a0\ufe0f  Margem de seguranca: pontos de atencao"
    else:
        veredito_bh = "\u26a0\ufe0f  CAUTELA — fundamentos com pontos criticos"
        veredito_ms = "\u274c Margem de seguranca: insuficiente no momento"

    alertas_str = ("\n".join(
        f"  • {a}" for a in alertas)
    ) if alertas else "  Nenhum alerta critico"

    agora_str  = _agora_brt().strftime("%d/%m/%Y %H:%M")
    ts_cotacao = fund.get("timestamp_cotacao") or agora_str
    preco_str  = (
        f"R$ {fund['preco_atual']:.2f}"
        if fund.get("preco_atual") is not None
        else "N/D"
    )
    nl  = "\n"
    sep = chr(9472) * 32

    # ── Helpers de formatação compacta para tabela ────────────
    def _fb(v):
        if v is None: return " N/D"
        if abs(v) >= 1e9:  return f"{v/1e9:+.1f}B"
        if abs(v) >= 1e6:  return f"{v/1e6:+.0f}M"
        return f"{v:+.0f}"

    def _fp(v):
        if v is None: return " N/D"
        return f"{v:+.1f}%"

    def _tabela_rich(serie, tipo="valor"):
        """
        Grade compacta 2 anos x 4 trimestres, com QoQ e YoY.
        serie — [{periodo, valor}, ...] mais recente primeiro
        tipo  — "valor" (variacao %) | "margem" (diferenca em pp)
        Colunas: 1T  2T  3T  4T  | Total/Media
        Linhas : 'AA  val val val val  tot
                 'BB  val val val val  tot
                 QoQ  --  dx% dx% dx%
                 YoY  dx% dx% dx% dx%  dx%
        """
        if not serie:
            return ""

        def _parse(p):
            try:
                return 2000 + int(p[2:]), int(p[0])
            except Exception:
                return None, None

        # Formata valor absoluto de forma compacta (sem sinal para receita)
        def _fv(v):
            if v is None:
                return "─"
            neg = v < 0
            av  = abs(v)
            if   av >= 100e9: s = f"{av/1e9:.0f}B"
            elif av >= 10e9:  s = f"{av/1e9:.1f}B"
            elif av >= 1e9:   s = f"{av/1e9:.2f}B"
            elif av >= 100e6: s = f"{av/1e6:.0f}M"
            elif av >= 10e6:  s = f"{av/1e6:.1f}M"
            elif av >= 1e6:   s = f"{av/1e6:.2f}M"
            else:             s = f"{av:.0f}"
            return f"-{s}" if neg else s

        def _fm(v):
            return "─" if v is None else f"{v:.1f}%"

        def _fpct(v):
            if v is None:
                return "─"
            return f"{'↑' if v >= 0 else '↓'}{abs(v):.0f}%"

        def _fpp(v):
            if v is None:
                return "─"
            return f"{'↑' if v >= 0 else '↓'}{abs(v):.1f}p"

        fval   = _fm   if tipo == "margem" else _fv
        fdelta = _fpp  if tipo == "margem" else _fpct

        # Montar grade: {(ano, q): valor}
        grade = {}
        for x in serie:
            a, q = _parse(x["periodo"])
            if a and q:
                grade[(a, q)] = x["valor"]
        if not grade:
            return ""

        # 2 anos mais recentes com dados
        anos = sorted({a for a, _ in grade})[-2:]
        qs   = [1, 2, 3, 4]

        # Total por ano (soma para valor; media para margem)
        def _tot(ano):
            vs = [grade[(ano, q)] for q in qs if (ano, q) in grade]
            if not vs:
                return None
            return sum(vs) / len(vs) if tipo == "margem" else sum(vs)

        # Linha de valores por ano
        rows = {
            ano: [fval(grade.get((ano, q))) for q in qs]
            for ano in anos
        }
        tots = {ano: _tot(ano) for ano in anos}

        # Linha QoQ — percorre 1T→4T dentro do ano mais recente
        ano_r = anos[-1]
        qoq   = []
        prev  = None
        for q in qs:
            v = grade.get((ano_r, q))
            if v is None:
                qoq.append("─")
            elif prev is None:
                qoq.append("base")
                prev = v
            else:
                if tipo == "margem":
                    qoq.append(_fpp(v - prev))
                elif prev != 0:
                    qoq.append(_fpct((v - prev) / abs(prev) * 100))
                else:
                    qoq.append("─")
                prev = v

        # Linha YoY — mesmo trimestre, ano anterior vs ano atual
        yoy = []
        if len(anos) == 2:
            ano_a = anos[0]
            for q in qs:
                va = grade.get((ano_a, q))
                vr = grade.get((ano_r, q))
                if va is None or vr is None:
                    yoy.append("─")
                elif tipo == "margem":
                    yoy.append(_fpp(vr - va))
                elif va != 0:
                    yoy.append(_fpct((vr - va) / abs(va) * 100))
                else:
                    yoy.append("─")

        # YoY total: compara mesmos trimestres disponíveis em ano_r
        yoy_tot = ""
        if len(anos) == 2:
            qs_r  = {q for q in qs if (ano_r, q) in grade}
            t_r   = tots.get(ano_r)
            vs_as = [grade[(anos[0], q)] for q in qs if q in qs_r
                     and (anos[0], q) in grade]
            if t_r is not None and vs_as:
                t_as = (
                    sum(vs_as) / len(vs_as)
                    if tipo == "margem"
                    else sum(vs_as)
                )
                if t_as != 0:
                    yoy_tot = (
                        " " + _fpp(t_r - t_as)
                        if tipo == "margem"
                        else " " + _fpct((t_r - t_as) / abs(t_as) * 100)
                    )

        # Larguras de coluna: max de header / todos os valores / QoQ / YoY
        hdr = ["1T", "2T", "3T", "4T"]
        all_for_w = [hdr, qoq, *rows.values()]
        if yoy:
            all_for_w.append(yoy)
        col_w = [
            max(len(r[i]) for r in all_for_w) + 1
            for i in range(4)
        ]

        def _row(label, vals, sufixo=""):
            cells = " ".join(v.ljust(c) for v, c in zip(vals, col_w))
            return f"{label:<5}{cells}{sufixo}".rstrip()

        # Sufixo de total para cada ano
        def _suf(ano):
            t = tots.get(ano)
            return "" if t is None else f" {fval(t)}"

        # Emoji de tendência para o final das linhas delta (sem quebrar colunas)
        def _trend(vals):
            up = sum(1 for v in vals if "↑" in v)
            dn = sum(1 for v in vals if "↓" in v)
            if up > dn: return " 🟢"
            if dn > up: return " 🔴"
            return ""

        # Montar saída
        linhas = [_row("    ", hdr)]
        for ano in anos:
            linhas.append(_row(f"'{str(ano)[2:]}:", rows[ano], _suf(ano)))
        linhas.append(_row("QoQ ", qoq) + _trend(qoq))
        if yoy:
            linhas.append(_row("YoY ", yoy, yoy_tot) + _trend(yoy))
        return nl.join(linhas)

    # ── Monta bloco trimestral ────────────────────────────────
    rec_4t = fund.get("receita_4t", [])
    ll_4t  = fund.get("lucro_liquido_4t", [])
    mgb_4t = fund.get("margem_bruta_4t", [])
    mgl_4t = fund.get("margem_liquida_4t", [])

    bloco_t = []

    if rec_4t:
        bloco_t.append("Receita (R$)")
        bloco_t.append(_tabela_rich(rec_4t))

    if ll_4t:
        if bloco_t:
            bloco_t.append("")
        bloco_t.append("Lucro Liq (R$)")
        bloco_t.append(_tabela_rich(ll_4t))

    if mgb_4t:
        if bloco_t:
            bloco_t.append("")
        bloco_t.append("Margem Bruta (%)")
        bloco_t.append(_tabela_rich(mgb_4t, tipo="margem"))

    if mgl_4t:
        if bloco_t:
            bloco_t.append("")
        bloco_t.append("Margem Liquida (%)")
        bloco_t.append(_tabela_rich(mgl_4t, tipo="margem"))

    if not bloco_t:
        # Dados trimestrais não disponíveis para esse ticker
        print(f"  [/check] {ticker}: SEM dados trimestrais na brapi")
        bloco_t = ["Dados trimestrais indisponiveis para este ticker."]

    bloco_t_str = nl.join(bloco_t)

    # HTML-escape para parse_mode=HTML (evita quebra se nome tiver &, <, >)
    def _he(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    sep2 = chr(9472) * 20   # separador mais curto que o sep global (32)

    msg = (
        f"\U0001f4ca /check {_he(ticker)}{nl}"
        f"{_he(fund['nome'])}{nl}"
        f"{sep2}{nl}"
        f"Cotacao : R$ {_he(preco_str)}  ({_he(ts_cotacao)} BRT){nl}"
        f"Consulta: {_he(agora_str)} BRT{nl}"
        f"{sep2}{nl}{nl}"
        f"▸ TRIMESTRAL{nl}"
        f"<pre>{_he(bloco_t_str)}</pre>{nl}"
        f"▸ MULTIPLOS{nl}"
        f"ROE : {_he(fmt_pct(fund['roe']))}{nl}"
        f"P/L : {_he(fmt_num(fund['pl']))}{nl}{nl}"
        f"▸ VEREDITO{nl}"
        f"{_he(veredito_bh)}{nl}"
        f"{_he(veredito_ms)}{nl}{nl}"
        f"Criterios: {pontos_ok}/{pontos_max} OK{nl}"
        f"Alertas:{nl}{_he(alertas_str)}{nl}{nl}"
        f"{sep2}{nl}"
        f"brapi.dev / Yahoo Finance"
    )
    teclado_check = {
        "inline_keyboard": [[
            {"text": "✅ Comprei", "callback_data": f"comprei|{ticker}"}
        ]]
    }
    _enviar_mensagem_fatiada(chat_id, msg, parse_mode="HTML", reply_markup=teclado_check)
    print(
        f"  [/check] Analise enviada: {ticker} "
        f"| Score {pontos_ok}/{pontos_max} | ratio={ratio:.0%}"
    )

# ============================================================
# SEÇÃO 4 — ALERTAS E MENSAGENS NO TELEGRAM
# ============================================================

def _enviar_mensagem(chat_id: str, texto: str,
                     reply_markup: dict = None,
                     parse_mode: str = None) -> dict:
    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text"   : texto,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code != 200:
            print(f"  Erro Telegram [{resp.status_code}]: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as erro:
        print(f"  Exceção ao enviar mensagem Telegram: {erro}")
        return {}


def _enviar_mensagem_fatiada(chat_id: str, texto: str,
                              tamanho_max: int = 4000,
                              parse_mode: str = None,
                              reply_markup: dict = None):
    """Envia mensagens longas em múltiplas partes sem quebrar linhas.
    O reply_markup (ex: botão inline) é enviado apenas no último chunk."""
    if len(texto) <= tamanho_max:
        _enviar_mensagem(chat_id, texto, parse_mode=parse_mode, reply_markup=reply_markup)
        return

    linhas  = texto.split("\n")
    bloco   = []
    atual   = 0
    parte   = 1

    for linha in linhas:
        tamanho_linha = len(linha) + 1
        if atual + tamanho_linha > tamanho_max and bloco:
            _enviar_mensagem(chat_id, "\n".join(bloco), parse_mode=parse_mode)
            print(f"  [Fatiado] Parte {parte} enviada ({atual} chars).")
            bloco = []
            atual = 0
            parte += 1
            time.sleep(0.5)

        bloco.append(linha)
        atual += tamanho_linha

    if bloco:
        _enviar_mensagem(chat_id, "\n".join(bloco), parse_mode=parse_mode, reply_markup=reply_markup)
        print(f"  [Fatiado] Parte {parte} (final) enviada ({atual} chars).")


def _enviar_foto(chat_id: str, imagem_bytes: bytes, legenda: str = ""):
    """Envia imagem PNG via Telegram sendPhoto (multipart)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        resp = requests.post(
            url,
            data   = {"chat_id": chat_id, "caption": legenda},
            files  = {"photo": ("grafico.png", imagem_bytes, "image/png")},
            timeout= 20,
        )
        if resp.status_code != 200:
            print(f"  [Foto] Erro Telegram [{resp.status_code}]: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as erro:
        print(f"  [Foto] Exceção ao enviar foto: {erro}")
        return {}


def enviar_alerta_queda(
    ticker: str,
    preco_atual: float,
    variacao_pct: float,
    score: float,
    score_labels: list,
    filtro_labels: list,
    motivo: str,
):
    """
    Monta e envia alerta de queda no Telegram com Score + badges de qualidade.

    Exemplo de cabeçalho gerado:
      Score: 7.8/10 ⭐ FORTE
      Volume 2.1x média | FCF positivo | DY 6.5%

    Parâmetros:
        ticker        : símbolo do ativo (ex: "PETR4")
        preco_atual   : preço no momento da queda
        variacao_pct  : variação percentual hoje (negativo)
        score         : float 0-10 calculado por calcular_score()
        score_labels  : lista de detalhes do score (componente → pontos)
        filtro_labels : badges do filtro de qualidade aprovado
        motivo        : texto completo com resultado da Perplexity
    """
    classificacao = _classificar_score(score)

    # ── Linha de badges de qualidade ─────────────────────────
    badges_str = " | ".join(filtro_labels)

    # ── Resumo dos componentes do score (máx 3 para não poluir) ──
    score_resumo = " | ".join(score_labels[:3]) if score_labels else ""

    sep30    = "─" * 30
    mensagem = (
        f"🔻 QUEDA — {ticker}\n"
        f"{sep30}\n"
        f"Preço  : R$ {preco_atual:.2f}\n"
        f"Var.   : {variacao_pct:+.1f}% hoje\n\n"
        f"🎯 Score: {score:.1f}/10 {classificacao}\n"
        f"📌 {badges_str}\n"
        f"({score_resumo})\n\n"
        f"📊 Análise rápida:\n{motivo}\n"
    )

    teclado = {
        "inline_keyboard": [[
            {
                "text"         : "✅ Comprei",
                "callback_data": f"comprei|{ticker}"
            }
        ]]
    }

    _enviar_mensagem(TELEGRAM_CHAT_ID, mensagem, reply_markup=teclado)
    print(f"  Alerta enviado: {ticker} ({variacao_pct:+.1f}% | Score: {score}/10)")


def _responder_callback(callback_query_id: str, texto: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
            data={"callback_query_id": callback_query_id, "text": texto},
            timeout=10
        )
    except Exception as erro:
        print(f"  Erro ao responder callback: {erro}")


# ============================================================
# SEÇÃO 5 — CÁLCULO DE IR
# ============================================================

def calcular_ir(
    preco_entrada,
    preco_saida,
    quantidade,
    data_entrada,
    data_saida,
    corretagem=None,
    vendas_mes=0.0
):
    if corretagem is None:
        corretagem = CORRETAGEM_PADRAO

    fmt        = "%Y-%m-%d %H:%M"
    dt_entrada = datetime.strptime(data_entrada, fmt)
    dt_saida   = datetime.strptime(data_saida,   fmt)

    mesmo_dia = (dt_entrada.date() == dt_saida.date())
    tipo_op   = "day-trade" if mesmo_dia else "swing"

    valor_compra  = preco_entrada * quantidade
    valor_venda   = preco_saida   * quantidade
    lucro_bruto   = valor_venda - valor_compra
    lucro_liquido = lucro_bruto - corretagem

    if tipo_op == "day-trade":
        aliquota       = 0.20
        isento         = False
        motivo_isencao = "Day-trade não tem isenção, independente do valor."
    else:
        aliquota = 0.15
        isento   = (vendas_mes < 20_000.0)
        if isento:
            motivo_isencao = (
                f"Vendas no mês: R$ {vendas_mes:,.2f} — "
                f"abaixo de R$ 20.000 → ISENTO"
            )
        else:
            motivo_isencao = (
                f"Vendas no mês: R$ {vendas_mes:,.2f} — "
                f"acima de R$ 20.000 → TRIBUTADO"
            )

    if lucro_liquido <= 0:
        ir_devido     = 0.0
        observacao_ir = (
            f"Prejuízo de R$ {abs(lucro_liquido):,.2f}. "
            "Guarde este registro para compensar em ganhos futuros."
        )
    elif isento:
        ir_devido     = 0.0
        observacao_ir = (
            "Operação ISENTA de IR "
            "(vendas do mês abaixo de R$ 20.000). "
            "Verifique com seu contador se esta é a única venda no mês."
        )
    else:
        ir_devido     = lucro_liquido * aliquota
        observacao_ir = (
            "DARF deve ser pago até o último dia útil do mês seguinte. "
            "Código DARF: 6015 (renda variável — pessoa física). "
            "Acesse o site da Receita Federal → e-CAC → DARF."
        )

    primeiro_prox_mes = (dt_saida.replace(day=28) + timedelta(days=4)).replace(day=1)
    prazo_darf        = primeiro_prox_mes.strftime("%m/%Y")

    return {
        "ticker"         : "—",
        "tipo_operacao"  : tipo_op,
        "quantidade"     : quantidade,
        "preco_entrada"  : preco_entrada,
        "preco_saida"    : preco_saida,
        "valor_compra"   : valor_compra,
        "valor_venda"    : valor_venda,
        "corretagem"     : corretagem,
        "lucro_bruto"    : lucro_bruto,
        "lucro_liquido"  : lucro_liquido,
        "isento"         : isento,
        "aliquota_pct"   : aliquota * 100,
        "ir_devido"      : ir_devido,
        "prazo_darf"     : prazo_darf,
        "motivo_isencao" : motivo_isencao,
        "observacao_ir"  : observacao_ir,
        "data_calculo"   : _agora_brt().strftime("%Y-%m-%d %H:%M"),
    }


def enviar_resumo_venda_telegram(ticker: str, resultado_ir: dict):
    r = resultado_ir

    if r["isento"]:
        bloco_ir = "✅ IR: ISENTO (vendas do mês abaixo de R$ 20.000)"
    elif r["ir_devido"] == 0 and r["lucro_liquido"] < 0:
        bloco_ir = "IR: R$ 0,00 (prejuízo — guarde para compensar futuramente)"
    else:
        bloco_ir = (
            f"💰 IR ({r['aliquota_pct']:.0f}% {r['tipo_operacao']}): "
            f"R$ {r['ir_devido']:,.2f}\n"
            f"📅 Prazo DARF: até o último dia útil de {r['prazo_darf']}\n"
            f"Código DARF: 6015"
        )

    sinal    = "✅ LUCRO" if r["lucro_liquido"] >= 0 else "🔻 PREJUÍZO"
    sep30    = "─" * 30
    mensagem = (
        f"📋 RESUMO DE VENDA — {ticker}\n"
        f"{sep30}\n"
        f"Tipo: {r['tipo_operacao'].upper()}\n"
        f"Quantidade: {r['quantidade']} ações\n\n"
        f"Compra : R$ {r['preco_entrada']:.2f}/ação "
        f"(total R$ {r['valor_compra']:,.2f})\n"
        f"Venda  : R$ {r['preco_saida']:.2f}/ação "
        f"(total R$ {r['valor_venda']:,.2f})\n"
        f"Corretagem: R$ {r['corretagem']:.2f}\n\n"
        f"{sinal}\n"
        f"Lucro bruto  : R$ {r['lucro_bruto']:,.2f}\n"
        f"Lucro líquido: R$ {r['lucro_liquido']:,.2f}\n\n"
        f"{bloco_ir}\n\n"
        f"ℹ️ {r['motivo_isencao']}\n"
        f"{r['observacao_ir']}"
    )

    _enviar_mensagem(TELEGRAM_CHAT_ID, mensagem)
    print(f"  Resumo de venda enviado: {ticker} | "
          f"IR: R$ {resultado_ir['ir_devido']:,.2f}")


# ============================================================
# SEÇÃO 6 — REGISTRO DE POSIÇÕES (posicoes.json)
# ============================================================

def _carregar_posicoes() -> list:
    try:
        with open(ARQUIVO_POSICOES, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _salvar_posicoes(posicoes: list):
    with open(ARQUIVO_POSICOES, "w", encoding="utf-8") as f:
        json.dump(posicoes, f, indent=2, ensure_ascii=False)


def registrar_posicao(ticker: str, preco: float, quantidade: int):
    posicoes = _carregar_posicoes()

    nova_posicao = {
        "ticker"       : ticker,
        "preco_entrada": preco,
        "quantidade"   : quantidade,
        "data_entrada" : _agora_brt().strftime("%Y-%m-%d %H:%M"),
        "status"       : "aberta",
        "ir_devido"    : None
    }

    posicoes.append(nova_posicao)
    _salvar_posicoes(posicoes)

    print(f"  ✅ Posição registrada: {ticker} | "
          f"{quantidade}x R$ {preco:.2f} | "
          f"Total: R$ {preco * quantidade:,.2f}")


def fechar_posicao(ticker: str, preco_saida: float,
                   resultado_ir: dict) -> bool:
    posicoes = _carregar_posicoes()
    fechou   = False

    for pos in posicoes:
        if pos["ticker"] == ticker and pos["status"] == "aberta":
            pos["status"]        = "fechada"
            pos["preco_saida"]   = preco_saida
            pos["data_saida"]    = _agora_brt().strftime("%Y-%m-%d %H:%M")
            pos["lucro_bruto"]   = resultado_ir["lucro_bruto"]
            pos["lucro_liquido"] = resultado_ir["lucro_liquido"]
            pos["tipo_operacao"] = resultado_ir["tipo_operacao"]
            pos["aliquota_pct"]  = resultado_ir["aliquota_pct"]
            pos["ir_devido"]     = resultado_ir["ir_devido"]
            pos["prazo_darf"]    = resultado_ir["prazo_darf"]
            pos["isento_ir"]     = resultado_ir["isento"]
            pos["roi_pct"]       = round(
                ((preco_saida - pos["preco_entrada"]) / pos["preco_entrada"]) * 100, 2
            )
            fechou             = True
            preco_entrada_orig = pos["preco_entrada"]
            quantidade_orig    = pos.get("quantidade", 1)
            break

    if fechou:
        _salvar_posicoes(posicoes)
        print(f"  Posição fechada: {ticker} | "
              f"IR: R$ {resultado_ir['ir_devido']:,.2f}")
        resultado_ir["preco_saida"] = preco_saida
        registrar_fechamento_historico(
            ticker        = ticker,
            resultado_ir  = resultado_ir,
            preco_entrada = preco_entrada_orig,
            quantidade    = quantidade_orig
        )
    else:
        print(f"  Nenhuma posição aberta encontrada para {ticker}")

    return fechou


# ============================================================
# SEÇÃO 7 — PROCESSADOR DE UPDATES DO TELEGRAM (polling)
# ============================================================

def _buscar_updates() -> list:
    global _ULTIMO_UPDATE_ID

    url    = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {
        "offset" : _ULTIMO_UPDATE_ID + 1,
        # long polling: Telegram segura a conexão até 10s
        # e responde imediatamente quando chega um update.
        # Elimina o delay de ~5s do polling curto.
        "timeout": 10,
    }

    try:
        # timeout do requests deve ser > timeout do long poll
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
    except Exception as erro:
        print(f"  Erro ao buscar updates Telegram: {erro}")
        return []

    if not data.get("ok"):
        return []

    updates = data.get("result", [])

    if updates:
        _ULTIMO_UPDATE_ID = updates[-1]["update_id"]

    return updates


def _processar_callback(update: dict):
    query    = update.get("callback_query", {})
    dados    = query.get("data", "").split("|")
    query_id = query.get("id", "")

    msg_chat = query.get("message", {}).get("chat", {}).get("id")
    from_id  = query.get("from", {}).get("id")
    chat_id  = str(msg_chat or from_id or TELEGRAM_CHAT_ID)

    if not dados or not dados[0]:
        return

    acao   = dados[0]
    ticker = dados[1] if len(dados) > 1 else "?"

    _responder_callback(query_id, f"Registrando compra de {ticker}...")

    if acao == "comprei":
        ESTADO_CONVERSA[chat_id] = {
            "ticker"    : ticker,
            "tentativas": 0,
        }
        print(f"  Usuário clicou Comprei: {ticker}. Aguardando preço e qtd...")

        # Se ticker não estiver na watchlist, insere automaticamente
        wl = carregar_watchlist()
        if ticker not in wl:
            if len(wl) < WATCHLIST_MAX:
                wl.append(ticker)
                salvar_watchlist(wl)
                print(f"  [callback] {ticker} adicionado à watchlist via Comprei.")
            else:
                print(f"  [callback] Watchlist cheia ({WATCHLIST_MAX}). {ticker} nao adicionado.")

        _enviar_mensagem(
            chat_id,
            f"📥 Registro de compra — {ticker}\n\n"
            f"Digite o preço médio pago e a quantidade, separados por espaço:\n"
            f"Formato: PRECO QUANTIDADE\n"
            f"Exemplos: 38.50 100   |   38,50 200"
        )

    else:
        print(f"  Callback desconhecido: {dados}")


def _enviar_ajuda(chat_id: str):
    """Envia menu de todos os comandos disponíveis."""
    sep = "─" * 32
    msg = "\n".join([
        "📖 COMANDOS DISPONÍVEIS",
        sep,
        "/check TICKER    — análise fundamentalista",
        "   Ex: /check PETR4",
        "   Ex: /check Petrobras",
        "",
        "/add TICKER      — adicionar à watchlist",
        "   Ex: /add MGLU3",
        "   Ex: /add MGLU3,COGN3",
        "",
        "/remove TICKER   — remover da watchlist",
        "   Ex: /remove MGLU3",
        "",
        "/watchlist       — listar tickers monitorados",
        "/limit           — ver uso do plano brapi",
        "",
        "/datascience SENHA — análise de portfólio",
        "",
        "VENDI TICKER PRECO QTD — registrar venda",
        "   Ex: VENDI PETR4 39.10 100",
        "",
        "/ajuda ou /?     — este menu",
        "/glossario       — termos e critérios explicados",
    ])
    _enviar_mensagem(chat_id, msg)


def _enviar_glossario(chat_id: str):
    """Envia glossário de termos financeiros e critérios do /check."""
    sep = "─" * 29
    msg = "\n".join([
        "📚 GLOSSÁRIO — TERMOS DO MONITOR B3",
        sep,
        "",
        "─INDICADORES DA TABELA TRIMESTRAL─",
        "",
        "Receita (R$)",
        "  Tudo que a empresa faturou no período.",
        "  Ex: Receita de R$ 2,54B no 1T24 = R$ 2,54 bilhões no 1º trimestre de 2024.",
        "",
        "FCF — Fluxo de Caixa Livre (R$)",
        "  Dinheiro que sobrou depois de pagar os investimentos (máquinas, expansão etc).",
        "  FCF positivo = empresa gera caixa; negativo = está consumindo reservas.",
        "  Ex: FCF de +500M significa que sobraram R$ 500 milhões no caixa.",
        "",
        "Margem Bruta (%)",
        "  De cada R$ 1,00 faturado, quanto sobra depois de pagar os custos de produção.",
        "  Ex: Margem Bruta de 45% = R$ 0,45 sobram de cada R$ 1,00 vendido.",
        "",
        "Margem Líquida (%)",
        "  De cada R$ 1,00 faturado, quanto vira lucro final (após todos os custos e impostos).",
        "  Ex: Margem Líquida de 10% = R$ 0,10 de lucro por cada R$ 1,00 vendido.",
        "",
        "QoQ — Quarter over Quarter (variação trimestral)",
        "  Compara o resultado do trimestre com o trimestre imediatamente anterior.",
        "  Ex: QoQ +3% na Receita = faturou 3% a mais que no trimestre passado.",
        "",
        "YoY — Year over Year (variação anual)",
        "  Compara o mesmo trimestre do ano atual com o do ano anterior.",
        "  Ex: YoY +17% = faturou 17% a mais no 1T25 vs o mesmo 1T24.",
        "",
        "YTD — Year to Date (acumulado do ano)",
        "  Soma dos trimestres já encerrados no ano corrente.",
        "  Ex: YTD 2025 (2T): R$ 2,1B = soma do 1T25 + 2T25.",
        "",
        "pp — Pontos Percentuais",
        "  Diferença entre dois valores percentuais (não é % de variação, é subtração direta).",
        "  Ex: Margem subiu de 30% para 33% = +3pp (não 10%).",
        "",
        "── MÚLTIPLOS E INDICADORES TTM ──",
        "",
        "TTM — Trailing Twelve Months (últimos 12 meses)",
        "  Soma ou média dos últimos 4 trimestres, independente do ano-calendário.",
        "  Ex: Receita TTM de R$ 5B = somou os últimos 4 trimestres disponíveis.",
        "",
        "ROE — Return on Equity (Retorno sobre Patrimônio)",
        "  Mede o quanto a empresa lucra comparado ao dinheiro que os acionistas investiram.",
        "  Critério: ROE >= 12% é considerado satisfatório.",
        "  Ex: ROE de 15% = para cada R$ 100 de patrimônio, gera R$ 15 de lucro por ano.",
        "",
        "DL/EBITDA — Dívida Líquida / EBITDA",
        "  Quantos anos de geração de caixa operacional seriam necessários para pagar a dívida.",
        "  Critério: DL/EBITDA < 1,8x é considerado saudável.",
        "  Ex: DL/EBITDA de 1,2x = em ~1,2 anos de operação a empresa quitaria toda a dívida.",
        "",
        "EBITDA",
        "  Lucro antes de juros, impostos, depreciação e amortização. Mede a eficiência operacional.",
        "  Ex: EBITDA de R$ 3B com Receita de R$ 10B = 30% de margem operacional.",
        "",
        "DY — Dividend Yield (%)",
        "  % do preço atual da ação que foi pago em dividendos no último ano.",
        "  Critério: DY >= 5% é considerado atrativo.",
        "  Ex: DY de 8% com ação a R$ 10 = pagou R$ 0,80 em dividendos por ação no ano.",
        "",
        "P/L — Preço / Lucro",
        "  Quantos anos de lucro atual seriam necessários para pagar o preço da ação.",
        "  Ex: P/L de 10 = ao preço atual, levaria 10 anos de lucro para recuperar o investimento.",
        "",
        "── OS 5 CRITÉRIOS DO /check ──",
        "",
        "O /check avalia 5 critérios e gera um veredito. Quando alguma métrica não está",
        "disponível (N/D), ela é excluída — por isso você pode ver '2/3 OK' em vez de 'X/5 OK'.",
        "",
        "Critério 1: FCF positivo",
        "  A empresa precisa gerar mais caixa do que consome. FCF negativo indica risco.",
        "",
        "Critério 2: DL/EBITDA < 1,8x",
        "  Dívida controlada. Acima de 1,8x a empresa pode ter dificuldade em cenário adverso.",
        "",
        "Critério 3: ROE >= 12%",
        "  Rentabilidade mínima. Abaixo de 12% o capital estaria melhor em renda fixa.",
        "",
        "Critério 4: Margem Bruta > 0%",
        "  Verificação básica: a empresa não pode vender abaixo do custo de produção.",
        "",
        "Critério 5: DY >= 5%",
        "  Remuneração ao acionista. Abaixo de 5% pode indicar que a empresa não distribui bem.",
        "",
        "── VEREDITO ──",
        "",
        "ATRATIVO  — >= 80% dos critérios OK  (ex: 4/5 ou 5/5)",
        "MODERADO  — 60% a 79% dos critérios OK  (ex: 3/5)",
        "CAUTELA   — < 60% dos critérios OK  (ex: 1/5 ou 2/5)",
        "",
        "── OUTROS TERMOS ──",
        "",
        "B3",
        "  Bolsa de Valores do Brasil, onde as ações são negociadas.",
        "  Ex: PETR4, VALE3, ITUB4 são ações listadas na B3.",
        "",
        "Ticker / Código de Ação",
        "  Código de 4 letras + número que identifica a ação na bolsa.",
        "  3 = ação ordinária (ON); 4 = ação preferencial (PN); 11 = FII ou ETF.",
        "  Ex: PETR4 = Petrobras Preferencial.",
        "",
        "Watchlist",
        "  Lista de ações que o monitor acompanha automaticamente.",
        "  Ex: /add PETR4 adiciona Petrobras à sua watchlist.",
        "",
        sep,
        "Use /check TICKER para ver a análise completa de qualquer ação.",
    ])
    _enviar_mensagem_fatiada(chat_id, msg)


def _processar_mensagem_texto(update: dict):
    """
    Processa mensagens de texto enviadas pelo usuário.

    Caso A — Fluxo de compra ativo (ESTADO_CONVERSA preenchido):
      Formato: "PRECO QUANTIDADE" → ex: "38.50 100"
      Máximo 3 tentativas antes de cancelar.

    Caso B — Comando de venda por texto:
      Formato: VENDI TICKER PRECO QUANTIDADE [VENDAS_MES]

    Caso C — Comando /datascience (v8.7+):
      Formato: /datascience SENHA

    Caso D — Adicionar tickers (v8.1):
      Formato: /add TICKER1,TICKER2  ou  /add TICKER1 TICKER2

    Caso E — Remover ticker (v8.1):
      Formato: /remove TICKER

    Caso F — Listar/status (v8.1):
      Formato: /watchlist  ou  /limit

    Caso G — /check (v8.4): ticker direto, nome ou desambiguação.
    Caso H — /ajuda ou /?: menu de comandos.
    Fallback — texto não reconhecido: orienta com /ajuda.
    """
    MAX_TENTATIVAS = 3

    message = update.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", TELEGRAM_CHAT_ID))
    texto   = message.get("text", "").strip()

    if not texto:
        return

    # ── Segurança: comandos /add /remove /watchlist /limit
    #    só são aceitos do TELEGRAM_CHAT_ID autorizado
    chat_id_autorizado  = str(TELEGRAM_CHAT_ID)
    eh_comando_watchlist = texto.lower().startswith(
        ("/add", "/remove", "/watchlist", "/limit", "/check")
    )
    if eh_comando_watchlist and chat_id != chat_id_autorizado:
        print(f"  [Segurança] Comando watchlist ignorado: "
              f"chat_id {chat_id} não autorizado.")
        return

    # ── Pré-Caso A: resolve seleção de /check multi-ticker ──
    estado_raw = ESTADO_CONVERSA.get(chat_id, {})
    if estado_raw.get("tipo") == "pendente_check":
        candidatos = estado_raw.get("candidatos", [])
        escolha    = texto.strip().upper()
        ticker_esc = None

        # Usuário digitou número (1, 2, 3…)
        if escolha.isdigit():
            idx_esc = int(escolha) - 1
            if 0 <= idx_esc < len(candidatos):
                ticker_esc = candidatos[idx_esc]

        # Usuário digitou o ticker diretamente
        if ticker_esc is None and escolha in candidatos:
            ticker_esc = escolha

        if ticker_esc:
            del ESTADO_CONVERSA[chat_id]
            executar_check(chat_id, ticker_esc)
            return
        else:
            opcoes_str = "  ".join(
                f"{i+1}.{t}" for i, t in enumerate(candidatos)
            )
            _enviar_mensagem(
                chat_id,
                f"Opção inválida. Escolha: {opcoes_str}"
            )
            return

    # ── Caso A: fluxo de compra ativo ──────────────────────
    estado = ESTADO_CONVERSA.get(chat_id)

    if estado:
        ticker     = estado.get("ticker", "?")
        tentativas = estado.get("tentativas", 0) + 1

        erro_parse = None
        preco      = None
        quantidade = None

        partes_compra = texto.split()
        if len(partes_compra) < 2:
            erro_parse = "Preciso de dois valores: PRECO e QUANTIDADE."
        else:
            try:
                preco = float(partes_compra[0].replace(",", "."))
                if preco <= 0:
                    raise ValueError
            except ValueError:
                erro_parse = (
                    f"Preço inválido: '{partes_compra[0]}'."
                    " Use número positivo (ex: 38.50)."
                )

            if erro_parse is None:
                try:
                    qtd_str    = partes_compra[1].replace(".", "").replace(",", "")
                    quantidade = int(qtd_str)
                    if quantidade <= 0:
                        raise ValueError
                except ValueError:
                    erro_parse = (
                        f"Quantidade inválida: '{partes_compra[1]}'."
                        " Use número inteiro positivo (ex: 100)."
                    )

        if erro_parse:
            if tentativas >= MAX_TENTATIVAS:
                del ESTADO_CONVERSA[chat_id]
                _enviar_mensagem(
                    chat_id,
                    f"❌ Registro de {ticker} cancelado após {MAX_TENTATIVAS} tentativas.\n"
                    f"Se quiser registrar manualmente, edite posicoes.json."
                )
                print(f"  Fluxo de compra cancelado ({ticker}): máx tentativas atingido.")
            else:
                restantes = MAX_TENTATIVAS - tentativas
                ESTADO_CONVERSA[chat_id]["tentativas"] = tentativas
                _enviar_mensagem(
                    chat_id,
                    f"⚠️ {erro_parse}\n\n"
                    f"Tente novamente ({restantes} tentativa(s) restante(s)):\n"
                    f"Formato: PRECO QUANTIDADE\n"
                    f"Exemplo: 38.50 100"
                )
                print(f"  Erro parse compra {ticker} "
                      f"(tentativa {tentativas}/{MAX_TENTATIVAS}): {erro_parse}")
            return

        registrar_posicao(ticker, preco, quantidade)
        del ESTADO_CONVERSA[chat_id]

        total = preco * quantidade
        _enviar_mensagem(
            chat_id,
            f"✅ Posição registrada com sucesso!\n\n"
            f"📌 {ticker}\n"
            f"   Preço médio : R$ {preco:.2f}/ação\n"
            f"   Quantidade  : {quantidade} ações\n"
            f"Salvo em posicoes.json. ✔\n\n"
            f"Para registrar a venda futuramente, envie:\n"
            f"VENDI {ticker} PRECO QUANTIDADE [VENDAS_MES]\n"
            f"Ex: VENDI {ticker} {preco*1.15:.2f} {quantidade} {total*1.15:.0f}"
        )
        print(f"  ✅ Compra registrada: {ticker} {quantidade}x R$ {preco:.2f} "
              f"= R$ {total:,.2f}")
        return

    # ── Caso C: comando /datascience ────────────────────────
    texto_lower = texto.lower()
    if texto_lower.startswith("/datascience"):
        print(f"  [DataScience] Comando detectado de chat_id={chat_id}")
        executar_datascience(chat_id, texto)
        return

    # ── Caso D: /add — adicionar tickers à watchlist (v8.4) ──
    if texto_lower.startswith("/add"):
        resto = texto[4:].strip()
        if not resto:
            _enviar_mensagem(
                chat_id,
                "⚠️ Uso: /add TICKER1,TICKER2\n"
                "Exemplos:\n"
                "  /add MGLU3\n"
                "  /add MGLU3,COGN3,BBDC4"
            )
            return

        # Normaliza: vírgula ou espaço → lista upper sem duplicatas
        candidatos = list(dict.fromkeys(
            t.strip().upper()
            for t in resto.replace(",", " ").split()
            if t.strip()
        ))

        watchlist_atual = carregar_watchlist()

        # ── Pré-filtros sem chamar API ──────────────────────
        ja_existem  = [t for t in candidatos if t in watchlist_atual]
        novos       = [t for t in candidatos if t not in watchlist_atual]
        vagas_livres = WATCHLIST_MAX - len(watchlist_atual)
        sem_vaga    = novos[vagas_livres:]   # excede limite
        novos       = novos[:vagas_livres]

        if not novos:
            partes_msg = []
            if ja_existem:
                partes_msg.append(f"ℹ️ Já na watchlist: {', '.join(ja_existem)}")
            if sem_vaga:
                partes_msg.append(
                    f"❌ Limite {WATCHLIST_MAX} atingido. "
                    f"Não adicionados: {', '.join(sem_vaga)}"
                )
            _enviar_mensagem(chat_id, "\n".join(partes_msg) or "❌ Nada a adicionar.")
            return

        # ── Validação em lote: 1 chamada brapi para todos ──
        _enviar_mensagem(
            chat_id,
            f"🔍 Validando {len(novos)} ticker(s) na B3... aguarde."
        )
        validos, invalidos = validar_tickers_em_lote(novos, apenas_acoes=True)

        # Comportamento atômico: qualquer inválido → não adiciona nenhum
        if invalidos:
            inv_str = ", ".join(invalidos)
            extra   = ""
            if ja_existem:
                extra = f"\nℹ️ Já existiam: {', '.join(ja_existem)}"
            _enviar_mensagem(
                chat_id,
                f"❌ Ticker(s) inválido(s) ou não é ação B3: {inv_str}\n"
                f"Nenhum ticker foi adicionado.\n"
                f"Corrija e tente novamente.{extra}"
            )
            return

        # Tudo válido → adiciona
        for t in validos:
            watchlist_atual.append(t)
        salvar_watchlist(watchlist_atual)
        print(f"  [Watchlist] +{validos} → total {len(watchlist_atual)}")

        partes_msg = [
            f"✅ Adicionado(s): {', '.join(validos)} "
            f"(total: {len(watchlist_atual)}/{WATCHLIST_MAX})"
        ]
        if ja_existem:
            partes_msg.append(f"ℹ️ Já existiam: {', '.join(ja_existem)}")
        if sem_vaga:
            partes_msg.append(
                f"⚠️ Limite atingido, ignorados: {', '.join(sem_vaga)}"
            )
        _enviar_mensagem(chat_id, "\n".join(partes_msg))
        return

    # ── Caso E: /remove — remover ticker da watchlist ───────
    if texto_lower.startswith("/remove"):
        partes_rm = texto.upper().split()
        if len(partes_rm) < 2:
            _enviar_mensagem(
                chat_id,
                "⚠️ Uso: /remove TICKER\nExemplo: /remove MGLU3"
            )
            return

        ticker_rm    = partes_rm[1].strip()
        watchlist_rm = carregar_watchlist()

        if ticker_rm not in watchlist_rm:
            _enviar_mensagem(
                chat_id,
                f"⚠️ {ticker_rm} não está na watchlist.\nUse /watchlist para ver a lista atual."
            )
            return

        watchlist_rm.remove(ticker_rm)
        salvar_watchlist(watchlist_rm)
        print(f"  [Watchlist] -{ticker_rm} (total: {len(watchlist_rm)})")
        print(f"  Watchlist atualizada via Telegram: "
              f"-1 → total {len(watchlist_rm)}")
        _enviar_mensagem(
            chat_id,
            f"🗑️ Removido: {ticker_rm} (total: {len(watchlist_rm)})"
        )
        return

    # ── Caso F1: /watchlist — listar tickers atuais ─────────
    if texto_lower.startswith("/watchlist"):
        wl = carregar_watchlist()
        linhas_wl = [f"📋 Watchlist atual ({len(wl)}/{WATCHLIST_MAX}):"]
        for i, t in enumerate(wl, 1):
            linhas_wl.append(f"  {i:2d}. {t}")
        linhas_wl.append("\nUso: /add TICKER | /remove TICKER | /limit")
        _enviar_mensagem(chat_id, "\n".join(linhas_wl))
        return

    # ── Caso F2: /limit — tamanho atual vs. máximo ──────────
    if texto_lower.startswith("/limit"):
        wl    = carregar_watchlist()
        usado = len(wl)
        livre = WATCHLIST_MAX - usado
        preenchido = usado * 20 // WATCHLIST_MAX
        barra = "█" * preenchido + "░" * (20 - preenchido)
        _enviar_mensagem(
            chat_id,
            f"[{barra}]\n"
            f"Usado : {usado}/{WATCHLIST_MAX} tickers\n"
            f"Livre : {livre} slots disponíveis\n\n"
            f"Plano free brapi: até {WATCHLIST_MAX} tickers recomendado.\n"
            f"Use /add TICKER para adicionar."
        )
        return

    # ── Caso G: /check — análise fundamentalista (v8.4) ──────
    # Aceita: /check PETR4 | /check Petrobras | /check vale
    if texto_lower.startswith("/check"):
        argumento = texto[6:].strip()   # tudo após "/check"
        if not argumento:
            _enviar_mensagem(
                chat_id,
                "⚠️ Uso: /check TICKER ou /check NomeEmpresa\n"
                "Exemplos:\n"
                "  /check VALE3\n"
                "  /check Petrobras\n"
                "  /check Vale"
            )
            return

        modo, candidatos = _resolver_ticker_por_nome(argumento)

        if modo == "nenhum":
            # Argumento não parece ticker nem nome conhecido
            # Tenta direto na brapi (pode ser ticker incomum)
            executar_check(chat_id, argumento)
            return

        if modo == "direto" or len(candidatos) == 1:
            executar_check(chat_id, candidatos[0])
            return

        # Múltiplos tickers → pergunta qual o usuário quer
        ESTADO_CONVERSA[chat_id] = {
            "tipo"       : "pendente_check",
            "candidatos" : candidatos,
        }
        opcoes_str = "\n".join(
            f"  {i+1}. {t}" for i, t in enumerate(candidatos)
        )
        _enviar_mensagem(
            chat_id,
            f"Encontrei {len(candidatos)} tickers para "
            f"\"{argumento}\":\n{opcoes_str}\n\n"
            f"Responda com o número ou o ticker desejado.\n"
            f"Ex: 1  ou  {candidatos[0]}"
        )
        return

    # ── Caso I: /ajuda e /? — menu de comandos ───────────────
    if texto_lower.startswith("/ajuda") or texto_lower.startswith("/?"):
        _enviar_ajuda(chat_id)
        return

    # ── Caso I: /glossario — termos financeiros ──────────────
    if texto_lower.startswith("/glossario"):
        _enviar_glossario(chat_id)
        return

    # ── Caso B: comando de venda por texto ──────────────────
    partes = texto.upper().split()

    if len(partes) >= 4 and partes[0] == "VENDI":
        try:
            ticker      = partes[1]
            preco_saida = float(partes[2].replace(",", "."))
            quantidade  = int(partes[3].replace(".", "").replace(",", ""))
            vendas_mes  = float(partes[4].replace(",", ".")) if len(partes) >= 5 else 0.0
        except (ValueError, IndexError):
            _enviar_mensagem(
                chat_id,
                "⚠️  Formato inválido. Use:\n"
                "VENDI TICKER PRECO QUANTIDADE VENDAS_MES\n\n"
                "Exemplos:\n"
                "VENDI VALE3 58.40 100 15000.00\n"
                "VENDI PETR4 39.10 200"
            )
            return

        posicoes   = _carregar_posicoes()
        pos_aberta = next(
            (p for p in posicoes
             if p["ticker"] == ticker and p["status"] == "aberta"),
            None
        )

        if not pos_aberta:
            _enviar_mensagem(
                chat_id,
                f"⚠️  Nenhuma posição aberta para {ticker}.\n"
                f"Verifique posicoes.json."
            )
            print(f"  Venda recebida mas sem posição aberta: {ticker}")
            return

        resultado = calcular_ir(
            preco_entrada = pos_aberta["preco_entrada"],
            preco_saida   = preco_saida,
            quantidade    = quantidade,
            data_entrada  = pos_aberta["data_entrada"],
            data_saida    = _agora_brt().strftime("%Y-%m-%d %H:%M"),
            corretagem    = CORRETAGEM_PADRAO,
            vendas_mes    = vendas_mes
        )
        resultado["ticker"] = ticker

        fechar_posicao(ticker, preco_saida, resultado)
        enviar_resumo_venda_telegram(ticker, resultado)


    # ── Fallback: texto não reconhecido ──────────────────────
    # Chega aqui somente se NÃO entrou em nenhum caso acima
    # (não é VENDI, não é compra em andamento, não é /comando)
    comandos_validos = (
        "/add", "/remove", "/watchlist", "/limit",
        "/check", "/ajuda", "/?", "/datascience", "vendi",
    )
    eh_cmd_conhecido = any(
        texto_lower.startswith(c) for c in comandos_validos
    )
    # Formato compra "38.50 100" também é válido (dois números)
    eh_formato_compra = (
        len(texto.split()) == 2
        and all(
            p.replace(".", "").replace(",", "").isdigit()
            for p in texto.split()
        )
    )
    if not eh_cmd_conhecido and not eh_formato_compra and not estado:
        _enviar_mensagem(
            chat_id,
            f"❓ Não entendi \"{texto[:60]}\"\n\n"
            "Digite /ajuda para ver os comandos disponíveis."
        )
        print(f"  [Fallback] Mensagem não reconhecida: {texto[:60]!r}")

def processar_updates(updates: list):
    """Dispatcher principal de updates do Telegram."""
    for update in updates:
        try:
            if "callback_query" in update:
                _processar_callback(update)
            elif "message" in update:
                _processar_mensagem_texto(update)
        except Exception as erro:
            print(f"  Erro ao processar update "
                  f"{update.get('update_id', '?')}: {erro}")


# ============================================================
# SEÇÃO 8 — LOOP PRINCIPAL DE MONITORAMENTO
# ============================================================

def monitorar_watchlist(intervalo_minutos: int = 15):
    print("=" * 60)
    print("  Monitor de Quedas B3  (v8.6 — Evolução trimestral 4T no /check)")
    print(f"  Limiar de queda    : {LIMIAR_QUEDA_PCT}%")
    print(f"  Intervalo pregão   : {intervalo_minutos} min")
    print(f"  Horário pregão     : {PREGAO_HORA_INICIO}h-{PREGAO_HORA_FIM}h BRT (seg-sex)")
    filtro_status = "ATIVO" if FILTRO_QUALIDADE_ATIVO else "DESATIVADO"
    print(
        f"  Filtro qualidade   : {filtro_status} "
        f"(Volume ≥{VOLUME_MINIMO_MULTIPLICADOR}x + FCF positivo)"
    )
    print(f"  Cache Sonar TTL    : {CACHE_SONAR_TTL_SEGUNDOS/3600:.0f}h")
    print(f"  Arquivo posições   : {ARQUIVO_POSICOES}")
    print(f"  Arquivo histórico  : {ARQUIVO_HISTORICO}")
    perp_status = "✅ ok" if PERPLEXITY_API_KEY else "⚠️  NÃO configurada"
    print(f"  Perplexity Sonar   : {perp_status}")
    print("=" * 60)

    while True:
        agora_str = _agora_brt().strftime("%d/%m/%Y %H:%M:%S BRT")
        print(f"\n[{agora_str}] Verificando...")

        # ── Polling Telegram ──────────────────────────────────
        updates = _buscar_updates()
        if updates:
            print(f"  {len(updates)} update(s) recebido(s) do Telegram.")
            processar_updates(updates)

        # ── Checa se mercado está aberto ──────────────────────
        mercado_aberto, _ts = checar_mercado_aberto()

        if not mercado_aberto:
            agora_brt     = _agora_brt()
            fora_horario  = not (PREGAO_HORA_INICIO <= agora_brt.hour < PREGAO_HORA_FIM)
            fim_de_semana = agora_brt.weekday() >= 5

            if fim_de_semana or fora_horario:
                print("  Mercado fechado (fora do horário/fim de semana).")
            else:
                print("  Mercado fechado (timestamps congelados).")

            segundos_total = calcular_espera_ate_proximo_pregao()
            fim_sleep      = time.time() + segundos_total

            while time.time() < fim_sleep:
                # long poll retorna em até 10s, sem sleep manual necessário
                upds = _buscar_updates()
                if upds:
                    print(f"  {len(upds)} update(s) recebido(s) fora do pregão.")
                    processar_updates(upds)

            continue

        # ── Mercado aberto: busca cotações ────────────────────
        print("  Mercado aberto. Buscando watchlist completa...")
        tickers  = carregar_watchlist()
        cotacoes = buscar_cotacoes(tickers)

        if not cotacoes:
            print("  Nenhuma cotação retornada. Verifique o token brapi.")
        else:
            registrar_cotacao_historico(cotacoes)

            print(f"\n  {'TICKER':<7} {'PRECO':>8}  {'VAR%':>7}  {'VOLUME':>14}")
            print("  " + "─"*7 + " " + "─"*8 + "  " + "─"*7 + "  " + "─"*14)

            for ativo in cotacoes:
                variacao = ativo.get("variacao_pct") or 0.0
                ticker   = ativo["symbol"]
                preco    = ativo["preco"]
                volume   = ativo.get("volume") or 0

                flag = " <<< ALERTA" if variacao <= LIMIAR_QUEDA_PCT else ""
                print(f"  {ticker:<7} R${preco:>7.2f}  "
                      f"{variacao:>+6.1f}%  {volume:>14,}{flag}")

                # ── Alerta de queda detectado ─────────────────
                if variacao <= LIMIAR_QUEDA_PCT:

                    # 0. Limite diário: no máximo 2 alertas por ticker por dia
                    hoje_str  = _agora_brt().strftime("%Y-%m-%d")
                    reg_a     = _CONTAGEM_ALERTAS_QUEDA.get(ticker, {"data": "", "count": 0})
                    if reg_a["data"] != hoje_str:
                        reg_a = {"data": hoje_str, "count": 0}
                    if reg_a["count"] >= 2:
                        print(f"  [{ticker}] Limite de 2 alertas/dia atingido. Ignorando.")
                        continue

                    # 1. Busca fundamentalistas (FCF, ROE, DY, VolMed)
                    fund = buscar_fundamentalistas(ticker)

                    # 2. Filtro de qualidade (volume alto + FCF positivo)
                    passa_filtro, filtro_labels = verificar_filtro_qualidade(
                        ticker       = ticker,
                        volume_atual = volume,
                        fund         = fund,
                    )

                    if not passa_filtro:
                        print(f"  [{ticker}] Alerta BLOQUEADO pelo filtro de qualidade.")
                        continue  # Não envia alerta para este ativo

                    # 3. Calcula score de oportunidade (0-10)
                    score, score_labels = calcular_score(
                        variacao_pct       = variacao,
                        preco_atual        = preco,
                        fund               = fund,
                        volume_atual       = volume,
                        fifty_two_week_low = ativo.get("fifty_two_week_low"),
                        fifty_two_week_high= ativo.get("fifty_two_week_high"),
                    )
                    print(f"  [{ticker}] Score: {score}/10 — {_classificar_score(score)}")

                    # 4. Consulta Perplexity (com cache TTL 6h)
                    motivo_perplexity = consultar_perplexity(ticker, variacao)

                    # 5. Monta motivo completo
                    motivo = (
                        f"Queda de {variacao:+.1f}% detectada hoje.\n"
                        f"Volume negociado: {volume:,}\n\n"
                        f"{motivo_perplexity}"
                    )

                    # 6. Envia alerta enriquecido
                    enviar_alerta_queda(
                        ticker        = ticker,
                        preco_atual   = preco,
                        variacao_pct  = variacao,
                        score         = score,
                        score_labels  = score_labels,
                        filtro_labels = filtro_labels,
                        motivo        = motivo,
                    )

                    # Incrementa contador diário de alertas para este ticker
                    reg_a["count"] += 1
                    _CONTAGEM_ALERTAS_QUEDA[ticker] = reg_a

        # ── Deteccao de streak pos-ciclo (v8.2) ──────────────
        if STREAK_ATIVO and cotacoes:
            historico_atual = _carregar_historico()
            print("  Verificando streaks de quedas acumuladas...")
            for ativo_s in cotacoes:
                tk   = ativo_s["symbol"]
                pr   = ativo_s["preco"]
                vol  = ativo_s.get("volume") or 0
                ativou, soma, n_dias = _calcular_streak(tk, historico_atual)
                if not ativou:
                    # Streak terminou: remove flag para alertar no próximo streak
                    if tk in _STREAKS_ALERTADOS:
                        print(f"  [Streak] {tk}: streak encerrado. Flag removida.")
                        _STREAKS_ALERTADOS.discard(tk)
                    continue
                if tk in _STREAKS_ALERTADOS:
                    print(f"  [Streak] {tk}: streak já alertado. Aguardando reset.")
                    continue
                fund_s = buscar_fundamentalistas(tk)
                passa_s, filtro_s = verificar_filtro_qualidade(
                    ticker       = tk,
                    volume_atual = vol,
                    fund         = fund_s,
                )
                if not passa_s:
                    print(f"  [Streak] {tk}: BLOQUEADO pelo filtro.")
                    continue
                var_s = ativo_s.get("variacao_pct") or 0.0
                score_s, slabels_s = calcular_score(
                    variacao_pct        = var_s,
                    preco_atual         = pr,
                    fund                = fund_s,
                    volume_atual        = vol,
                    fifty_two_week_low  = ativo_s.get("fifty_two_week_low"),
                    fifty_two_week_high = ativo_s.get("fifty_two_week_high"),
                )
                enviar_alerta_streak(
                    ticker        = tk,
                    preco_atual   = pr,
                    soma_pct      = soma,
                    n_dias        = n_dias,
                    score         = score_s,
                    score_labels  = slabels_s,
                    filtro_labels = filtro_s,
                )
                # Marca este streak como já alertado
                _STREAKS_ALERTADOS.add(tk)

        # ── Aguarda proximo ciclo (polling a cada 5s) ─────────
        prox      = _agora_brt() + timedelta(minutes=intervalo_minutos)
        fim_ciclo = time.time() + intervalo_minutos * 60
        print(f"\n  Próxima verificação em {intervalo_minutos} min "
              f"({prox.strftime('%H:%M')} BRT)...")

        while time.time() < fim_ciclo:
            # long poll retorna em até 10s ou imediatamente se houver update
            upds = _buscar_updates()
            if upds:
                print(f"  {len(upds)} update(s) recebido(s) durante espera.")
                processar_updates(upds)


# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    monitorar_watchlist(intervalo_minutos=30)
