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
  - posicoes.json    → você preenche manualmente ao comprar/vender (opcional)
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
THRESHOLD_QUEDA  = 3.0                  # alerta de queda >= 3%

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
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# 1. CARREGA HISTORICO.JSON
# ─────────────────────────────────────────────

def carregar_historico():
    dados = carregar_json(HISTORICO_FILE)
    if dados is None:
        print(f"❌ Arquivo '{HISTORICO_FILE}' não encontrado.")
        print("   Verifique se o monitor.py já gerou o arquivo.")
        return None

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], format="%Y-%m-%d %H:%M")
    df = df.drop_duplicates(subset=["data", "ticker"])
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

    quedas = df[df["variacao_pct"] <= -threshold].copy()

    if quedas.empty:
        print(f"\n  Nenhum registro com queda ≥ {threshold}% no histórico atual.")
        print(f"  Continue monitorando — o histórico ainda é curto.")
        media_var = 0.0
    else:
        media_var = quedas["variacao_pct"].mean()
        idx_max_queda = quedas["variacao_pct"].idxmin()

        print(f"\n  Ocorrências com queda ≥ {threshold}%: {len(quedas)}")
        print(f"  Variação média nesses registros  : {media_var:+.2f}%")
        print(f"  Maior queda registrada           : "
              f"{quedas.loc[idx_max_queda, 'variacao_pct']:.2f}% "
              f"({quedas.loc[idx_max_queda, 'ticker']} "
              f"em {quedas.loc[idx_max_queda, 'data'].strftime('%d/%m/%Y %H:%M')})")

        print(f"\n  {'Ticker':<8} {'Variação':>10} {'Preço':>10}  {'Data/Hora'}")
        print("  " + "-" * 48)

        for _, row in quedas.iterrows():
            print(
                f"  🔴 {row['ticker']:<6} "
                f"{row['variacao_pct']:>+9.2f}% "
                f"R${row['preco']:>8.2f}  "
                f"{row['data'].strftime('%d/%m/%Y %H:%M')}"
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

    # Último registro por dia (evita múltiplos pontos no mesmo dia)
    df_ticker["data_dia"] = df_ticker["data"].dt.date
    df_dia = (
        df_ticker.sort_values("data")
                 .groupby("data_dia")
                 .last()
                 .reset_index()
    )

    fig, ax = plt.subplots(figsize=(13, 5))

    ax.plot(df_dia["data"], df_dia["preco"],
            color="#1a73e8", linewidth=2.0,
            marker="o", markersize=6,
            label=f"{ticker} — Fechamento")

    ax.fill_between(df_dia["data"], df_dia["preco"],
                    alpha=0.10, color="#1a73e8")

    # Anotação do último preço
    ultimo_preco = df_dia["preco"].iloc[-1]
    ultima_data  = df_dia["data"].iloc[-1]
    ax.annotate(
        f"R$ {ultimo_preco:.2f}",
        xy=(ultima_data, ultimo_preco),
        xytext=(-55, 14),
        textcoords="offset points",
        fontsize=10, fontweight="bold", color="#1a73e8",
        arrowprops=dict(arrowstyle="->", color="#1a73e8", lw=1.2)
    )

    # Média móvel (adaptada ao volume de dados disponível)
    if len(df_dia) >= 5:
        janela = min(5, len(df_dia))
        df_dia["mm"] = df_dia["preco"].rolling(janela).mean()
        ax.plot(df_dia["data"], df_dia["mm"],
                color="#f57c00", linewidth=1.3,
                linestyle="--", label=f"Média Móvel {janela}d")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %Hh"))
    plt.xticks(rotation=30, fontsize=8)

    ax.set_title(f"{ticker} — Evolução de Preço (dados: monitor.py)",
                 fontsize=14, fontweight="bold", pad=12)
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

    print(f"✅ Gráfico salvo: {output_file}  ({len(df_dia)} pontos)\n")


# ─────────────────────────────────────────────
# 5. ROI DAS POSIÇÕES (posicoes.json — opcional)
# ─────────────────────────────────────────────

def analisar_posicoes():
    separador("💼 POSIÇÕES — ROI DAS OPERAÇÕES")

    posicoes = carregar_json(POSICOES_FILE)

    if posicoes is None:
        print(f"\n  ℹ️  Arquivo '{POSICOES_FILE}' não encontrado.")
        print("  Para rastrear suas operações, crie o arquivo assim:\n")
        exemplo = [
            {
                "ticker": "PETR4",
                "status": "aberta",
                "data_compra": "2026-01-10",
                "preco_compra": 36.50,
                "quantidade": 100
            },
            {
                "ticker": "VALE3",
                "status": "fechada",
                "data_compra": "2025-10-01",
                "preco_compra": 80.00,
                "quantidade": 50,
                "data_venda": "2026-02-01",
                "preco_venda": 86.00
            }
        ]
        print(json.dumps(exemplo, indent=2, ensure_ascii=False))
        print()
        return

    fechadas = [p for p in posicoes if p.get("status") == "fechada"]
    abertas  = [p for p in posicoes if p.get("status") == "aberta"]

    if fechadas:
        print(f"\n  {'Ticker':<8} {'Compra':>10} {'Venda':>10} {'ROI':>9} {'Resultado':>14}")
        print("  " + "-" * 58)

        rois, lucro_total = [], 0.0

        for p in fechadas:
            roi   = ((p["preco_venda"] - p["preco_compra"]) / p["preco_compra"]) * 100
            lucro = (p["preco_venda"] - p["preco_compra"]) * p["quantidade"]
            rois.append(roi)
            lucro_total += lucro
            sinal = "✅" if roi >= 0 else "🔴"
            print(
                f"  {sinal} {p['ticker']:<6} "
                f"R${p['preco_compra']:>8.2f} "
                f"R${p['preco_venda']:>8.2f} "
                f"{roi:>+8.2f}% "
                f"R${lucro:>12.2f}"
            )

        roi_medio = sum(rois) / len(rois)
        print("  " + "-" * 58)
        print(f"  {'ROI MÉDIO:':>46} {roi_medio:>+8.2f}%")
        print(f"  {'RESULTADO TOTAL:':>46} R${lucro_total:>11.2f}")

    if abertas:
        print(f"\n  📂 Em carteira (abertas):")
        for p in abertas:
            print(f"     {p['ticker']:<8} R${p['preco_compra']:.2f} "
                  f"em {p.get('data_compra','?')} | Qtd: {p['quantidade']}")

    print()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  📈 ANALYZE.PY — Monitor Buy-and-Hold B3 (v2)           ║")
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
    quedas_detectadas = len(df[df["variacao_pct"] <= -THRESHOLD_QUEDA])
    print(f"\n  Tickers monitorados      : {df['ticker'].nunique()}")
    print(f"  Total de snapshots       : {len(df)}")
    print(f"  Alertas de queda ≥{THRESHOLD_QUEDA}%   : {quedas_detectadas}")
    print(f"  Threshold configurado    : {THRESHOLD_QUEDA}%")
    print(f"  Gráfico gerado           : {OUTPUT_PNG}")
    print()
    separador()
    print()
    print("  ⚠️  DISCLAIMER: Isso NÃO é recomendação financeira profissional.")
    print("  Faça sua própria análise e consulte um assessor certificado.")
    print("  Investimentos envolvem riscos.")
    print()


if __name__ == "__main__":
    main()
