"""Parse PDFs de DANFE NFC-e (cupom de consumidor) e extrai itens.

Layout suportado: impressão da consulta pública da NFC-e (Sefaz-SP),
onde cada item aparece como:

    DESCRICAO DO PRODUTO (Código: 123 )
    Qtde.:0,55UN: kgVl. Unit.:   14,98
    Vl. Total
    8,24
"""

import re
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from .parser import Item

RE_ITEM = re.compile(
    r"(?P<desc>.+?)\s*\(C[óo]digo:\s*(?P<cod>\S+)\s*\)\s*\n"
    r"Qtde\.:\s*(?P<qtd>[\d.,]+)\s*UN:\s*(?P<un>\S+)\s*Vl\. Unit\.:\s*(?P<vunit>[\d.,]+)\s*\n"
    r"Vl\. Total\s*\n"
    r"(?P<vtotal>[\d.,]+)",
    re.IGNORECASE,
)
RE_CNPJ = re.compile(r"CNPJ:\s*([\d./-]+)")
RE_EMISSAO = re.compile(r"Emiss[ãa]o:\s*(\d{2}/\d{2}/\d{4})")
RE_CHAVE = re.compile(r"Chave de acesso:\s*\n?((?:\d{4}\s*){11})")


def _num(s: str) -> float:
    """Converte número em formato brasileiro: '1.234,56' -> 1234.56"""
    return float(s.replace(".", "").replace(",", "."))


def parse_pdf(pdf_path: Path) -> list[Item]:
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    m = RE_CNPJ.search(text)
    cnpj = re.sub(r"\D", "", m.group(1)) if m else ""

    # nome do emitente: linha imediatamente anterior ao CNPJ
    nome = ""
    if m:
        antes = text[: m.start()].strip().splitlines()
        if antes:
            nome = antes[-1].strip()

    m = RE_EMISSAO.search(text)
    if not m:
        raise ValueError(f"Data de emissão não encontrada em {pdf_path}")
    data_emissao = datetime.strptime(m.group(1), "%d/%m/%Y").date()

    m = RE_CHAVE.search(text)
    chave = re.sub(r"\s", "", m.group(1)) if m else ""
    if not chave:
        raise ValueError(f"Chave de acesso não encontrada em {pdf_path}")

    items = []
    for it in RE_ITEM.finditer(text):
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
