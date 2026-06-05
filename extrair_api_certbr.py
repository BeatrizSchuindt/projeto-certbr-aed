"""
extrair_api_certbr.py
─────────────────────
Pipeline completo de extração dos dados da API interna do CERT.br.

A API expõe arquivos texto (.txt) em https://stats.cert.br/data/incidentes/
organizados em dois grupos:

  GRUPO A — Séries históricas globais (sem ano na URL)
    • incidentes.txt          → total anual 1999-presente
    • dos.txt                 → notificações DoS anuais 1999-presente

  GRUPO B — Detalhamento por ano (com ano na URL)
    • {ano}/tipos-incidente.txt          → agregado por categoria no ano
    • {ano}/tipos-incidente-mensal.txt   → categoria x mês
    • {ano}/incidentes-mensal.txt        → total por mês
    • {ano}/tipos-fraude-mensal.txt      → phishing vs malware por mês
    • {ano}/top-portas.txt               → portas mais varridas
    • {ano}/top-cc.txt                   → países de origem
    • {ano}/top-asn.txt                  → sistemas autônomos de origem

O detalhamento por ano está disponível de 2016 a 2026.

Uso:
    python extrair_api_certbr.py                # tudo (padrão)
    python extrair_api_certbr.py 2020 2024      # intervalo customizado

Dependências:
    pip install requests pandas
"""

from __future__ import annotations
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests


# ─── Configuração ────────────────────────────────────────────────────────────
BASE_URL  = "https://stats.cert.br/data/incidentes"
ANO_INI   = 2016
ANO_FIM   = 2026
OUT_DIR   = Path("dados_certbr")
PAUSA_SEG = 0.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Pesquisa Acadêmica - IFMT Cuiabá) "
        "AppleWebKit/537.36"
    ),
    "Accept": "text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://stats.cert.br/incidentes/",
}

# Arquivos do grupo A (séries globais sem ano)
ARQS_GLOBAIS = {
    "incidentes": "incidentes.txt",
    "dos":        "dos.txt",
}

# Arquivos do grupo B (por ano)
ARQS_ANUAIS = {
    "tipos_incidente":        "tipos-incidente.txt",
    "tipos_incidente_mensal": "tipos-incidente-mensal.txt",
    "incidentes_mensal":      "incidentes-mensal.txt",
    "tipos_fraude_mensal":    "tipos-fraude-mensal.txt",
    "top_portas":             "top-portas.txt",
    "top_cc":                 "top-cc.txt",
    "top_asn":                "top-asn.txt",
}


