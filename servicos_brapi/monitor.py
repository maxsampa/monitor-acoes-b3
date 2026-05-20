# ============================================================
# monitor.py — Monitor de Quedas B3 com Alertas no Telegram
# Projeto: Mauá Engenharia Industrial & IA
# Autor: gerado via Claude Sonnet 4.6
# Versão: 4.0 — detecção inteligente de pregão via timestamps brapi
#
# Novidades v4.0:
#   - Fuso horário correto via pytz (America/Sao_Paulo)
#   - Detecção de pregão aberto SEM lista fixa de feriados:
#       → usa regular_market_time da resposta brapi.dev
#       → se timestamp != hoje BRT → mercado fechado → dorme até 10h
#   - Primeira chamada leve (1 ticker) para checar timestamp antes
#     de buscar a watchlist completa (economiza tokens/quota)
#   - Pausa automática fora de seg-sex 10h-17h BRT
#   - Histórico acumulado em historico.json (cotações + fechamentos)
#   - Cálculo de IR e rastreamento de posições (posicoes.json)
# ============================================================

import os
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from brapi import Brapi
import pytz

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

BRAPI_API_KEY    = os.environ.get("BRAPI_API_KEY")
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Limiar de queda para disparar alerta (em %)
LIMIAR_QUEDA_PCT = -3.0      # -3% ou mais negativo -> alerta

# Arquivos de persistência
ARQUIVO_POSICOES  = "posicoes.json"
ARQUIVO_WATCHLIST = "watchlist.txt"
ARQUIVO_HISTORICO = "historico.json"

# Corretagem padrão por operação (em R$)
# Altere para o valor real da sua corretora (0.0 se for isenta)
CORRETAGEM_PADRAO = 0.0

# Fuso horário oficial da B3
TZ_BRT = pytz.timezone("America/Sao_Paulo")

# Horário de pregão B3 (seg-sex)
PREGAO_HORA_INICIO = 10   # 10h BRT
PREGAO_HORA_FIM    = 17   # 17h BRT (após 17h preços congelam)

# Ticker sentinela: 1 ticker leve para checar timestamp antes da watchlist completa
TICKER_SENTINELA = "PETR4"


# ============================================================
# SEÇÃO 1 — WATCHLIST
# ============================================================

def carregar_watchlist() -> list:
    """
    Lê os tickers da watchlist.
    Tenta primeiro o arquivo watchlist.txt (1 ticker por linha).
    Linhas começando com '#' são ignoradas (comentários).
    Se o arquivo não existir, usa a lista fixa de fallback.
    Retorna lista de tickers em maiúsculas, sem espaços.
    """
    lista_fixa = [
        "PETR4", "VALE3", "ITUB4", "BBAS3",
        "WEGE3", "TAEE11", "CPLE6", "ELET3",
        "PRIO3", "EQTL3", "RAIL3", "B3SA3"
    ]

    if os.path.exists(ARQUIVO_WATCHLIST):
        with open(ARQUIVO_WATCHLIST, "r", encoding="utf-8") as f:
            tickers = [
                linha.strip().upper()
                for linha in f
                if linha.strip() and not linha.startswith("#")
            ]
        if tickers:
            print(f"  Watchlist carregada do arquivo: {tickers}")
            return tickers

    print(f"  watchlist.txt não encontrado. Usando lista fixa.")
    return lista_fixa


# ============================================================
# SEÇÃO 2 — DETECÇÃO INTELIGENTE DE PREGÃO (via brapi timestamps)
# ============================================================

def _agora_brt() -> datetime:
    """Retorna o datetime atual já convertido para BRT (America/Sao_Paulo)."""
    return datetime.now(tz=TZ_BRT)


def _extrair_timestamp_brt(acao) -> datetime:
    """
    Extrai o timestamp mais recente de um objeto de cotação brapi.
    Tenta regular_market_time primeiro; fallback para
    regular_market_previous_close_time.
    Converte para datetime timezone-aware em BRT.
    Retorna None se nenhum campo estiver disponível.
    """
    ts = getattr(acao, "regular_market_time", None)
    if ts is None:
        ts = getattr(acao, "regular_market_previous_close_time", None)
    if ts is None:
        return None

    # ts pode ser: int (unix epoch), float, ou datetime já pronto
    if isinstance(ts, (int, float)):
        # Unix timestamp -> datetime UTC -> converte para BRT
        dt_utc = datetime.fromtimestamp(ts, tz=pytz.utc)
        return dt_utc.astimezone(TZ_BRT)

    if isinstance(ts, datetime):
        # Já é datetime — garante fuso, senão assume UTC
        if ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        return ts.astimezone(TZ_BRT)

    return None


