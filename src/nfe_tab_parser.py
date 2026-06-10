"""Parse do texto copiado da aba NFe da Consulta Completa NFC-e (Sefaz-SP).

Extrai dados do emitente e do cabeçalho da nota.
O texto dos Produtos/Serviços é tratado pelo txt_parser.py.
"""

import re
from datetime import date

RE_CHAVE = re.compile(r"Chave de acesso\b[^\n]*\n([\d\-./]+)\s")
RE_DATA_EMISSAO = re.compile(r"Data de Emiss[ãa]o\s*\n([\d/]+)")
RE_NUMERO = re.compile(r"\bN[úu]mero\s*\n(\d+)")
RE_SERIE = re.compile(r"\bS[ée]rie\s*\n(\d+)")
RE_VALOR_TOTAL = re.compile(r"Valor Total da Nota Fiscal\s*\n([\d.,]+)")

# Bloco do Emitente: entre "Emitente" e "Destinatário"
RE_BLOCO_EMITENTE = re.compile(
    r"Emitente\s*\nCNPJ\s*\n([\d./\-]+).*?Nome / Razão Social\s*\n(.+?)\s*\t.*?UF\s*\n([A-Z]{2})",
    re.DOTALL,
)


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def parse_nfe_tab(text: str) -> dict:
    """
    Retorna dict com chaves:
      emitente: {cnpj, nome, uf}
      nota:     {chave, data_emissao, numero, serie, valor_total}
    Lança ValueError se campos obrigatórios não forem encontrados.
    """
    m = RE_CHAVE.search(text)
    if not m:
        raise ValueError("Chave de acesso não encontrada.")
    chave = re.sub(r"\D", "", m.group(1))

    m = RE_DATA_EMISSAO.search(text)
    if not m:
        raise ValueError("Data de emissão não encontrada.")
    data_emissao = date(*reversed([int(x) for x in m.group(1).split("/")]))

    m_num  = RE_NUMERO.search(text)
    m_ser  = RE_SERIE.search(text)
    m_val  = RE_VALOR_TOTAL.search(text)
    m_emit = RE_BLOCO_EMITENTE.search(text)

    if not m_emit:
        raise ValueError("Dados do emitente não encontrados.")

    cnpj = re.sub(r"\D", "", m_emit.group(1))
    nome = m_emit.group(2).strip()
    uf   = m_emit.group(3).strip()

    return {
        "emitente": {
            "cnpj": cnpj,
            "nome": nome,
            "uf":   uf,
            "logradouro": "",
            "municipio":  "",
        },
        "nota": {
            "chave":        chave,
            "data_emissao": data_emissao,
            "numero":       m_num.group(1) if m_num else "",
            "serie":        m_ser.group(1) if m_ser else "",
            "valor_total":  _num(m_val.group(1)) if m_val else None,
        },
    }
