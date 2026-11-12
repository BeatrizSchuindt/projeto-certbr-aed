"""
analise_estatistica.py
──────────────────────
Testes estatísticos do artigo "Análise exploratória de dados de segurança na
Internet brasileira: incidentes notificados ao CERT.br" (ERI-MT 2026).

Série analisada: total mensal de notificações, jan/2016 a abr/2026 (124 meses),
lida de dados_certbr/tipos_incidente_mensal.csv (gerado por extrair_api_certbr.py).

  1. Tendência     — Mann-Kendall nos totais anuais (2016–2025) e
                     Mann-Kendall sazonal na série mensal, com inclinação de Sen
  2. Sazonalidade  — Kruskal-Wallis na série bruta, decomposição STL robusta,
                     força da sazonalidade (F_S) e Kruskal-Wallis sem tendência
  3. Meses atípicos — limite do IQR e identificador de Hampel

Os meses atípicos (jul/2017 e jun/2019) são MANTIDOS em todos os testes.

Uso:
    python analise_estatistica.py

Dependências:
    pip install pandas numpy scipy statsmodels pymannkendall
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import kruskal
from statsmodels.tsa.seasonal import STL

ALFA = 0.05
ARQUIVO = Path("dados_certbr") / "tipos_incidente_mensal.csv"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
TENDENCIA = {"increasing": "crescente", "decreasing": "decrescente",
             "no trend": "sem tendência significativa"}


def fmt(x: float, casas: int = 0) -> str:
    """Formata número no padrão brasileiro (1.234,5)."""
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def kruskal_por_mes(serie: pd.Series):
    """Kruskal-Wallis comparando os 12 meses do ano entre si."""
    grupos = [serie[serie.index.month == m].values for m in range(1, 13)]
    return kruskal(*grupos), [len(g) for g in grupos]


# ─── Dados ───────────────────────────────────────────────────────────────────
df = pd.read_csv(ARQUIVO, parse_dates=["data"])
total = (df[df["categoria"] == "total_geral"]
         .set_index("data")["total"].sort_index().astype(float))
total.index.freq = "MS"

print(f"Série: {len(total)} meses, de {total.index[0]:%m/%Y} a {total.index[-1]:%m/%Y}")
print(f"Média {fmt(total.mean())} | mediana {fmt(total.median())} | "
      f"desvio-padrão {fmt(total.std())}")


# ─── 1. Tendência: Mann-Kendall ──────────────────────────────────────────────
print("\n=== 1. TENDÊNCIA (Mann-Kendall) ===")

# 1a. Totais anuais — só anos completos (2016 a 2025, n = 10)
anos_completos = total[total.index.year <= 2025]
anual = anos_completos.groupby(anos_completos.index.year).sum()
r = mk.original_test(anual.values, alpha=ALFA)
print(f"Anual (2016–2025, n = {len(anual)}): tau = {fmt(r.Tau, 3)}; "
      f"p = {fmt(r.p, 3)} -> {TENDENCIA[r.trend]}")
print(f"  Total 2016 = {fmt(anual[2016])}; total 2025 = {fmt(anual[2025])}; "
      f"variação = {fmt(100 * (anual[2025] / anual[2016] - 1), 1)}%")

# 1b. Sazonal — compara só observações do mesmo mês (Hirsch et al. 1982);
#     usa os 124 meses (jan–abr com 11 anos, mai–dez com 10)
r = mk.seasonal_test(total.values, period=12, alpha=ALFA)
print(f"Sazonal (124 meses): tau = {fmt(r.Tau, 3)}; p = {fmt(r.p, 4)} -> {TENDENCIA[r.trend]}")
print(f"  Inclinação de Sen: {fmt(r.slope)} notificações/ano (no mesmo mês)")


# ─── 2. Sazonalidade: Kruskal-Wallis e STL ───────────────────────────────────
print("\n=== 2. SAZONALIDADE ===")

# 2a. Kruskal-Wallis na série bruta
(H, p), n_por_mes = kruskal_por_mes(total)
print(f"Kruskal-Wallis, série bruta: H = {fmt(H, 2)}; p = {fmt(p, 3)}")
print(f"  Observações por mês: {dict(zip(MESES, n_por_mes))}")

# 2b. STL robusta no logaritmo do total (período de 12 meses)
log_total = np.log(total)
stl = STL(log_total, period=12, robust=True).fit()
S, R, T = stl.seasonal, stl.resid, stl.trend

# Força da sazonalidade (Wang et al. 2006): 0 = ausente, 1 = forte
F_S = max(0.0, 1 - R.var() / (S + R).var())
print(f"Força da sazonalidade (STL): F_S = {fmt(F_S, 3)}")

fator = np.exp(S.groupby(S.index.month).mean())
mes_max = fator.idxmax()
print(f"  Maior fator sazonal: {MESES[mes_max - 1]} "
      f"({fmt(100 * (fator[mes_max] - 1), 0)}% acima da tendência)")

# 2c. Kruskal-Wallis na série sem tendência (log do total menos a tendência STL)
(H, p), _ = kruskal_por_mes(log_total - T)
print(f"Kruskal-Wallis, série sem tendência: H = {fmt(H, 2)}; p = {fmt(p, 3)}")

# 2d. Médias e medianas por mês, com e sem os dois meses atípicos
atipicos = pd.to_datetime(["2017-07-01", "2019-06-01"])
sem_atip = total.drop(atipicos)
tabela = pd.DataFrame({
    "média": total.groupby(total.index.month).mean(),
    "média s/ atípicos": sem_atip.groupby(sem_atip.index.month).mean(),
    "mediana": total.groupby(total.index.month).median(),
}).round(0).astype(int)
tabela.index = MESES
print("\nMédias e medianas por mês:")
print(tabela.to_string())
print(f"Média geral: {fmt(total.mean())} | sem atípicos: {fmt(sem_atip.mean())} "
      f"| mediana geral: {fmt(total.median())}")


# ─── 3. Meses atípicos: IQR e Hampel ─────────────────────────────────────────
print("\n=== 3. MESES ATÍPICOS ===")

# 3a. IQR: um único limite para o período inteiro (Tukey 1977)
q1, q3 = total.quantile([0.25, 0.75])
limite = q3 + 1.5 * (q3 - q1)
acima = total[total > limite].sort_values(ascending=False)
print(f"IQR: limite superior = {fmt(limite)}; {len(acima)} meses acima:")
for data, valor in acima.items():
    print(f"  {data:%m/%Y}: {fmt(valor)}")

# 3b. Hampel: desvio do log em relação à mediana móvel centrada de 13 meses,
#     padronizado pelo escore-z modificado (Iglewicz e Hoaglin 1993)
desvio = log_total - log_total.rolling(13, center=True, min_periods=1).median()
mad = np.median(np.abs(desvio - desvio.median()))
z = 0.6745 * (desvio - desvio.median()) / mad
print(f"Hampel (|z| > 3,5): {(z.abs() > 3.5).sum()} meses atípicos")
for data in z.abs().sort_values(ascending=False).index[:6]:
    marca = "  <- atípico" if abs(z[data]) > 3.5 else ""
    print(f"  {data:%m/%Y}: z = {fmt(z[data], 2)}{marca}")
for data in acima.index:
    if abs(z[data]) <= 3.5:
        print(f"  (IQR, mas não Hampel) {data:%m/%Y}: z = {fmt(z[data], 2)}")