def checar_mercado_aberto():
    """
    Verifica se o mercado B3 está realmente aberto hoje.

    Lógica em 3 camadas (da mais leve para a mais pesada):
    ──────────────────────────────────────────────────────
    Camada 1 (local, sem API):
      Se sáb/dom → fechado. Se fora de 10h-17h → fechado.

    Camada 2 (1 chamada leve à brapi com TICKER_SENTINELA):
      Extrai regular_market_time da resposta.
      Converte para BRT e compara com a data de hoje.

    Camada 3 (decisão por timestamp):
      Se timestamp == hoje → ABERTO, prossegue.
      Se timestamp != hoje → FECHADO (feriado ou preços congelados).

    Retorna:
        (True,  dt_brt)  → mercado aberto
        (False, dt_brt)  → mercado fechado, dt_brt pode ser None
    """
    agora = _agora_brt()

    # Camada 1a: fim de semana (sem API)
    if agora.weekday() >= 5:
        print(f"  Fim de semana ({agora.strftime('%A %d/%m')}).")
        return False, None

    # Camada 1b: fora do horário de pregão (sem API)
    if not (PREGAO_HORA_INICIO <= agora.hour < PREGAO_HORA_FIM):
        print(f"  Fora do horário de pregão ({agora.strftime('%H:%M')} BRT).")
        return False, None

    # Camada 2: chama brapi com 1 ticker para pegar timestamp real
    try:
        client   = Brapi(api_key=BRAPI_API_KEY)
        resposta = client.quote.retrieve(tickers=TICKER_SENTINELA)

        if not resposta.results:
            print("  brapi retornou lista vazia na checagem de sentinela.")
            return False, None

        dt_brt = _extrair_timestamp_brt(resposta.results[0])

        if dt_brt is None:
            # Timestamp indisponível: assume aberto para não bloquear
            print("  Aviso: timestamp indisponível na brapi. Assumindo aberto.")
            return True, None

        # Camada 3: compara data do timestamp com hoje BRT
        hoje_brt = agora.date()

        if dt_brt.date() == hoje_brt:
            print(f"  Timestamp brapi: {dt_brt.strftime('%d/%m/%Y %H:%M')} BRT "
                  f"-> mercado ABERTO hoje.")
            return True, dt_brt
        else:
            # Preços congelados: feriado ou entre pregões com timestamp do dia anterior
            print("  Preços congelados (fora pregão ou feriado). "
                  "Pulando chamada para economizar tokens.")
            print(f"  Último update brapi: {dt_brt.strftime('%d/%m/%Y %H:%M')} BRT "
                  f"!= hoje ({hoje_brt.strftime('%d/%m/%Y')}).")
            return False, dt_brt

    except Exception as erro:
        print(f"  Erro ao checar sentinela brapi: {erro}")
        return False, None


def calcular_espera_ate_proximo_pregao() -> float:
    """
    Calcula quantos segundos faltam até as 10h BRT do próximo
    dia útil (seg-sex).

    Exemplos práticos:
      - Sexta  17h30 -> segunda 10h00 (dorme ~64.5h)
      - Sábado 08h00 -> segunda 10h00 (dorme ~50h)
      - Segunda 07h  -> mesma segunda 10h00 (dorme 3h)
      - Feriado terça-> quarta 10h00 (re-verifica na manhã seguinte)
    """
    agora   = _agora_brt()
    proximo = agora.replace(hour=PREGAO_HORA_INICIO,
                            minute=0, second=0, microsecond=0)

    # Se já passamos das 10h de hoje -> avança para o dia seguinte
    if agora >= proximo:
        proximo += timedelta(days=1)

    # Pula fins de semana: sáb=5, dom=6
    while proximo.weekday() >= 5:
        proximo += timedelta(days=1)

    segundos = (proximo - agora).total_seconds()
    horas    = segundos / 3600
    print(f"  Dormindo {horas:.1f}h até próximo pregão: "
          f"{proximo.strftime('%d/%m/%Y %H:%M')} BRT")
    return segundos


