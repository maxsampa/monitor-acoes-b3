Grok
1. **Filtro automático de qualidade da queda**  
   Só disparar alerta se volume > média histórica do ticker (ex: 1.5x) OU se FCF positivo nos últimos 4T (via brapi modules). Evita alertas em quedas de baixa liquidez.

2. **Alerta de upside realizado (take-profit parcial)**  
   Quando posição aberta subir +15–25%, enviar alerta “Venda parcial sugerida” com cálculo de lucro e IR.

3. **Watchlist dinâmica via X**  
   Comando no Telegram: “adicionar TICKER” → bot checa fundamentos básicos na brapi e adiciona se passar (FCF >0, dívida baixa).

4. **Relatório semanal automático**  
   Toda segunda 9h, enviar no Telegram: posições abertas (ROI atual), quedas da semana, insight “melhor momento de entrada histórico”.

5. **Backtest simples de alertas**  
   No comando “datascience backtest” → simular “se tivesse comprado todas quedas ≥3% nos últimos X meses, qual ROI total?”.

6. **Integração leve com IBOV**  
   Comparar variação do ticker vs IBOV no alerta (ex: “PETR4 -4%, mas IBOV -0.5% → mais irracional”).

7. **Alerta de dividendos próximos**  
   Via brapi dividends → se ticker na posição aberta tiver provento em 30 dias, avisar.
