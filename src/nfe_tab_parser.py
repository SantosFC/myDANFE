"""Parse do texto copiado das abas NFe ou Emitente da Consulta Completa NFC-e (Sefaz-SP).

Detecta automaticamente qual aba foi colada:
- Aba NFe:      tem Data de Emissão, Número, Série, Valor Total
- Aba Emitente: tem Endereço, Bairro, Município completos

Ambas fornecem CNPJ e Nome do emitente.
A chave de acesso está no cabeçalho das duas abas.
"""

import re
from datetime import date, datetime


RE_CHAVE = re.compile(r"Chave de acesso\b[^\n]*\n([\d\-./]+)\s")

# --- Aba NFe ---
RE_DATA_EMISSAO = re.compile(r"Data de Emiss[ãa]o\s*\n([\d/]+)")
RE_NUMERO       = re.compile(r"\bN[úu]mero\s*\n(\d+)")
RE_SERIE        = re.compile(r"\bS[ée]rie\s*\n(\d+)")
RE_VALOR_TOTAL  = re.compile(r"Valor Total da Nota Fiscal\s*\n([\d.,]+)")
RE_EMITENTE_NFE = re.compile(
    r"Emitente\s*\nCNPJ\s*\n([\d./\-]+).*?Nome / Razão Social\s*\n(.+?)\s*\t.*?UF\s*\n([A-Z]{2})",
    re.DOTALL,
)

# --- Aba Emitente ---
RE_NOME_EMIT    = re.compile(r"Nome / Razão Social\s*\n(.+?)\s*\t")
RE_NOME_FANTASIA = re.compile(r"Nome Fantasia\s*\n(.+?)\n")
RE_CNPJ_EMIT    = re.compile(r"CNPJ\s*\n([\d./\-]+)\s*\t")
RE_LOGRADOURO   = re.compile(r"Endere[çc]o\s*\n(.+?)\n")
RE_MUNICIPIO    = re.compile(r"Munic[íi]pio\s*\n\d+ - (.+?)\s*\t")
RE_UF_EMIT      = re.compile(r"\bUF\s*\n([A-Z]{2})\s*\t")


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _chave_para_campos(chave: str) -> dict:
    """Extrai série, número e data (AAMM) dos 44 dígitos da chave."""
    if len(chave) != 44:
        return {"serie": "", "numero": "", "data_emissao": None}
    serie  = str(int(chave[22:25]))
    numero = str(int(chave[25:34]))
    ano = 2000 + int(chave[2:4])
    mes = int(chave[4:6])
    try:
        data = date(ano, mes, 1)
    except ValueError:
        data = None
    return {"serie": serie, "numero": numero, "data_emissao": data}


def _detect_tab(text: str) -> str:
    if "Dados do Emitente" in text:
        return "emitente"
    return "nfe"


def _parse_aba_emitente(text: str, chave: str) -> dict:
    m_nome    = RE_NOME_EMIT.search(text)
    m_fantasia = RE_NOME_FANTASIA.search(text)
    m_cnpj    = RE_CNPJ_EMIT.search(text)
    m_uf      = RE_UF_EMIT.search(text)
    m_log     = RE_LOGRADOURO.search(text)
    m_mun     = RE_MUNICIPIO.search(text)

    if not m_cnpj or not m_nome:
        raise ValueError("CNPJ ou Nome do emitente não encontrados na aba Emitente.")

    cnpj = re.sub(r"\D", "", m_cnpj.group(1))
    campos_chave = _chave_para_campos(chave)

    return {
        "emitente": {
            "cnpj":          cnpj,
            "nome":          m_nome.group(1).strip(),
            "nome_fantasia": m_fantasia.group(1).strip() if m_fantasia else "",
            "uf":            m_uf.group(1).strip() if m_uf else "",
            "logradouro":    m_log.group(1).strip() if m_log else "",
            "municipio":     m_mun.group(1).strip() if m_mun else "",
        },
        "nota": {
            "chave":        chave,
            "data_emissao": campos_chave["data_emissao"],
            "numero":       campos_chave["numero"],
            "serie":        campos_chave["serie"],
            "valor_total":  None,
        },
    }


def _parse_aba_nfe(text: str, chave: str) -> dict:
    m_data = RE_DATA_EMISSAO.search(text)
    if not m_data:
        raise ValueError("Data de emissão não encontrada.")
    data_emissao = date(*reversed([int(x) for x in m_data.group(1).split("/")]))

    m_emit = RE_EMITENTE_NFE.search(text)
    if not m_emit:
        raise ValueError("Dados do emitente não encontrados.")

    m_num = RE_NUMERO.search(text)
    m_ser = RE_SERIE.search(text)
    m_val = RE_VALOR_TOTAL.search(text)

    return {
        "emitente": {
            "cnpj":          re.sub(r"\D", "", m_emit.group(1)),
            "nome":          m_emit.group(2).strip(),
            "nome_fantasia": "",
            "uf":            m_emit.group(3).strip(),
            "logradouro":    "",
            "municipio":     "",
        },
        "nota": {
            "chave":        chave,
            "data_emissao": data_emissao,
            "numero":       m_num.group(1) if m_num else "",
            "serie":        m_ser.group(1) if m_ser else "",
            "valor_total":  _num(m_val.group(1)) if m_val else None,
        },
    }


def parse_nfe_tab(text: str) -> dict:
    """
    Aceita texto da aba NFe ou da aba Emitente.
    Retorna dict com chaves emitente e nota.
    """
    m = RE_CHAVE.search(text)
    if not m:
        raise ValueError("Chave de acesso não encontrada.")
    chave = re.sub(r"\D", "", m.group(1))

    if _detect_tab(text) == "emitente":
        return _parse_aba_emitente(text, chave)
    return _parse_aba_nfe(text, chave)
