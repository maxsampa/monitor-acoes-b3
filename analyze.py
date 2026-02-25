"""
analyze.py — Análise de Portfólio Buy-and-Hold (B3)
Compatível com o historico.json gerado pelo monitor.py

Estrutura esperada do historico.json:
  Lista de objetos com: tipo, data, ticker, preco, variacao_pct, volume

O que faz:
  1. Lê historico.json (snapshots de cotação do monitor.py)
  2. Mostra último preço conhecido de cada ticker da watchlist
  3. Insight: variação média nos snapshots com queda >= THRESHOLD_QUEDA %
  4. Detecta alertas de queda >= THRESHOLD_QUEDA % no histórico
  5. Gera gráfico de evolução de preço de PETR4 com os dados locais
  6. Lê posicoes.json (opcional) para calcular ROI das suas operações

Como rodar:
  pip install matplotlib pandas
  python analyze.py

Arquivos necessários na mesma pasta:
  - historico.json   → gerado automaticamente pelo monitor.py
  - posicoes.json    → gerado automaticamente pelo monitor.py (opcional)
"""

import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURAÇÕES — ajuste aqui conforme necessário
# ─────────────────────────────────────────────

HISTORICO_FILE   = "historico.json"     # gerado pelo monitor.py
POSICOES_FILE    = "posicoes.json"      # suas operações (opcional)
OUTPUT_PNG       = "petr4_historico.png"
TICKER_GRAFICO   = "PETR4"
THRESHOLD_QUEDA  = 2.5                  # alerta de queda >= 2.5%

WATCHLIST = [
    "PETR4", "VALE3", "ITUB4", "BBAS3", "WEGE3",
    "TAEE11", "CPLE3", "AXIA3", "PRIO3", "EQTL3",
    "RAIL3", "B3SA3"
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def separador(titulo="", char="=", largura=62):
    if titulo:
        print(f"\n{char*3} {titulo} {char*(largura - len(titulo) - 5)}")
    else:
        print(char * largura)


def carregar_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"⚠️  Arquivo '{path}' corrompido ou inválido: {e}")
        print(f"   Verifique o conteúdo manualmente.")
        return None


# ─────────────────────────────────────────────
# 1. CARREGA HISTORICO.JSON
# ─────────────────────────────────────────────

def carregar_historico():
    dados = carregar_json(HISTORICO_FILE)
    if dados is None:
        print(f"❌ Arquivo '{HISTORICO_FILE}' não encontrado.")
        print("   Verifique se o monitor.py já gerou o arquivo.")
        return None

    # Filtra apenas registros de cotação (ignora alertas, trades, etc.)
    cotacoes = [d for d in dados if d.get("tipo") == "cotacao"]
    if not cotacoes:
        # Fallback: aceita qualquer registro que tenha preco e ticker
        cotacoes = [d for d in dados if "preco" in d and "ticker" in d]

    df = pd.DataFrame(cotacoes)
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m-%d %H:%M")

    # Remove duplicatas REAIS: mesmo ticker + mesmo preço + mesma variação
    # (o monitor salva o mesmo snapshot várias vezes durante o after-market)
    df = df.drop_duplicates(subset=["ticker", "preco", "variacao_pct"])
    df = df.sort_values(["ticker", "data"]).reset_index(drop=True)

    print(f"✅ {len(df)} registros carregados | "
          f"{df['ticker'].nunique()} tickers | "
          f"período: {df['data'].min().strftime('%d/%m/%Y %H:%M')} "
          f"→ {df['data'].max().strftime('%d/%m/%Y %H:%M')}")

    return df


# ─────────────────────────────────────────────
# 2. ÚLTIMO PREÇO DE CADA TICKER
# ─────────────────────────────────────────────

def resumo_precos(df):
    separador("📊 PREÇOS — ÚLTIMO SNAPSHOT REGISTRADO")

    ultimos = (
        df.sort_values("data")
          .groupby("ticker")
          .last()
          .reset_index()
    )

    print(f"\n  {'Ticker':<8} {'Preço':>10} {'Var. Dia':>10} {'Volume':>15}  {'Atualizado'}")
    print("  " + "-" * 60)

    for _, row in ultimos[ultimos["ticker"].isin(WATCHLIST)].iterrows():
        sinal = "🟢" if row["variacao_pct"] >= 0 else "🔴"
        print(
            f"  {sinal} {row['ticker']:<6} "
            f"R${row['preco']:>8.2f} "
            f"{row['variacao_pct']:>+9.2f}% "
            f"{row['volume']:>14,.0f}  "
            f"{row['data'].strftime('%d/%m %H:%M')}"
        )
    print()