# ============================================================
# SEÇÃO 2.5 — HISTÓRICO DE COTAÇÕES E FECHAMENTOS (historico.json)
# ============================================================
# Estrutura do historico.json:
# [
#   {                                     <- snapshot de mercado
#     "tipo"        : "cotacao",
#     "data"        : "2025-02-20 10:30",
#     "ticker"      : "VALE3",
#     "preco"       : 58.40,
#     "variacao_pct": -4.8,
#     "volume"      : 12345678
#   },
#   {                                     <- venda registrada
#     "tipo"         : "fechamento",
#     "data"         : "2025-02-20 14:00",
#     "ticker"       : "VALE3",
#     "preco_entrada": 55.00,
#     "preco_saida"  : 58.40,
#     "quantidade"   : 100,
#     "roi_pct"      : 6.18,
#     "lucro_liquido": 340.00,
#     "ir_devido"    : 0.00,
#     "tipo_operacao": "swing",
#     "isento"       : true
#   }
# ]
# ============================================================

def _carregar_historico() -> list:
    """Carrega historico.json. Retorna [] se não existir ou corrompido."""
    try:
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _salvar_historico(historico: list):
    """Persiste a lista de registros no arquivo historico.json."""
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)


def registrar_cotacao_historico(cotacoes: list):
    """
    Salva um snapshot de todas as cotações verificadas no ciclo atual.
    Chamada automaticamente SOMENTE quando mercado está aberto.

    Parâmetro:
        cotacoes: lista de dicts retornada por buscar_cotacoes()
    
    Campo extra: variacao_pct_dia_anterior
        Compara o preco atual com o último preco registrado para o mesmo
        ticker em historico.json. Se não houver registro anterior, salva null.
        Fórmula: (preco_atual - preco_anterior) / preco_anterior * 100
    """
    historico = _carregar_historico()
    agora     = _agora_brt().strftime("%Y-%m-%d %H:%M")

    # Monta índice {ticker: ultimo_preco} varrendo o histórico uma única vez
    # (evita O(n²) ao processar vários tickers em sequência)
    ultimo_preco: dict = {}
    for reg in historico:
        if reg.get("tipo") == "cotacao" and reg.get("preco") is not None:
            ultimo_preco[reg["ticker"]] = reg["preco"]

    for ativo in cotacoes:
        ticker      = ativo.get("symbol", "?")
        preco_atual = ativo.get("preco")

        # Calcula variação em relação ao último snapshot registrado
        preco_ant = ultimo_preco.get(ticker)
        if preco_ant is not None and preco_ant != 0 and preco_atual is not None:
            var_dia_ant = round((preco_atual - preco_ant) / preco_ant * 100, 4)
        else:
            var_dia_ant = None   # sem registro anterior para este ticker

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
    print(f"  -> {len(cotacoes)} cotações salvas em historico.json")


def registrar_fechamento_historico(ticker: str, resultado_ir: dict,
                                   preco_entrada: float, quantidade: int):
    """
    Salva o fechamento de uma posição no historico.json.
    Inclui ROI percentual e dados completos de IR.
    Chamada automaticamente dentro de fechar_posicao().
    """
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
    print(f"  -> Fechamento {ticker} salvo em historico.json "
          f"(ROI: {roi_pct:+.2f}% | IR: R$ {resultado_ir['ir_devido']:,.2f})")


# ============================================================
# SEÇÃO 3 — COTAÇÕES COMPLETAS (brapi.dev SDK oficial)
# ============================================================

def buscar_cotacoes(tickers: list) -> list:
    """
    Busca cotações em lote via SDK oficial da brapi.dev.
    Chamada SOMENTE quando checar_mercado_aberto() retorna True.
    Retorna lista de dicionários com os dados relevantes de cada ativo.
    """
    client      = Brapi(api_key=BRAPI_API_KEY)
    tickers_str = ",".join(tickers)

    try:
        resposta = client.quote.retrieve(tickers=tickers_str)
    except Exception as erro:
        print(f"  Erro ao buscar cotações na brapi.dev: {erro}")
        return []

    resultados = []
    for acao in resposta.results:
        resultados.append({
            "symbol"      : acao.symbol,
            "preco"       : acao.regular_market_price,
            "variacao_pct": acao.regular_market_change_percent,
            "volume"      : acao.regular_market_volume,
            "nome"        : acao.short_name,
        })

    return resultados


