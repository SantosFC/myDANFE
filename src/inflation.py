"""Cálculo do índice de inflação pessoal."""

import pandas as pd


def build_dataframe(rows) -> pd.DataFrame:
    cols = [
        "id", "nfe_chave", "data_emissao", "cnpj_emitente", "nome_emitente",
        "codigo_produto", "descricao", "ncm", "unidade",
        "quantidade", "valor_unitario", "valor_total",
    ]
    df = pd.DataFrame([dict(r) for r in rows], columns=cols)
    df["data_emissao"] = pd.to_datetime(df["data_emissao"])
    df["ano_mes"] = df["data_emissao"].dt.to_period("M")
    return df


def preco_medio_mensal(df: pd.DataFrame, descricao: str) -> pd.DataFrame:
    """Preço médio ponderado por quantidade para um produto, mês a mês."""
    prod = df[df["descricao"].str.upper() == descricao.upper()].copy()
    agg = (
        prod.groupby("ano_mes")
        .apply(
            lambda g: (g["valor_unitario"] * g["quantidade"]).sum() / g["quantidade"].sum(),
            include_groups=False,
        )
        .rename("preco_medio")
        .reset_index()
    )
    agg["ano_mes_str"] = agg["ano_mes"].astype(str)
    return agg


def inflacao_pessoal_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variação percentual mês a mês do gasto total ponderado pela
    mesma cesta de produtos (itens presentes em pelo menos 2 meses).
    """
    monthly = (
        df.groupby(["ano_mes", "descricao"])["valor_total"]
        .sum()
        .reset_index()
    )
    # mantém apenas produtos com presenças em múltiplos meses
    counts = monthly.groupby("descricao")["ano_mes"].nunique()
    recorrentes = counts[counts >= 2].index
    basket = monthly[monthly["descricao"].isin(recorrentes)]

    gasto_mensal = basket.groupby("ano_mes")["valor_total"].sum().reset_index()
    gasto_mensal = gasto_mensal.sort_values("ano_mes")
    gasto_mensal["variacao_pct"] = gasto_mensal["valor_total"].pct_change() * 100
    gasto_mensal["ano_mes_str"] = gasto_mensal["ano_mes"].astype(str)
    return gasto_mensal


def top_produtos_por_gasto(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    return (
        df.groupby("descricao")["valor_total"]
        .sum()
        .nlargest(n)
        .reset_index()
        .rename(columns={"valor_total": "gasto_total"})
    )
