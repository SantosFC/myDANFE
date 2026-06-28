import axios from "axios";

const api = axios.create({ baseURL: "/api" });

export const processar = (texto_nfe, texto_prod) =>
  api.post("/notas/processar", { texto_nfe, texto_prod }).then((r) => r.data);

export const salvar = (emitente, nota, itens) =>
  api.post("/notas/salvar", { emitente, nota, itens }).then((r) => r.data);

export const listarProdutos = () => api.get("/produtos/").then((r) => r.data);

export const renomearProduto = (descricao, novo_nome) =>
  api.put(`/produtos/${encodeURIComponent(descricao)}`, { novo_nome }).then((r) => r.data);

export const getResumo = () => api.get("/painel/resumo").then((r) => r.data);
export const getInflacao = () => api.get("/painel/inflacao").then((r) => r.data);
export const getTopProdutos = () => api.get("/painel/top-produtos").then((r) => r.data);
export const getEvolucao = (produto) =>
  api.get(`/painel/evolucao/${encodeURIComponent(produto)}`).then((r) => r.data);
export const getRegistros = () => api.get("/painel/registros").then((r) => r.data);