# ============================================================
# SEÇÃO 4 — ALERTA NO TELEGRAM (COMPRA)
# ============================================================

def enviar_alerta_compra(ticker: str, preco_atual: float,
                         variacao_pct: float, motivo: str):
    """
    Envia mensagem de alerta de queda no Telegram com botões inline:
      Comprei  |  Ignorei
    O callback_data carrega ticker + preco para registro automático.
    """
    mensagem = (
        f"ALERTA DE QUEDA - {ticker}\n"
        f"{'─' * 30}\n"
        f"Preco atual: R$ {preco_atual:.2f}\n"
        f"Variacao hoje: {variacao_pct:+.1f}%\n\n"
        f"Analise rapida:\n{motivo}\n\n"
        f"Isso NAO e recomendacao financeira profissional.\n"
        f"Faca sua propria analise e consulte um assessor certificado."
    )

    teclado = {
        "inline_keyboard": [[
            {
                "text"         : "Comprei",
                "callback_data": f"comprei|{ticker}|{preco_atual}"
            },
            {
                "text"         : "Ignorei",
                "callback_data": f"ignorei|{ticker}"
            }
        ]]
    }

    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id"     : TELEGRAM_CHAT_ID,
        "text"        : mensagem,
        "reply_markup": json.dumps(teclado)
    }

    resposta = requests.post(url, data=payload)

    if resposta.status_code == 200:
        print(f"  Alerta enviado: {ticker} ({variacao_pct:+.1f}%)")
    else:
        print(f"  Erro ao enviar alerta: {resposta.text}")