# ─── Download ────────────────────────────────────────────────────────────────
def baixar(url: str) -> str | None:
    """Faz GET na URL e retorna o texto. None em caso de erro/404."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as e:
        print(f"      erro: {e}")
        return None


# ─── Parsers (um por tipo de arquivo) ────────────────────────────────────────
def _split_linhas(texto: str) -> list[list[str]]:
    """Quebra o texto em linhas e tokeniza cada uma, ignorando comentários (#)."""
    out = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        out.append(linha.split())
    return out


def parse_serie_global(texto: str) -> pd.DataFrame:
    """
    Parser para incidentes.txt e dos.txt.
    Formato: ano | mês_referência | valor
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if len(tokens) < 3:
            continue
        try:
            registros.append({
                "ano":            int(tokens[0]),
                "mes_referencia": tokens[1],
                "valor":          int(tokens[-1]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


def parse_tipos_incidente(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para tipos-incidente.txt (anual).
    Formato: num | % | tipo
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if len(tokens) < 3:
            continue
        try:
            registros.append({
                "ano":        ano,
                "categoria":  " ".join(tokens[2:]),
                "total":      int(tokens[0]),
                "percentual": float(tokens[1]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


def parse_tipos_incidente_mensal(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para tipos-incidente-mensal.txt.
    Formato: Mês | Total | DoS | % | Fraude | % | Invasão | % | Outros | % | Scan | % | Web | %
    """
    linhas = _split_linhas(texto)
    if not linhas:
        return pd.DataFrame()

    categorias = ["DoS", "Fraude", "Invasao", "Outros", "Scan", "Web"]
    registros = []
    for tokens in linhas:
        if tokens[0].lower() == "total":
            continue
        try:
            mes = int(tokens[0])
        except ValueError:
            continue
        if not (1 <= mes <= 12):
            continue
        try:
            total_mes = int(tokens[1])
        except (ValueError, IndexError):
            continue

        # Linha total geral do mês
        registros.append({
            "ano":        ano,
            "mes":        mes,
            "data":       pd.Timestamp(year=ano, month=mes, day=1).date(),
            "categoria":  "total_geral",
            "total":      total_mes,
            "percentual": None,
        })
        # Cada categoria ocupa 2 colunas a partir do índice 2: valor, %
        for i, cat in enumerate(categorias):
            idx_val = 2 + i * 2
            idx_pct = 3 + i * 2
            if idx_pct >= len(tokens):
                break
            try:
                valor = int(tokens[idx_val])
                pct   = float(tokens[idx_pct])
            except (ValueError, IndexError):
                continue
            registros.append({
                "ano":        ano,
                "mes":        mes,
                "data":       pd.Timestamp(year=ano, month=mes, day=1).date(),
                "categoria":  cat,
                "total":      valor,
                "percentual": pct,
            })
    return pd.DataFrame(registros)


def parse_incidentes_mensal(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para incidentes-mensal.txt.
    Formato: Mês | num | %
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if tokens[0].lower() == "total":
            continue
        try:
            mes = int(tokens[0])
        except (ValueError, IndexError):
            continue
        if not (1 <= mes <= 12):
            continue
        try:
            registros.append({
                "ano":        ano,
                "mes":        mes,
                "data":       pd.Timestamp(year=ano, month=mes, day=1).date(),
                "total":      int(tokens[1]),
                "percentual": float(tokens[2]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


def parse_tipos_fraude_mensal(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para tipos-fraude-mensal.txt.
    Formato: Mês | Total | malware | % | phishing | %
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if tokens[0].lower() == "total":
            continue
        try:
            mes = int(tokens[0])
        except (ValueError, IndexError):
            continue
        if not (1 <= mes <= 12):
            continue
        try:
            registros.append({
                "ano":             ano,
                "mes":             mes,
                "data":            pd.Timestamp(year=ano, month=mes, day=1).date(),
                "total":           int(tokens[1]),
                "malware":         int(tokens[2]),
                "malware_pct":     float(tokens[3]),
                "phishing":        int(tokens[4]),
                "phishing_pct":    float(tokens[5]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


def parse_top_portas(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para top-portas.txt.
    Formato: num | % | porta
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if len(tokens) < 3:
            continue
        try:
            registros.append({
                "ano":        ano,
                "porta":      tokens[2],
                "total":      int(tokens[0]),
                "percentual": float(tokens[1]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


def parse_top_cc(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para top-cc.txt.
    Formato: num | % | cc | name (name pode ter espaços)
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if len(tokens) < 4:
            continue
        try:
            registros.append({
                "ano":        ano,
                "cc":         tokens[2],
                "nome_pais":  " ".join(tokens[3:]),
                "total":      int(tokens[0]),
                "percentual": float(tokens[1]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


def parse_top_asn(texto: str, ano: int) -> pd.DataFrame:
    """
    Parser para top-asn.txt.
    Formato: num | % | asn | cc | nome_as (nome_as pode ter espaços)
    """
    linhas = _split_linhas(texto)
    registros = []
    for tokens in linhas:
        if len(tokens) < 5:
            continue
        try:
            registros.append({
                "ano":        ano,
                "asn":        int(tokens[2]),
                "cc":         tokens[3],
                "nome_as":    " ".join(tokens[4:]),
                "total":      int(tokens[0]),
                "percentual": float(tokens[1]),
            })
        except (ValueError, IndexError):
            continue
    return pd.DataFrame(registros)


# Mapa parser por chave de arquivo
PARSERS = {
    "tipos_incidente":        parse_tipos_incidente,
    "tipos_incidente_mensal": parse_tipos_incidente_mensal,
    "incidentes_mensal":      parse_incidentes_mensal,
    "tipos_fraude_mensal":    parse_tipos_fraude_mensal,
    "top_portas":             parse_top_portas,
    "top_cc":                 parse_top_cc,
    "top_asn":                parse_top_asn,
}


# ─── Orquestração ────────────────────────────────────────────────────────────
def extrair_globais(out_dir: Path) -> None:
    """Baixa e processa incidentes.txt e dos.txt."""
    print("\n[Grupo A] Séries históricas globais")
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for chave, arquivo in ARQS_GLOBAIS.items():
        url = f"{BASE_URL}/{arquivo}"
        print(f"  · {chave:12s}  ", end="", flush=True)
        texto = baixar(url)
        if texto is None:
            print("falhou")
            continue
        # Salva o bruto
        (raw_dir / arquivo).write_text(texto, encoding="utf-8")
        # Processa
        df = parse_serie_global(texto)
        csv = out_dir / f"{chave}_anual.csv"
        df.to_csv(csv, index=False, encoding="utf-8-sig")
        print(f"OK ({len(df)} linhas → {csv.name})")
        time.sleep(PAUSA_SEG)


def extrair_anual(ano: int, out_dir: Path) -> dict[str, pd.DataFrame]:
    """Baixa e processa todos os arquivos de um ano. Retorna dict de DFs."""
    raw_dir = out_dir / "raw" / str(ano)
    raw_dir.mkdir(parents=True, exist_ok=True)
    resultados = {}

    for chave, arquivo in ARQS_ANUAIS.items():
        url = f"{BASE_URL}/{ano}/{arquivo}"
        texto = baixar(url)
        if texto is None:
            print(f"      {chave}: 404")
            continue
        (raw_dir / arquivo).write_text(texto, encoding="utf-8")
        parser = PARSERS[chave]
        df = parser(texto, ano)
        resultados[chave] = df
        time.sleep(PAUSA_SEG)

    return resultados


def consolidar_anos(todos: dict[int, dict], out_dir: Path) -> None:
    """Consolida o detalhamento de todos os anos em CSVs únicos por categoria."""
    print("\nConsolidando e salvando CSVs por gráfico:")

    for chave in ARQS_ANUAIS.keys():
        frames = [d[chave] for d in todos.values() if chave in d]
        if not frames:
            continue
        df = pd.concat(frames, ignore_index=True)
        csv = out_dir / f"{chave}.csv"
        df.to_csv(csv, index=False, encoding="utf-8-sig")
        print(f"  · {chave:28s}  → {csv.name}  ({len(df)} linhas)")


# ─── Main ────────────────────────────────────────────────────────────────────
def main() -> None:
    ano_ini, ano_fim = ANO_INI, ANO_FIM
    if len(sys.argv) >= 3:
        ano_ini, ano_fim = int(sys.argv[1]), int(sys.argv[2])

    OUT_DIR.mkdir(exist_ok=True)
    print(f"Extraindo dados do CERT.br para {OUT_DIR.resolve()}")
    print(f"Período do detalhamento anual: {ano_ini} a {ano_fim}")

    # Grupo A — séries globais (independem de ano)
    extrair_globais(OUT_DIR)

    # Grupo B — detalhamento por ano
    print(f"\n[Grupo B] Detalhamento por ano")
    todos = {}
    for ano in range(ano_ini, ano_fim + 1):
        print(f"  · {ano}:")
        dfs = extrair_anual(ano, OUT_DIR)
        if dfs:
            todos[ano] = dfs

    consolidar_anos(todos, OUT_DIR)

    print(f"\nConcluído. Arquivos em: {OUT_DIR.resolve()}")
    print("\nResumo dos CSVs gerados:")
    for csv in sorted(OUT_DIR.glob("*.csv")):
        print(f"  {csv.name:35s}  {csv.stat().st_size:>9} bytes")


if __name__ == "__main__":
    main()