# ─────────────────────────────────────────────
# 3. INSIGHT — QUEDAS >= THRESHOLD
# ─────────────────────────────────────────────

def insight_quedas(df, threshold=THRESHOLD_QUEDA):
    separador(f"📉 INSIGHT — QUEDAS ≥ {threshold}% REGISTRADAS")

    quedas_raw = df[df["variacao_pct"] <= -threshold].copy()

    # Consolida: 1 registro por ticker por pregão (pior queda do dia)
    # Evita contar o mesmo evento várias vezes porque o preço não mudou
    if not quedas_raw.empty:
        quedas_raw["dia"] = quedas_raw["data"].dt.date
        quedas = (
            quedas_raw.sort_values("variacao_pct")          # menor variação primeiro
                      .groupby(["ticker", "dia"])
                      .first()                               # pega a pior queda do dia
                      .reset_index()
        )
    else:
        quedas = quedas_raw

    if quedas.empty:
        print(f"\n  Nenhum evento de queda ≥ {threshold}% no histórico atual.")
        print(f"  Continue monitorando — o histórico ainda é curto.")
        media_var = 0.0
    else:
        media_var = quedas["variacao_pct"].mean()
        idx_max_queda = quedas["variacao_pct"].idxmin()

        print(f"\n  Eventos únicos (ticker+pregão) com queda ≥ {threshold}%: {len(quedas)}")
        print(f"  Variação média nesses eventos    : {media_var:+.2f}%")
        print(f"  Maior queda registrada           : "
              f"{quedas.loc[idx_max_queda, 'variacao_pct']:.2f}% "
              f"({quedas.loc[idx_max_queda, 'ticker']} "
              f"em {quedas.loc[idx_max_queda, 'data'].strftime('%d/%m/%Y')})")

        print(f"\n  {'Ticker':<8} {'Variação':>10} {'Preço':>10}  {'Pregão'}")
        print("  " + "-" * 48)

        for _, row in quedas.iterrows():
            print(
                f"  🔴 {row['ticker']:<6} "
                f"{row['variacao_pct']:>+9.2f}% "
                f"R${row['preco']:>8.2f}  "
                f"{row['data'].strftime('%d/%m/%Y')}"
            )

    print(f"\n  💡 Insight: Média de variação em quedas >{threshold}%: {media_var:+.2f}%")
    print(f"  📌 Buy-and-hold: use esses momentos como radar de aporte.")
    print()


# ─────────────────────────────────────────────
# 4. GRÁFICO DE PREÇOS — PETR4
# ─────────────────────────────────────────────