# ============================================================
# SEÇÃO 5 — CÁLCULO DE IR (IMPOSTO DE RENDA SOBRE GANHO)
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
    """
    Calcula lucro bruto, líquido e IR devido na venda de ações.

    Regras:
      - Day-trade (mesmo dia): alíquota 20%, nunca isento
      - Swing (mais de 1 dia): alíquota 15%
      - Isenção swing: vendas do mês < R$ 20.000
      - Prejuízo: IR = 0 (registra para compensação futura)

    Parâmetros:
        preco_entrada : preço médio de compra por ação (R$)
        preco_saida   : preço de venda por ação (R$)
        quantidade    : número de ações vendidas
        data_entrada  : data da compra  ("YYYY-MM-DD HH:MM")
        data_saida    : data da venda   ("YYYY-MM-DD HH:MM")
        corretagem    : custo total de corretagem (compra + venda)
        vendas_mes    : total em R$ vendido no mês corrente
    """
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
        motivo_isencao = "Day-trade nao tem isencao, independente do valor."
    else:
        aliquota = 0.15
        isento   = (vendas_mes < 20_000.0)
        if isento:
            motivo_isencao = (
                f"Vendas no mes: R$ {vendas_mes:,.2f} — "
                f"abaixo de R$ 20.000 -> ISENTO"
            )
        else:
            motivo_isencao = (
                f"Vendas no mes: R$ {vendas_mes:,.2f} — "
                f"acima de R$ 20.000 -> TRIBUTADO"
            )

    if lucro_liquido <= 0:
        ir_devido     = 0.0
        observacao_ir = (
            f"Prejuizo de R$ {abs(lucro_liquido):,.2f}. "
            "Guarde este registro para compensar em ganhos futuros."
        )
    elif isento:
        ir_devido     = 0.0
        observacao_ir = (
            "Operacao ISENTA de IR "
            "(vendas do mes abaixo de R$ 20.000). "
            "Verifique com seu contador se esta e a unica venda no mes."
        )
    else:
        ir_devido     = lucro_liquido * aliquota
        observacao_ir = (
            "DARF deve ser pago ate o ultimo dia util do mes seguinte. "
            "Codigo DARF: 6015 (renda variavel — pessoa fisica). "
            "Acesse: gov.br/receitafederal -> e-CAC -> DARF."
        )

    # Prazo DARF: mês seguinte ao da venda
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
    """
    Envia resumo completo da venda + cálculo de IR no Telegram.
    Inclui: lucro, IR, prazo DARF e disclaimer obrigatório.
    """
    r = resultado_ir

    if r["isento"]:
        bloco_ir = "IR: ISENTO (vendas do mes abaixo de R$ 20.000)"
    elif r["ir_devido"] == 0 and r["lucro_liquido"] < 0:
        bloco_ir = "IR: R$ 0,00 (prejuizo — guarde para compensar futuramente)"
    else:
        bloco_ir = (
            f"IR ({r['aliquota_pct']:.0f}% {r['tipo_operacao']}): "
            f"R$ {r['ir_devido']:,.2f}\n"
            f"Prazo DARF: ate o ultimo dia util de {r['prazo_darf']}\n"
            f"Codigo DARF: 6015"
        )

    sinal    = "LUCRO" if r["lucro_liquido"] >= 0 else "PREJUIZO"
    mensagem = (
        f"RESUMO DE VENDA — {ticker}\n"
        f"{'─' * 30}\n"
        f"Tipo: {r['tipo_operacao'].upper()}\n"
        f"Quantidade: {r['quantidade']} acoes\n\n"
        f"Compra: R$ {r['preco_entrada']:.2f}/acao "
        f"(total R$ {r['valor_compra']:,.2f})\n"
        f"Venda:  R$ {r['preco_saida']:.2f}/acao "
        f"(total R$ {r['valor_venda']:,.2f})\n"
        f"Corretagem: R$ {r['corretagem']:.2f}\n\n"
        f"{sinal}\n"
        f"Lucro bruto:   R$ {r['lucro_bruto']:,.2f}\n"
        f"Lucro liquido: R$ {r['lucro_liquido']:,.2f}\n\n"
        f"{bloco_ir}\n\n"
        f"{r['motivo_isencao']}\n"
        f"{r['observacao_ir']}\n\n"
        f"Calculo aproximado. Consulte contador ou Receita Federal.\n"
        f"Isso NAO e recomendacao financeira profissional. "
        f"Investimentos envolvem riscos."
    )

    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
    r_resp  = requests.post(url, data=payload)

    if r_resp.status_code == 200:
        print(f"  Resumo de venda enviado: {ticker} | "
              f"IR: R$ {resultado_ir['ir_devido']:,.2f}")
    else:
        print(f"  Erro ao enviar resumo de venda: {r_resp.text}")


# ============================================================
# SEÇÃO 6 — REGISTRO DE POSIÇÕES (posicoes.json)
# ============================================================

