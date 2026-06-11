"""Parse PDFs de DANFE NFC-e e extrai itens.

Dois layouts suportados:

1. **Resumo do consumidor** (consulta pública simplificada, Sefaz-SP):
       DESCRICAO DO PRODUTO (Código: 123 )
       Qtde.:0,55UN: kgVl. Unit.:   14,98
       Vl. Total
       8,24

2. **Consulta Completa NFC-e** (visão fiscal detalhada, Sefaz-SP):
       Num. Descrição Qtd. Unidade Comercial Valor(R$)
       1 DESCRICAO 0,4300 Kg 59,250
       Código do Produto
       40003
       ...
       Valor unitário de comercialização
       137,8000000000
"""

import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from .parser import Item

# --- Layout 1: Resumo consumidor ---
RE_ITEM_RESUMO = re.compile(
    r"(?P<desc>.+?)\s*\(C[óo]digo:\s*(?P<cod>\S+)\s*\)\s*\n"
    r"Qtde\.:\s*(?P<qtd>[\d.,]+)\s*UN:\s*(?P<un>\S+)\s*Vl\. Unit\.:\s*(?P<vunit>[\d.,]+)\s*\n"
    r"Vl\. Total\s*\n"
    r"(?P<vtotal>[\d.,]+)",
    re.IGNORECASE,
)
RE_CNPJ = re.compile(r"CNPJ:\s*([\d./-]+)")
RE_EMISSAO_RESUMO = re.compile(r"Emiss[ãa]o:\s*(\d{2}/\d{2}/\d{4})")
RE_CHAVE_RESUMO = re.compile(r"Chave de acesso:\s*\n?((?:\d{4}\s*){11})")

# --- Layout 2: Consulta Completa ---
# Chave no formato: 35-2606-07.985.900/0004-27-65-001-000.236.945-130.829.096-5
# A linha seguinte ao cabeçalho "Chave de acesso ... Versão XML"
RE_CHAVE_COMPLETA = re.compile(r"Chave de acesso\b.*?\n([\d\-./]+)\s")
RE_DATA_HORA = re.compile(r"Data/Hora:\s*(\d{2}/\d{2}/\d{4})")
# Linha de item: "1 DESCRICAO 0,4300 Kg 59,250"
RE_ITEM_LINHA = re.compile(
    r"^(\d+) (.+?) ([\d,]+) (\w+) ([\d,]+)$",
    re.MULTILINE,
)
RE_COD_PRODUTO = re.compile(r"Código do Produto\n(\S+)")
RE_NCM = re.compile(r"Código NCM\n(\d+)")
RE_VUNIT = re.compile(r"Valor unitário de comercialização\n([\d,]+)")


def _num(s: str) -> float:
    """Converte número em formato brasileiro: '1.234,56' -> 1234.56"""
    return float(s.replace(".", "").replace(",", "."))


def _chave_completa_para_44(raw: str) -> str:
    """Remove separadores e extrai os 44 dígitos da chave."""
    return re.sub(r"\D", "", raw)


def _detect_layout(text: str) -> str:
    if "DADOS DOS PRODUTOS E SERVIÇOS" in text.upper():
        return "completa"
    return "resumo"


def _parse_resumo(text: str, pdf_path: Path) -> list[Item]:
    m = RE_CNPJ.search(text)
    cnpj = re.sub(r"\D", "", m.group(1)) if m else ""
    nome = ""
    if m:
        antes = text[: m.start()].strip().splitlines()
        if antes:
            nome = antes[-1].strip()

    m = RE_EMISSAO_RESUMO.search(text)
    if not m:
        raise ValueError(f"Data de emissão não encontrada em {pdf_path}")
    data_emissao = datetime.strptime(m.group(1), "%d/%m/%Y").date()

    m = RE_CHAVE_RESUMO.search(text)
    chave = re.sub(r"\s", "", m.group(1)) if m else ""
    if not chave:
        raise ValueError(f"Chave de acesso não encontrada em {pdf_path}")

    items = []
    for it in RE_ITEM_RESUMO.finditer(text):
        items.append(
            Item(
                nfe_chave=chave,
                data_emissao=data_emissao,
                cnpj_emitente=cnpj,
                nome_emitente=nome,
                codigo_produto=it.group("cod"),
                descricao=it.group("desc").strip(),
                ncm="",
                unidade=it.group("un"),
                quantidade=_num(it.group("qtd")),
                valor_unitario=_num(it.group("vunit")),
                valor_total=_num(it.group("vtotal")),
            )
        )
    return items


def _parse_completa(text: str, pdf_path: Path) -> list[Item]:
    m = RE_CHAVE_COMPLETA.search(text)
    if not m:
        raise ValueError(f"Chave de acesso não encontrada em {pdf_path}")
    chave = _chave_completa_para_44(m.group(1))
    # CNPJ está embutido na chave (posições 3-16)
    cnpj = chave[6:20]

    m = RE_DATA_HORA.search(text)
    if not m:
        raise ValueError(f"Data/Hora não encontrada em {pdf_path}")
    data_emissao = datetime.strptime(m.group(1), "%d/%m/%Y").date()

    # extrai listas paralelas: item_linhas, códigos, NCMs, preços unitários
    item_linhas = list(RE_ITEM_LINHA.finditer(text))
    codigos = [m.group(1) for m in RE_COD_PRODUTO.finditer(text)]
    ncms = [m.group(1) for m in RE_NCM.finditer(text)]
    vunits = [m.group(1) for m in RE_VUNIT.finditer(text)]

    items = []
    for i, it in enumerate(item_linhas):
        qtd = _num(it.group(3))
        vtotal = _num(it.group(5))
        vunit = _num(vunits[i]) if i < len(vunits) else (vtotal / qtd if qtd else 0)
        items.append(
            Item(
                nfe_chave=chave,
                data_emissao=data_emissao,
                cnpj_emitente=cnpj,
                nome_emitente="",  # não disponível neste layout
                codigo_produto=codigos[i] if i < len(codigos) else str(i + 1),
                descricao=it.group(2).strip(),
                ncm=ncms[i] if i < len(ncms) else "",
                unidade=it.group(4),
                quantidade=qtd,
                valor_unitario=vunit,
                valor_total=vtotal,
            )
        )
    return items


def parse_pdf(pdf_path: Path) -> list[Item]:
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    layout = _detect_layout(text)
    if layout == "completa":
        items = _parse_completa(text, pdf_path)
    else:
        items = _parse_resumo(text, pdf_path)

    if not items:
        raise ValueError(f"Nenhum item encontrado em {pdf_path}")
    return items


def parse_pdf_directory(pdf_dir: Path) -> list[Item]:
    all_items: list[Item] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        try:
            all_items.extend(parse_pdf(pdf_path))
        except Exception as exc:
            print(f"[AVISO] {pdf_path.name}: {exc}")
    return all_items
