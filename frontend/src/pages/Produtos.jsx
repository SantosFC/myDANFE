import { useEffect, useState } from "react";
import { listarProdutos, renomearProduto } from "../api";

export default function Produtos() {
  const [descricoes, setDescricoes] = useState([]);
  const [selecionado, setSelecionado] = useState("");
  const [novoNome, setNovoNome] = useState("");
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listarProdutos().then((d) => {
      setDescricoes(d);
      if (d.length) { setSelecionado(d[0]); setNovoNome(d[0]); }
    });
  }, []);

  function handleSelect(e) {
    setSelecionado(e.target.value);
    setNovoNome(e.target.value);
    setMsg(null);
  }

  async function handleSalvar() {
    setLoading(true);
    setMsg(null);
    try {
      const { atualizados } = await renomearProduto(selecionado, novoNome.trim());
      setMsg({ tipo: "success", texto: `✅ ${atualizados} item(s) renomeado(s).` });
      const novos = await listarProdutos();
      setDescricoes(novos);
      setSelecionado(novoNome.trim());
      setNovoNome(novoNome.trim());
    } catch (e) {
      setMsg({ tipo: "error", texto: e.response?.data?.detail || "Erro ao renomear." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Editar Descrição de Produtos</h1>
      <p style={{ color: "#666", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Selecione um produto pelo nome original da nota e defina um nome mais legível.
        A alteração se aplica a todos os registros com essa descrição.
      </p>

      {msg && <div className={`alert alert-${msg.tipo}`}>{msg.texto}</div>}

      {descricoes.length === 0 ? (
        <div className="alert alert-info">Nenhum produto cadastrado ainda.</div>
      ) : (
        <div className="card">
          <p style={{ fontSize: "0.85rem", color: "#666", marginBottom: "1rem" }}>
            {descricoes.length} produto(s) cadastrado(s)
          </p>
          <div className="form-group">
            <label>Produto</label>
            <select value={selecionado} onChange={handleSelect}>
              {descricoes.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Nova descrição</label>
            <input
              type="text"
              value={novoNome}
              onChange={(e) => setNovoNome(e.target.value)}
            />
          </div>
          {novoNome.trim() && novoNome.trim() !== selecionado && (
            <p style={{ fontSize: "0.85rem", color: "#555", marginBottom: "1rem" }}>
              Renomear <strong>"{selecionado}"</strong> → <strong>"{novoNome.trim()}"</strong>
            </p>
          )}
          <button
            className="btn-primary"
            disabled={!novoNome.trim() || novoNome.trim() === selecionado || loading}
            onClick={handleSalvar}
          >
            {loading ? "Salvando..." : "Salvar"}
          </button>
        </div>
      )}
    </div>
  );
}