def _carregar_posicoes() -> list:
    """Carrega posicoes.json. Retorna [] se não existir."""
    try:
        with open(ARQUIVO_POSICOES, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _salvar_posicoes(posicoes: list):
    """Persiste a lista de posições no arquivo JSON."""
    with open(ARQUIVO_POSICOES, "w", encoding="utf-8") as f:
        json.dump(posicoes, f, indent=2, ensure_ascii=False)


def registrar_posicao(ticker: str, preco: float, quantidade: int = 1):
    """
    Salva uma nova posição aberta no arquivo posicoes.json.
    Chamada quando o usuário clica em 'Comprei' no Telegram.
    """
    posicoes = _carregar_posicoes()

    posicoes.append({
        "ticker"       : ticker,
        "preco_entrada": preco,
        "quantidade"   : quantidade,
        "data_entrada" : _agora_brt().strftime("%Y-%m-%d %H:%M"),
        "status"       : "aberta",
        "ir_devido"    : None    # preenchido automaticamente ao vender
    })

    _salvar_posicoes(posicoes)
    print(f"  Posição registrada: {ticker} | {quantidade}x R$ {preco:.2f}")


def fechar_posicao(ticker: str, preco_saida: float,
                   resultado_ir: dict) -> bool:
    """
    Fecha a posição mais antiga em aberto para o ticker.
    Atualiza status para 'fechada', salva ROI e IR no JSON.
    Também registra o fechamento em historico.json.

    Retorna True se encontrou e fechou, False se não encontrou.
    """
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
            break   # fecha somente a posição mais antiga

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
# SEÇÃO 7 — PROCESSADOR DE CALLBACKS (BOTÕES DO TELEGRAM)
# ============================================================

def processar_callback(update: dict):
    """
    Processa os callbacks dos botões inline clicados no Telegram.

    Formatos de callback_data esperados:
    ─────────────────────────────────────────────────────────
    'comprei|TICKER|PRECO'
        -> registra posição aberta em posicoes.json

    'ignorei|TICKER'
        -> apenas loga, sem ação no JSON

    'vendi|TICKER|PRECO_SAIDA|QUANTIDADE|VENDAS_MES'
        -> calcula IR, fecha posição no JSON,
           envia resumo completo no Telegram

    Nota: VENDAS_MES = total em R$ vendido no mês corrente.
          Envie 0.0 se não souber — o bot avisará para conferir.
    ─────────────────────────────────────────────────────────
    """
    query = update.get("callback_query", {})
    dados = query.get("data", "").split("|")

    if not dados or not dados[0]:
        return

    acao   = dados[0]
    ticker = dados[1] if len(dados) > 1 else "?"

    def responder_callback(texto: str):
        """Responde ao Telegram para remover o ícone giratório."""
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
            data={"callback_query_id": query.get("id"), "text": texto}
        )

    # ── COMPREI ─────────────────────────────────────────────
    if acao == "comprei" and len(dados) >= 3:
        preco      = float(dados[2])
        quantidade = int(dados[3]) if len(dados) >= 4 else 1
        registrar_posicao(ticker, preco, quantidade)
        responder_callback(f"Registrado: {ticker} {quantidade}x R$ {preco:.2f}")

    # ── IGNOREI ─────────────────────────────────────────────
    elif acao == "ignorei":
        print(f"  Usuário ignorou alerta: {ticker}")
        responder_callback(f"Ignorado: {ticker}")

    # ── VENDI ────────────────────────────────────────────────
    elif acao == "vendi" and len(dados) >= 4:
        try:
            preco_saida = float(dados[2])
            quantidade  = int(dados[3])
            vendas_mes  = float(dados[4]) if len(dados) >= 5 else 0.0
        except (ValueError, IndexError):
            responder_callback("Dados inválidos na venda.")
            return

        posicoes   = _carregar_posicoes()
        pos_aberta = next(
            (p for p in posicoes
             if p["ticker"] == ticker and p["status"] == "aberta"),
            None
        )

        if not pos_aberta:
            responder_callback(f"Nenhuma posição aberta para {ticker}.")
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
        responder_callback(
            f"Venda de {ticker} registrada! "
            f"IR: R$ {resultado['ir_devido']:,.2f}"
        )

    else:
        print(f"  Callback desconhecido: {dados}")


# ============================================================
# SEÇÃO 8 — LOOP PRINCIPAL DE MONITORAMENTO
# ============================================================