def gerar_grafico(df, ticker=TICKER_GRAFICO, output_file=OUTPUT_PNG):
    df_ticker = df[df["ticker"] == ticker].copy()

    if df_ticker.empty:
        print(f"⚠️  Nenhum dado para {ticker} no histórico. Gráfico não gerado.")
        return

    # Ordena por data e remove duplicatas de preço CONSECUTIVAS
    # (mantém o primeiro e último de cada grupo de preço igual = mostra mudanças reais)
    df_ticker = df_ticker.sort_values("data").reset_index(drop=True)

    # Usa todos os pontos únicos — sem agrupamento por dia
    # (quando histórico > 30 dias, agrupa por dia automaticamente)
    dias_unicos = df_ticker["data"].dt.date.nunique()
    if dias_unicos > 30:
        # Histórico longo: 1 ponto por dia (fechamento)
        df_ticker["data_dia"] = df_ticker["data"].dt.date
        df_plot = (
            df_ticker.groupby("data_dia")
                     .last()
                     .reset_index()
        )
        rotulo_x = "%d/%m"
        titulo_periodo = "diário"
    else:
        # Histórico curto: todos os snapshots (visão intraday/intra-semana)
        df_plot = df_ticker.copy()
        rotulo_x = "%d/%m %Hh"
        titulo_periodo = "por snapshot"

    n_pontos = len(df_plot)
    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(df_plot["data"], df_plot["preco"],
            color="#1a73e8", linewidth=2.0,
            marker="o", markersize=5 if n_pontos > 10 else 7,
            label=f"{ticker} — Preço")

    ax.fill_between(df_plot["data"], df_plot["preco"],
                    df_plot["preco"].min() * 0.998,   # fill apenas até o mínimo (não zero)
                    alpha=0.12, color="#1a73e8")

    # Escala Y focada na faixa real de preços (±3% de margem)
    p_min = df_plot["preco"].min()
    p_max = df_plot["preco"].max()
    margem = max((p_max - p_min) * 0.3, p_min * 0.02)   # mínimo 2% de margem
    ax.set_ylim(p_min - margem, p_max + margem)

    # Anotação do último preço
    ultimo_preco = df_plot["preco"].iloc[-1]
    ultima_data  = df_plot["data"].iloc[-1]
    ax.annotate(
        f"R$ {ultimo_preco:.2f}",
        xy=(ultima_data, ultimo_preco),
        xytext=(-60, 16),
        textcoords="offset points",
        fontsize=10, fontweight="bold", color="#1a73e8",
        arrowprops=dict(arrowstyle="->", color="#1a73e8", lw=1.2)
    )

    # Média móvel só se houver pontos suficientes
    if n_pontos >= 5:
        janela = min(5, n_pontos)
        df_plot = df_plot.copy()
        df_plot["mm"] = df_plot["preco"].rolling(janela).mean()
        ax.plot(df_plot["data"], df_plot["mm"],
                color="#f57c00", linewidth=1.3,
                linestyle="--", label=f"Média Móvel {janela}pts")

    ax.xaxis.set_major_formatter(mdates.DateFormatter(rotulo_x))
    plt.xticks(rotation=30, fontsize=8)

    ax.set_title(
        f"{ticker} — Evolução de Preço ({titulo_periodo}) | monitor.py",
        fontsize=14, fontweight="bold", pad=12
    )
    ax.set_xlabel("Data / Hora", fontsize=11)
    ax.set_ylabel("Preço (R$)", fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.text(0.01, 0.01,
             f"Fonte: monitor.py → {HISTORICO_FILE}  |  "
             "Isso NÃO é recomendação financeira profissional.",
             fontsize=7, color="gray")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"✅ Gráfico salvo: {output_file}  ({n_pontos} pontos | modo: {titulo_periodo})\n")


# ─────────────────────────────────────────────
# 5. ROI DAS POSIÇÕES (posicoes.json — opcional)
# ─────────────────────────────────────────────

