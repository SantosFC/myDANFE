"""Busca série histórica do IPCA via API pública do IBGE (SIDRA)."""

import urllib.request
import json
from functools import lru_cache


SIDRA_URL = "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/all/d/v2266%202"


@lru_cache(maxsize=1)
def fetch_ipca() -> dict[str, float]:
    """Retorna {ano_mes: variacao_pct} ex: {'2024-01': 0.42}"""
    try:
        with urllib.request.urlopen(SIDRA_URL, timeout=10) as resp:  # nosec B310 — URL fixa do IBGE
            data = json.loads(resp.read())
    except Exception:
        return {}

    result = {}
    for row in data[1:]:  # primeira linha é cabeçalho
        periodo = row.get("D3C", "")  # ex: "202401"
        valor = row.get("V", "")
        if len(periodo) == 6 and valor not in ("", "-", "..."):
            try:
                ano_mes = f"{periodo[:4]}-{periodo[4:]}"
                result[ano_mes] = float(valor)
            except ValueError:
                pass
    return result
