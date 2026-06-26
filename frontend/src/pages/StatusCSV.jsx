import { useRef, useState } from "react";
import { statusCsv } from "../api";

// Lê o arquivo como texto, tentando UTF-16 LE primeiro (padrão do portal
// Nota Fiscal Paulista) e caindo para UTF-8 se não houver BOM.
function lerArquivo(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = () => reject(new Error("Erro ao ler arquivo"));
    // UTF-16 LE com BOM é o formato padrão do portal SP
    reader.readAsText(file, "UTF-16LE");
  });
}

export default function StatusCSV() {
  const inputRef = useRef(null);
  const [notas, setNotas] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  const totalImportadas = notas?.filter((n) => n.importada).length ?? 0;
  const totalPendentes = notas?.filter((n) => !n.importada).length ?? 0;

  async function handleArquivo(e) {
    const file = e.target.files[0];
    if (!file) return;

    setErro("");
    setNotas(null);
    setCarregando(true);

    try {
      const conteudo = await lerArquivo(file);
      const dados = await statusCsv(conteudo);
      setNotas(dados.notas);
    } catch (err) {
      setErro(err.response?.data?.detail ?? err.message ?? "Erro desconhecido");
    } finally {
      setCarregando(false);
      // Limpa o input para permitir selecionar o mesmo arquivo novamente
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div>
      <h2>Status das Notas (CSV)</h2>
      <p>
        Exporte a lista de notas do portal{" "}
        <strong>Nota Fiscal Paulista</strong> (aba "Consulta NFC-e",
        botão "Exportar CSV") e carregue o arquivo aqui. O sistema vai
        comparar cada nota com o banco de dados e indicar quais já foram
        importadas e quais ainda estão pendentes.
      </p>

      <div style={{ margin: "1.5rem 0" }}>
        <label htmlFor="csv-input" style={{ fontWeight: 600 }}>
          Selecionar arquivo CSV:
        </label>
        <br />
        <input
          id="csv-input"
          ref={inputRef}
          type="file"
          accept=".csv,.txt"
          onChange={handleArquivo}
          style={{ marginTop: "0.5rem" }}
          disabled={carregando}
        />
      </div>

      {carregando && <p className="info">Analisando o CSV...</p>}

      {erro && <p className="erro">Erro: {erro}</p>}

      {notas !== null && (
        <>
          {/* Resumo */}
          <div className="resumo-csv" style={{ marginBottom: "1rem" }}>
            <span className="badge badge-ok">
              {totalImportadas} importada{totalImportadas !== 1 ? "s" : ""}
            </span>
            <span className="badge badge-pendente" style={{ marginLeft: "0.75rem" }}>
              {totalPendentes} pendente{totalPendentes !== 1 ? "s" : ""}
            </span>
            <span style={{ marginLeft: "0.75rem", color: "#666" }}>
              de {notas.length} nota{notas.length !== 1 ? "s" : ""} no CSV
            </span>
          </div>

          {notas.length === 0 ? (
            <p className="info">Nenhuma nota encontrada no CSV.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="tabela-notas">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Data</th>
                    <th>Emitente</th>
                    <th>CNPJ</th>
                    <th>Nº Nota</th>
                    <th style={{ textAlign: "right" }}>Valor (R$)</th>
                    <th>Situação Crédito</th>
                  </tr>
                </thead>
                <tbody>
                  {notas.map((nota) => (
                    <tr
                      key={`${nota.cnpj}-${nota.numero}`}
                      className={nota.importada ? "linha-importada" : "linha-pendente"}
                    >
                      <td>
                        {nota.importada ? (
                          <span className="badge badge-ok">Importada</span>
                        ) : (
                          <span className="badge badge-pendente">Pendente</span>
                        )}
                      </td>
                      <td>{nota.data_emissao}</td>
                      <td>{nota.emitente}</td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
                        {formatarCnpj(nota.cnpj)}
                      </td>
                      <td>{nota.numero}</td>
                      <td style={{ textAlign: "right" }}>
                        {nota.valor != null
                          ? nota.valor.toLocaleString("pt-BR", {
                              minimumFractionDigits: 2,
                            })
                          : "-"}
                      </td>
                      <td>{nota.situacao_credito}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function formatarCnpj(cnpj) {
  if (!cnpj || cnpj.length !== 14) return cnpj;
  return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`;
}