def analisar_posicoes():
    """
    Lê posicoes.json gerado pelo monitor.py.

    Campos usados do monitor.py:
      preco_entrada  → preço médio de compra por ação
      preco_saida    → preço de venda (só existe se status == "fechada")
      data_entrada   → data/hora da compra
      data_saida     → data/hora da venda (só se fechada)
      quantidade     → número de ações
      status         → "aberta" | "fechada"
      roi_pct        → calculado pelo monitor ao fechar (opcional)
      lucro_liquido  → lucro após corretagem (opcional)
      ir_devido      → IR calculado pelo monitor (opcional)
    """
    separador("💼 POSIÇÕES — ROI DAS OPERAÇÕES")

    posicoes = carregar_json(POSICOES_FILE)

    if posicoes is None:
        print(f"\n  ℹ️  Arquivo '{POSICOES_FILE}' não encontrado.")
        print("  O arquivo é gerado automaticamente pelo monitor.py")
        print("  quando você clica em ✅ Comprei no alerta do Telegram.")
        print("  Exemplo de estrutura gerada pelo monitor.py:\n")
        exemplo = [
            {
                "ticker": "PETR4",
                "status": "aberta",
                "preco_entrada": 36.50,
                "quantidade": 100,
                "data_entrada": "2026-01-10 10:35",
                "ir_devido": None
            },
            {
                "ticker": "VALE3",
                "status": "fechada",
                "preco_entrada": 80.00,
                "quantidade": 50,
                "data_entrada": "2025-10-01 11:00",
                "preco_saida": 86.00,
                "data_saida": "2026-02-01 14:30",
                "lucro_liquido": 300.00,
                "roi_pct": 7.50,
                "ir_devido": 45.00
            }
        ]
        print(json.dumps(exemplo, indent=2, ensure_ascii=False))
        print()
        return

    fechadas = [p for p in posicoes if p.get("status") == "fechada"]
    abertas  = [p for p in posicoes if p.get("status") == "aberta"]

    # ── Posições fechadas (com preço de saída) ──────────────────────────
    if fechadas:
        print(f"\n  {'Ticker':<8} {'Entrada':>10} {'Saída':>10} {'ROI':>9} {'Resultado':>14}  {'IR Devido':>10}")
        print("  " + "-" * 70)

        rois, lucro_total, ir_total = [], 0.0, 0.0

        for p in fechadas:
            # Campos do monitor.py: preco_entrada / preco_saida
            # Fallback para nomes antigos caso o usuário edite manualmente
            p_entrada = p.get("preco_entrada") or p.get("preco_compra", 0)
            p_saida   = p.get("preco_saida")   or p.get("preco_venda",  0)
            qtd       = p.get("quantidade", 1)

            if not p_entrada or not p_saida:
                print(f"  ⚠️  {p.get('ticker','?')}: campos de preço ausentes. Pulando.")
                continue

            # roi_pct e lucro_liquido podem vir direto do monitor
            roi   = p.get("roi_pct")       or ((p_saida - p_entrada) / p_entrada * 100)
            lucro = p.get("lucro_liquido") or ((p_saida - p_entrada) * qtd)
            ir    = p.get("ir_devido")     or 0.0

            rois.append(roi)
            lucro_total += lucro
            ir_total    += ir

            # data_saida é o campo do monitor; fallback: data_venda (manual)
            data_saida = p.get("data_saida", p.get("data_venda", "?"))
            sinal = "✅" if roi >= 0 else "🔴"
            print(
                f"  {sinal} {p['ticker']:<6} "
                f"R${p_entrada:>8.2f} "
                f"R${p_saida:>8.2f} "
                f"{roi:>+8.2f}% "
                f"R${lucro:>12.2f}  "
                f"R${ir:>8.2f}"
            )

        if rois:
            roi_medio = sum(rois) / len(rois)
            print("  " + "-" * 70)
            print(f"  {'ROI MÉDIO:':>53} {roi_medio:>+8.2f}%")
            print(f"  {'RESULTADO LÍQUIDO TOTAL:':>53} R${lucro_total:>11.2f}")
            print(f"  {'IR TOTAL DEVIDO:':>53} R${ir_total:>11.2f}")

    # ── Posições abertas (em carteira) ──────────────────────────────────
    if abertas:
        print(f"\n  📂 Em carteira (posições abertas):")
        print(f"     {'Ticker':<8} {'Preço Entrada':>14} {'Qtd':>6}  {'Total Investido':>16}  {'Data Entrada'}")
        print("     " + "-" * 62)

        total_investido = 0.0
        for p in abertas:
            # Campos do monitor.py: preco_entrada / data_entrada
            p_entrada = p.get("preco_entrada") or p.get("preco_compra", 0)
            qtd       = p.get("quantidade", 0)
            total     = p_entrada * qtd
            data_ent  = p.get("data_entrada", p.get("data_compra", "?"))
            total_investido += total
            print(
                f"     {p['ticker']:<8} "
                f"R${p_entrada:>12.2f} "
                f"{qtd:>6}  "
                f"R${total:>14.2f}  "
                f"{data_ent}"
            )

        print("     " + "-" * 62)
        print(f"     {'TOTAL EM CARTEIRA:':>31} R${total_investido:>14.2f}")

    if not fechadas and not abertas:
        print("\n  Nenhuma posição encontrada em posicoes.json.")

    print()

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  📈 ANALYZE.PY — Monitor Buy-and-Hold B3 (v3)           ║")
    print("║  Compatível com historico.json do monitor.py            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    df = carregar_historico()
    if df is None:
        return

    resumo_precos(df)
    insight_quedas(df, threshold=THRESHOLD_QUEDA)

    separador(f"📈 GRÁFICO — {TICKER_GRAFICO}")
    print()
    gerar_grafico(df, TICKER_GRAFICO)

    analisar_posicoes()

    separador("📋 RESUMO EXECUTIVO")
    quedas_raw = df[df["variacao_pct"] <= -THRESHOLD_QUEDA]
    if not quedas_raw.empty:
        quedas_raw = quedas_raw.copy()
        quedas_raw["dia"] = quedas_raw["data"].dt.date
        quedas_detectadas = quedas_raw.groupby(["ticker", "dia"]).ngroups
    else:
        quedas_detectadas = 0
    print(f"\n  Tickers monitorados      : {df['ticker'].nunique()}")
    print(f"  Total de snapshots       : {len(df)}")
    print(f"  Alertas de queda ≥{THRESHOLD_QUEDA}%   : {quedas_detectadas}")
    print(f"  Threshold configurado    : {THRESHOLD_QUEDA}%")
    print(f"  Gráfico gerado           : {OUTPUT_PNG}")
    print()
    separador()
    print()
    

if __name__ == "__main__":
    main()
