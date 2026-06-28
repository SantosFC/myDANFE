import { useState } from "react";
import { processar, salvar } from "../api";

const RE_CHAVE = /[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}[\s\-.]?[\d]{4}/;

function extrairChave(text) {
  const m = text.match(RE_CHAVE);
  if (!m) return null;
  return m[0].replace(/\D/g, "");
}

export default function ImportarNota() {
  const [nfe, setNfe] = useState("");
  const [prod, setProd] = useState("");
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState(null);

  const chaveNfe = extrairChave(nfe);
  const chaveProd = extrairChave(prod);

  function keyStatus() {
    if (chaveNfe && chaveProd) {
      return chaveNfe === chaveProd
        ? { cls: "key-match", text: `✅ Chaves conferem — ${chaveNfe.slice(0, 10)}...${chaveNfe.slice(-6)}` }
        : { cls: "key-mismatch", text: "❌ Chaves não coincidem — verifique se colou abas da mesma nota" };
    }
    if (chaveNfe) return { cls: "key-partial", text: `🔑 Chave no campo 1: ${chaveNfe.slice(0, 10)}...${chaveNfe.slice(-6)}` };
    if (chaveProd) return { cls: "key-partial", text: `🔑 Chave no campo 2: ${chaveProd.slice(0, 10)}...${chaveProd.slice(-6)}` };
    return null;
  }

  async function handleProcessar() {
    setLoading(true);
    setMsg(null);
    try {
      const data = await processar(nfe, prod);
      setPreview(data);
    } catch (e) {
      setMsg({ tipo: "error", texto: e.response?.data?.detail || "Erro ao processar." });
    } finally {
      setLoading(false);
    }
  }

  async function handleSalvar() {
    setLoading(true);
    setMsg(null);
    try {
      const { itens_salvos } = await salvar(preview.emitente, preview.nota, preview.itens);
      setMsg({ tipo: "success", texto: `✅ Nota salva com sucesso! ${itens_salvos} itens importados.` });
      setPreview(null);
      setNfe("");
      setProd("");
    } catch (e) {
      setMsg({ tipo: "error", texto: e.response?.data?.detail || "Erro ao salvar." });
    } finally {
      setLoading(false);
    }
  }

  const ks = keyStatus();

  return (
    <div>
      <h1>Importar Nota Fiscal</h1>
      <p style={{ color: "#666", marginBottom: "1.5rem", fontSize: "0.9rem" }}>
        Cole o texto copiado da Consulta Completa NFC-e (Sefaz-SP). Use Ctrl+A → Ctrl+C em cada aba.
      </p>

      {msg && <div className={`alert alert-${msg.tipo}`}>{msg.texto}</div>}

      <div className="grid-2" style={{ marginBottom: "1rem" }}>
        <div className="card">
          <h2>1. Aba NFe</h2>
          <textarea
            rows={12}
            placeholder={"Nota Fiscal de Consumidor Eletrônica\n\nChave de acesso ..."}
            value={nfe}
            onChange={(e) => setNfe(e.target.value)}
          />
        </div>
        <div className="card">
          <h2>2. Aba Produtos / Serviços</h2>
          <textarea
            rows={12}
            placeholder={"Dados dos Produtos e Serviços\nNum.\t\nDescrição ..."}
            value={prod}
            onChange={(e) => setProd(e.target.value)}
          />
        </div>
      </div>

      {ks && <div className={`key-check ${ks.cls}`}>{ks.text}</div>}

      <button
        className="btn-primary"
        disabled={!nfe || !prod || loading}
        onClick={handleProcessar}
      >
        {loading ? "Processando..." : "Processar"}
      </button>

      {preview && (
        <div style={{ marginTop: "2rem" }}>
          <div className="metrics">
            <div className="metric">
              <div className="metric-label">Emitente</div>
              <div className="metric-value" style={{ fontSize: "1rem" }}>
                {preview.emitente.nome_fantasia || preview.emitente.nome}
              </div>
            </div>
            <div className="metric">
              <div className="metric-label">Data</div>
              <div className="metric-value" style={{ fontSize: "1rem" }}>{preview.nota.data_emissao || "—"}</div>
            </div>
            <div className="metric">
              <div className="metric-label">Nota</div>
              <div className="metric-value" style={{ fontSize: "1rem" }}>
                Série {preview.nota.serie} nº {preview.nota.numero}
              </div>
            </div>
            <div className="metric">
              <div className="metric-label">Total</div>
              <div className="metric-value" style={{ fontSize: "1rem" }}>
                {preview.nota.valor_total ? `R$ ${Number(preview.nota.valor_total).toFixed(2)}` : "—"}
              </div>
            </div>
          </div>

          {preview.ja_importada ? (
            <div className="alert alert-warning">⚠️ Esta nota já foi importada anteriormente.</div>
          ) : (
            <div className="alert alert-info">📋 {preview.itens.length} itens prontos para importação.</div>
          )}

          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Descrição</th>
                  <th>Qtd</th>
                  <th>Un</th>
                  <th>Vl. Unit.</th>
                  <th>Vl. Total</th>
                  <th>EAN</th>
                  <th>NCM</th>
                </tr>
              </thead>
              <tbody>
                {preview.itens.map((it, i) => (
                  <tr key={i}>
                    <td>{it.descricao}</td>
                    <td>{it.quantidade}</td>
                    <td>{it.unidade}</td>
                    <td>R$ {it.valor_unitario.toFixed(2)}</td>
                    <td>R$ {it.valor_total.toFixed(2)}</td>
                    <td>{it.ean || "—"}</td>
                    <td>{it.ncm}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ marginTop: "0.75rem", fontWeight: 600 }}>
              Total: R$ {preview.itens.reduce((s, i) => s + i.valor_total, 0).toFixed(2)}
            </p>
          </div>

          <button
            className="btn-primary"
            disabled={preview.ja_importada || loading}
            onClick={handleSalvar}
          >
            {loading ? "Salvando..." : "Confirmar e Salvar"}
          </button>
        </div>
      )}
    </div>
  );
}
