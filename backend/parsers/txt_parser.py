"""Parse texto copiado da Consulta Completa NFC-e (Sefaz-SP).

Como usar:
  1. Abra a nota pelo QR code do cupom
  2. Clique na aba 'Produtos / Serviços'
  3. Ctrl+A → Ctrl+C (selecionar tudo e copiar)
  4. Cole em um arquivo .txt e salve em data/txts/

O texto copiado do navegador usa tabulações como separadores de coluna.
"""

import re
from datetime import datetime
from pathlib import Path

from .xml_parser import Item

RE_CHAVE = re.compile(r"Chave de acesso\b[^\n]*\n([\d\-./]+)\s")
RE_DATA = re.compile(r"Data/Hora:\s*(\d{2}/\d{2}/\d{4})")

# Linha de item com tabs: "1 \tPERA WILLIAMS PREMIUM KG \t0,5500 \tkg \t8,240"
RE_ITEM = re.compile(
    r"^(\d+)\s*\t\s*(.+?)\s*\t\s*([\d,]+)\s*\t\s*(\w+)\s*\t\s*([\d,]+)",
    re.MULTILINE,
)
RE_COD = re.compile(r"Código do Produto\n(\S+)")
RE_NCM = re.compile(r"Código NCM\n(\d+)")
RE_EAN = re.compile(r"Código EAN Comercial\n([^\n\t]+)")
RE_VUNIT = re.compile(r"Valor unitário de comercialização\n([\d,]+)")
RE_DESC = re.compile(r"Valor do Desconto\n([\d,]+)")


def _num(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def _chave_digitos(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def parse_txt(txt_path: Path) -> list[Item]:
    text = txt_path.read_text(encoding="utf-8", errors="replace")

    m = RE_CHAVE.search(text)
    if not m:
        raise ValueError(f"Chave de acesso não encontrada em {txt_path.name}")
    chave = _chave_digitos(m.group(1))
    cnpj = chave[6:20]

    m = RE_DATA.search(text)
    if not m:
        raise ValueError(f"Data/Hora não encontrada em {txt_path.name}")
    data_emissao = datetime.strptime(m.group(1), "%d/%m/%Y").date()

    item_matches = list(RE_ITEM.finditer(text))
    codigos = [x.group(1) for x in RE_COD.finditer(text)]
    ncms = [x.group(1) for x in RE_NCM.finditer(text)]
    eans = [x.group(1) for x in RE_EAN.finditer(text)]
    vunits = [x.group(1) for x in RE_VUNIT.finditer(text)]
    descontos = [x.group(1) for x in RE_DESC.finditer(text)]

    items = []
    for i, it in enumerate(item_matches):
        qtd = _num(it.group(3))
        vtotal_bruto = _num(it.group(5))
        desconto = _num(descontos[i]) if i < len(descontos) else 0.0
        vtotal = vtotal_bruto - desconto
        vunit_raw = _num(vunits[i]) if i < len(vunits) else (vtotal_bruto / qtd if qtd else 0)
        # Recalcula o valor unitário líquido com base no desconto
        vunit = (vunit_raw - desconto / qtd) if qtd else vunit_raw
        ean_raw = eans[i] if i < len(eans) else ""
        items.append(
            Item(
                nfe_chave=chave,
                data_emissao=data_emissao,
                cnpj_emitente=cnpj,
                nome_emitente="",
                codigo_produto=codigos[i] if i < len(codigos) else str(i + 1),
                descricao=it.group(2).strip(),
                ncm=ncms[i] if i < len(ncms) else "",
                unidade=it.group(4),
                quantidade=qtd,
                valor_unitario=round(vunit, 10),
                valor_total=vtotal,
                ean="" if ean_raw.upper() in ("SEM GTIN", "") else ean_raw,
            )
        )

    if not items:
        raise ValueError(f"Nenhum item encontrado em {txt_path.name}")
    return items


def parse_txt_directory(txt_dir: Path) -> list[Item]:
    all_items: list[Item] = []
    for path in sorted(txt_dir.glob("*.txt")):
        try:
            all_items.extend(parse_txt(path))
        except Exception as exc:
            print(f"[AVISO] {path.name}: {exc}")
    return all_items
