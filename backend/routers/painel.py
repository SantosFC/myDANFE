from fastapi import APIRouter

from backend.db import query_all
from backend.inflation import (
    build_dataframe,
    inflacao_pessoal_mensal,
    preco_medio_mensal,
    top_produtos_por_gasto,
)
from backend.ipca import fetch_ipca

router = APIRouter()


def _rows_to_df():
    rows = query_all()
    if not rows:
        return None
    return build_dataframe(rows)


@router.get("/resumo")
def resumo():
    df = _rows_to_df()
    if df is None:
        return {
            "total_compras": 0,
            "produtos_unicos": 0,
            "estabelecimentos": 0,
            "gasto_total": 0,
        }
    return {
        "total_compras": len(df),
        "produtos_unicos": int(df["descricao_nota"].nunique()),
        "estabelecimentos": int(df["nome_emitente"].nunique()),
        "gasto_total": float(df["valor_total"].sum()),
    }


@router.get("/inflacao")
def inflacao():
    df = _rows_to_df()
    if df is None:
        return {"minha_cesta": [], "ipca": {}}
    infl = inflacao_pessoal_mensal(df).dropna(subset=["variacao_pct"])
    ipca = fetch_ipca()
    return {
        "minha_cesta": infl[["ano_mes_str", "variacao_pct"]].to_dict(orient="records"),
        "ipca": ipca,
    }


@router.get("/top-produtos")
def top_produtos():
    df = _rows_to_df()
    if df is None:
        return []
    top = top_produtos_por_gasto(df)
    return top.to_dict(orient="records")


@router.get("/evolucao/{produto:path}")
def evolucao(produto: str):
    df = _rows_to_df()
    if df is None:
        return []
    hist = preco_medio_mensal(df, produto)
    if hist.empty:
        return []
    return hist[["ano_mes_str", "preco_medio"]].to_dict(orient="records")


@router.get("/registros")
def registros():
    rows = query_all()
    result = []
    for r in rows:
        result.append(
            {
                "data_emissao": str(r["data_emissao"]) if r["data_emissao"] else None,
                "nome_emitente": r["nome_emitente"],
                "descricao_nota": r["descricao_nota"],
                "quantidade": float(r["quantidade"] or 0),
                "valor_unitario": float(r["valor_unitario"] or 0),
                "valor_total": float(r["valor_total"] or 0),
            }
        )
    return result
