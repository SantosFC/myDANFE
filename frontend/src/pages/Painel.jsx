import { useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { getResumo, getInflacao, getTopProdutos, getEvolucao, getRegistros } from "../api";

function fmt(n) { return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(n); }

export default function Painel() {
  const [resumo, setResumo] = useState(null);
  const [inflacao, setInflacao] = useState(null);
  const [topProdutos, setTopProdutos] = useState([]);
  const [evolucao, setEvolucao] = useState([]);
  const [produtos, setProdutos] = useState([]);
  const [produtoSel, setProdutoSel] = useState("");
  const [registros, setRegistros] = useState([]);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    getResumo().then(setResumo);
    getInflacao().then(setInflacao);
    getTopProdutos().then((d) => {
      setTopProdutos(d);
      const nomes = d.map((p) => p.descricao_nota).sort((a, b) => a.localeCompare(b, "pt-BR"));
      setProdutos(nomes);
      if (nomes.length) { setProdutoSel(nomes[0]); }
    });
  }, []);

  useEffect(() => {
    if (produtoSel) getEvolucao(produtoSel).then(setEvolucao);
  }, [produtoSel]);

  function handleVerRegistros() {
    if (!showTable) getRegistros().then(setRegistros);
    setShowTable((v) => !v);
  }

  if (!resumo) return <p className="spinner">Carregando...</p>;

  const ipca = inflacao?.ipca || {};
  const cestaDados = (inflacao?.minha_cesta || []).map((d) => ({
    mes: d.ano_mes_str,
    cesta: d.variacao_pct,
    ipca: ipca[d.ano_mes_str] ?? null,
  }));

  return (
    <div>
      <h1>Painel</h1>

      <div className="metrics">
        <div className="metric">
          <div className="metric-label">Total de compras</div>
          <div className="metric-value">{resumo.total_compras.toLocaleString("pt-BR")}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Produtos únicos</div>
          <div className="metric-value">{resumo.produtos_unicos.toLocaleString("pt-BR")}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Estabelecimentos</div>
          <div className="metric-value">{resumo.estabelecimentos.toLocaleString("pt-BR")}</div>
        </div>
        <div className="metric">
          <div className="metric-label">Gasto total</div>
          <div className="metric-value">{fmt(resumo.gasto_total)}</div>
        </div>
      </div>

      <div className="card">
        <h2>Variação mensal — sua cesta vs IPCA</h2>
        {cestaDados.length === 0 ? (
          <p style={{ color: "#999" }}>Dados insuficientes. Importe notas de pelo menos 2 meses.</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={cestaDados}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="mes" />
              <YAxis unit="%" />
              <Tooltip formatter={(v) => `${v?.toFixed(2)}%`} />
              <Legend />
              <Bar dataKey="cesta" name="Minha cesta" fill="#1565c0" />
              <Line dataKey="ipca" name="IPCA oficial" stroke="#e53935" dot={false} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid-2">
        <div className="card">
          <h2>Top 15 produtos por gasto total</h2>
          <ResponsiveContainer width="100%" height={380}>
            <BarChart data={[...topProdutos].reverse()} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tickFormatter={(v) => fmt(v)} />
              <YAxis type="category" dataKey="descricao_nota" width={160} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => fmt(v)} />
              <Bar dataKey="gasto_total" name="Gasto" fill="#1565c0" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2>Evolução de preço por produto</h2>
          <div className="form-group">
            <select value={produtoSel} onChange={(e) => setProdutoSel(e.target.value)}>
              {produtos.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          {evolucao.length === 0 ? (
            <p style={{ color: "#999" }}>Sem histórico suficiente.</p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={evolucao}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="ano_mes_str" />
                <YAxis tickFormatter={(v) => fmt(v)} />
                <Tooltip formatter={(v) => fmt(v)} />
                <Line dataKey="preco_medio" name="Preço médio" stroke="#1565c0" dot />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card">
        <button className="btn-secondary" onClick={handleVerRegistros}>
          {showTable ? "Ocultar registros" : "Ver todos os registros"}
        </button>
        {showTable && (
          <div style={{ marginTop: "1rem", overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Emitente</th>
                  <th>Produto</th>
                  <th>Qtd</th>
                  <th>Vl. Unit.</th>
                  <th>Vl. Total</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((r, i) => (
                  <tr key={i}>
                    <td>{r.data_emissao}</td>
                    <td>{r.nome_emitente}</td>
                    <td>{r.descricao_nota}</td>
                    <td>{r.quantidade}</td>
                    <td>{fmt(r.valor_unitario)}</td>
                    <td>{fmt(r.valor_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