def monitorar_watchlist(intervalo_minutos: int = 15):
    """
    Loop principal do monitor — fluxo por ciclo:
    ─────────────────────────────────────────────────────────
    1. Verifica fim de semana / fora de 10h-17h (sem chamar API).
    2. Faz chamada leve (TICKER_SENTINELA) para checar timestamp.
    3. Se timestamp != hoje BRT:
         -> imprime aviso de mercado fechado
         -> dorme até 10h do próximo dia útil
    4. Se timestamp == hoje BRT:
         -> busca watchlist completa
         -> salva snapshot em historico.json
         -> analisa quedas e dispara alertas no Telegram
    5. Aguarda 15 min e repete.
    ─────────────────────────────────────────────────────────
    """
    print("=" * 52)
    print("  Monitor de Quedas B3  (v4.0)")
    print(f"  Limiar de queda  : {LIMIAR_QUEDA_PCT}%")
    print(f"  Intervalo pregao : {intervalo_minutos} min")
    print(f"  Horario pregao   : {PREGAO_HORA_INICIO}h-{PREGAO_HORA_FIM}h BRT (seg-sex)")
    print(f"  Arquivo posicoes : {ARQUIVO_POSICOES}")
    print(f"  Arquivo historico: {ARQUIVO_HISTORICO}")
    print("=" * 52)

    while True:
        agora_str = _agora_brt().strftime("%d/%m/%Y %H:%M:%S BRT")
        print(f"\n[{agora_str}] Verificando...")

        # ── Etapa 1+2: checa mercado (local + sentinela brapi) ──
        mercado_aberto, _ts = checar_mercado_aberto()

        if not mercado_aberto:
            # Determina mensagem de acordo com o motivo
            agora_brt    = _agora_brt()
            fora_horario = not (PREGAO_HORA_INICIO <= agora_brt.hour < PREGAO_HORA_FIM)
            fim_de_semana = agora_brt.weekday() >= 5

            if fim_de_semana or fora_horario:
                print("  Mercado fechado (fora do horario/fim de semana). "
                      "Dormindo ate proximo pregao as 10h.")
            else:
                # Chegou aqui: dentro do horário, dia útil, mas timestamp antigo
                print("  Mercado fechado (timestamps congelados). "
                      "Dormindo ate proximo pregao as 10h.")

            segundos = calcular_espera_ate_proximo_pregao()
            time.sleep(segundos)
            continue

        # ── Etapa 3: mercado aberto — busca watchlist completa ──
        print("  Mercado aberto. Buscando watchlist completa...")
        tickers  = carregar_watchlist()
        cotacoes = buscar_cotacoes(tickers)

        if not cotacoes:
            print("  Nenhuma cotacao retornada. Verifique o token brapi.")
        else:
            # Salva snapshot no histórico (só quando mercado aberto)
            registrar_cotacao_historico(cotacoes)

            # Tabela de resumo no terminal
            print(f"\n  {'TICKER':<7} {'PRECO':>8}  {'VAR%':>7}  {'VOLUME':>14}")
            print(f"  {'─'*7} {'─'*8}  {'─'*7}  {'─'*14}")

            for ativo in cotacoes:
                variacao = ativo.get("variacao_pct") or 0.0
                ticker   = ativo["symbol"]
                preco    = ativo["preco"]
                volume   = ativo.get("volume") or 0

                flag = " <<< ALERTA" if variacao <= LIMIAR_QUEDA_PCT else ""
                print(f"  {ticker:<7} R${preco:>7.2f}  "
                      f"{variacao:>+6.1f}%  {volume:>14,}{flag}")

                if variacao <= LIMIAR_QUEDA_PCT:
                    motivo = (
                        f"Queda de {variacao:+.1f}% detectada hoje.\n"
                        f"Volume negociado: {volume:,}\n"
                        f"Verifique noticias e fundamentos antes de agir.\n"
                        f"Estrategia buy-and-hold: so compre se for "
                        f"panico irracional, nao problema estrutural."
                    )
                    enviar_alerta_compra(
                        ticker       = ticker,
                        preco_atual  = preco,
                        variacao_pct = variacao,
                        motivo       = motivo
                    )

        # ── Etapa 4: aguarda próximo ciclo dentro do pregão ─────
        prox = _agora_brt() + timedelta(minutes=intervalo_minutos)
        print(f"\n  Proxima verificacao em {intervalo_minutos} min "
              f"({prox.strftime('%H:%M')} BRT)...")
        time.sleep(intervalo_minutos * 60)


# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == "__main__":

    # ── TESTE: cálculo de IR (sem rodar o loop) ─────────────
    # Descomente para testar isoladamente:
    #
    # resultado_teste = calcular_ir(
    #     preco_entrada = 38.50,
    #     preco_saida   = 44.20,
    #     quantidade    = 100,
    #     data_entrada  = "2025-01-10 10:30",
    #     data_saida    = "2025-02-20 14:00",
    #     corretagem    = 0.0,
    #     vendas_mes    = 4420.0
    # )
    # resultado_teste["ticker"] = "PETR4"
    # print(json.dumps(resultado_teste, indent=2, ensure_ascii=False))

    # ── TESTE: detecção de pregão (sem rodar o loop) ─────────
    # Descomente para verificar o timestamp sem loop:
    #
    # aberto, ts = checar_mercado_aberto()
    # print(f"Mercado aberto: {aberto} | Timestamp brapi: {ts}")
    # if not aberto:
    #     seg = calcular_espera_ate_proximo_pregao()
    #     print(f"Segundos para proximo pregao: {seg:.0f}")

    # Inicia o monitor
    monitorar_watchlist(intervalo_minutos=15)
