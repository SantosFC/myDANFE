"""Painel Streamlit — inflação pessoal a partir de XMLs de NFe."""

from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from .parser import parse_directory
from .db import init_db, insert_items, query_all
from .inflation import build_dataframe, inflacao_pessoal_mensal, preco_medio_mensal, top_produtos_por_gasto
from .ipca import fetch_ipca

DATA_DIR = Path(__file__).parent.parent / "data"
XML_DIR = DATA_DIR / "xmls"


def ingest_xmls():
    items = parse_directory(XML_DIR)
    if items:
        init_db()
        inserted = insert_items(items)
        return inserted, len(items)
    return 0, 0


st.set_page_config(page_title="Inflação Pessoal", layout="wide")
st.title("📊 Inflação Pessoal — myDANFE")

# --- Barra lateral ---
with st.sidebar:
    st.header("Importar XMLs")
    st.caption(f"Coloque seus XMLs de NFe em `data/xmls/`")
    if st.button("🔄 Processar XMLs agora"):
        inserted, total = ingest_xmls()
        if total == 0:
            st.warning("Nenhum XML encontrado.")
        else:
            st.success(f"{inserted} novos itens de {total} registros processados.")

# --- Carregar dados ---
try:
    init_db()
    rows = query_all()
except Exception as exc:
    st.error(
        f"Erro ao conectar ao MariaDB: {exc}\n\n"
        "Verifique as variáveis DANFE_DB_HOST, DANFE_DB_USER, "
        "DANFE_DB_PASSWORD e DANFE_DB_NAME (veja .env.example)."
    )
    st.stop()

if not rows:
    st.info("Nenhum dado ainda. Adicione XMLs de NFe em `data/xmls/` e clique em **Processar XMLs agora**.")
    st.stop()

df = build_dataframe(rows)

# --- Métricas gerais ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de compras", f"{len(df):,}")
col2.metric("Produtos únicos", f"{df['descricao'].nunique():,}")
col3.metric("Estabelecimentos", f"{df['nome_emitente'].nunique():,}")
col4.metric(
    "Gasto total",
    f"R$ {df['valor_total'].sum():,.2f}",
)

st.divider()

# --- Inflação pessoal vs IPCA ---
st.subheader("Variação mensal — sua cesta vs IPCA")

infl = inflacao_pessoal_mensal(df).dropna(subset=["variacao_pct"])
ipca_dict = fetch_ipca()

fig = go.Figure()
fig.add_bar(
    x=infl["ano_mes_str"],
    y=infl["variacao_pct"],
    name="Minha cesta",
    marker_color="#2196F3",
)
if ipca_dict:
    meses = infl["ano_mes_str"].tolist()
    ipca_vals = [ipca_dict.get(m) for m in meses]
    fig.add_scatter(
        x=meses,
        y=ipca_vals,
        mode="lines+markers",
        name="IPCA oficial",
        line=dict(color="#FF5722", width=2),
    )
fig.update_layout(
    yaxis_title="Variação (%)",
    xaxis_title="Mês",
    legend=dict(orientation="h"),
    height=400,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Top produtos por gasto ---
col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader("Top 15 produtos por gasto total")
    top = top_produtos_por_gasto(df)
    fig2 = px.bar(
        top,
        x="gasto_total",
        y="descricao",
        orientation="h",
        labels={"gasto_total": "Gasto (R$)", "descricao": ""},
        height=450,
    )
    fig2.update_layout(yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.subheader("Evolução de preço por produto")
    produtos = sorted(df["descricao"].unique().tolist())
    produto_sel = st.selectbox("Selecione o produto", produtos)
    if produto_sel:
        hist = preco_medio_mensal(df, produto_sel)
        if len(hist) >= 2:
            var_total = (
                (hist["preco_medio"].iloc[-1] / hist["preco_medio"].iloc[0]) - 1
            ) * 100
            st.caption(f"Variação acumulada no período: **{var_total:+.1f}%**")
        fig3 = px.line(
            hist,
            x="ano_mes_str",
            y="preco_medio",
            markers=True,
            labels={"ano_mes_str": "Mês", "preco_medio": "Preço médio (R$)"},
            height=380,
        )
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# --- Tabela bruta ---
with st.expander("Ver todos os registros"):
    st.dataframe(
        df[["data_emissao", "nome_emitente", "descricao", "quantidade", "valor_unitario", "valor_total"]]
        .sort_values("data_emissao", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
    )
