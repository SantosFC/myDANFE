"""Painel Streamlit — inflação pessoal a partir de XMLs de NFe."""

import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.nfe_tab_parser import parse_nfe_tab
from src.txt_parser import parse_txt
from src.db import init_db, insert_items, ingest_nota, query_all
from src.inflation import build_dataframe, inflacao_pessoal_mensal, preco_medio_mensal, top_produtos_por_gasto
from src.ipca import fetch_ipca

st.set_page_config(page_title="Inflação Pessoal", layout="wide")
st.title("myDANFE — Inflação Pessoal")

# --- Carregar dados ---
try:
    init_db()
except Exception as exc:
    st.error(
        f"Erro ao conectar ao banco: {exc}\n\n"
        "Verifique as variáveis DANFE_DB_HOST, DANFE_DB_USER, "
        "DANFE_DB_PASSWORD e DANFE_DB_NAME."
    )
    st.stop()

# --- Navegação ---
pagina = st.sidebar.radio("Menu", ["Painel", "Importar Nota"])

# ════════════════════════════════════════════════════════
# PÁGINA: IMPORTAR NOTA
# ════════════════════════════════════════════════════════
if pagina == "Importar Nota":
    st.header("Importar Nota Fiscal")
    st.caption(
        "Cole o texto copiado da Consulta Completa NFC-e (Sefaz-SP). "
        "Use Ctrl+A → Ctrl+C em cada aba."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Aba NFe ou Emitente")
        texto_nfe = st.text_area(
            "Cole aqui o texto da aba NFe ou Emitente",
            height=300,
            placeholder="Nota Fiscal de Consumidor Eletrônica\n\nChave de acesso ...",
            label_visibility="collapsed",
        )

    with col2:
        st.subheader("2. Aba Produtos / Serviços")
        texto_prod = st.text_area(
            "Cole aqui o texto da aba Produtos",
            height=300,
            placeholder="Dados dos Produtos e Serviços\nNum.\t\nDescrição ...",
            label_visibility="collapsed",
        )

    if st.button("Processar", type="primary", disabled=not (texto_nfe and texto_prod)):
        try:
            cabecalho = parse_nfe_tab(texto_nfe)

            with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
                f.write(texto_prod)
                tmp = Path(f.name)
            itens = parse_txt(tmp)
            tmp.unlink()

            st.session_state["preview_cab"]  = cabecalho
            st.session_state["preview_itens"] = itens
            st.session_state["importado"] = False

        except Exception as exc:
            st.error(f"Erro ao processar: {exc}")

    # --- Preview ---
    if "preview_cab" in st.session_state and not st.session_state.get("importado"):
        cab   = st.session_state["preview_cab"]
        itens = st.session_state["preview_itens"]
        e = cab["emitente"]
        n = cab["nota"]

        st.divider()
        st.subheader("Preview")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Emitente", e["nome_fantasia"] or e["nome"])
        c2.metric("Data", str(n["data_emissao"]) if n["data_emissao"] else "—")
        c3.metric("Nota", f"Série {n['serie']} nº {n['numero']}")
        c4.metric("Total", f"R$ {n['valor_total']:.2f}" if n["valor_total"] else "—")

        rows = []
        for i in itens:
            rows.append({
                "Descrição": i.descricao,
                "Qtd": i.quantidade,
                "Un": i.unidade,
                "Vl. Unit.": f"R$ {i.valor_unitario:.2f}",
                "Vl. Total": f"R$ {i.valor_total:.2f}",
                "EAN": i.ean or "—",
                "NCM": i.ncm,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        total = sum(i.valor_total for i in itens)
        st.markdown(f"**Total dos itens: R$ {total:.2f}**")

        if st.button("Confirmar e Salvar", type="primary"):
            try:
                itens_dict = [
                    {
                        "codigo_produto": i.codigo_produto,
                        "descricao":      i.descricao,
                        "ncm":            i.ncm,
                        "unidade":        i.unidade,
                        "quantidade":     i.quantidade,
                        "valor_unitario": i.valor_unitario,
                        "valor_total":    i.valor_total,
                        "ean":            i.ean,
                    }
                    for i in itens
                ]
                ingest_nota(e, n, itens_dict)
                st.session_state["importado"] = True
                st.success(f"Nota importada com sucesso! {len(itens)} itens salvos.")
                st.balloons()
            except Exception as exc:
                st.error(f"Erro ao salvar: {exc}")

# ════════════════════════════════════════════════════════
# PÁGINA: PAINEL
# ════════════════════════════════════════════════════════
else:
    rows = query_all()

    if not rows:
        st.info("Nenhum dado ainda. Vá em **Importar Nota** para adicionar sua primeira nota.")
        st.stop()

    df = build_dataframe(rows)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de compras", f"{len(df):,}")
    col2.metric("Produtos únicos", f"{df['descricao_nota'].nunique():,}")
    col3.metric("Estabelecimentos", f"{df['nome_emitente'].nunique():,}")
    col4.metric("Gasto total", f"R$ {df['valor_total'].sum():,.2f}")

    st.divider()

    st.subheader("Variação mensal — sua cesta vs IPCA")
    infl = inflacao_pessoal_mensal(df).dropna(subset=["variacao_pct"])
    ipca_dict = fetch_ipca()

    fig = go.Figure()
    fig.add_bar(x=infl["ano_mes_str"], y=infl["variacao_pct"], name="Minha cesta", marker_color="#2196F3")
    if ipca_dict:
        meses = infl["ano_mes_str"].tolist()
        ipca_vals = [ipca_dict.get(m) for m in meses]
        fig.add_scatter(x=meses, y=ipca_vals, mode="lines+markers", name="IPCA oficial", line=dict(color="#FF5722", width=2))
    fig.update_layout(yaxis_title="Variação (%)", xaxis_title="Mês", legend=dict(orientation="h"), height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Top 15 produtos por gasto total")
        top = top_produtos_por_gasto(df)
        fig2 = px.bar(top, x="gasto_total", y="descricao_nota", orientation="h",
                      labels={"gasto_total": "Gasto (R$)", "descricao_nota": ""}, height=450)
        fig2.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.subheader("Evolução de preço por produto")
        produtos = sorted(df["descricao_nota"].unique().tolist())
        produto_sel = st.selectbox("Selecione o produto", produtos)
        if produto_sel:
            hist = preco_medio_mensal(df, produto_sel)
            if len(hist) >= 2:
                var_total = ((hist["preco_medio"].iloc[-1] / hist["preco_medio"].iloc[0]) - 1) * 100
                st.caption(f"Variação acumulada no período: **{var_total:+.1f}%**")
            fig3 = px.line(hist, x="ano_mes_str", y="preco_medio", markers=True,
                           labels={"ano_mes_str": "Mês", "preco_medio": "Preço médio (R$)"}, height=380)
            st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    with st.expander("Ver todos os registros"):
        st.dataframe(
            df[["data_emissao", "nome_emitente", "descricao_nota", "quantidade", "valor_unitario", "valor_total"]]
            .sort_values("data_emissao", ascending=False)
            .reset_index(drop=True),
            use_container_width=True,
        )
