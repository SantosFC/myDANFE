"""Parse XMLs de NFe e extrai itens de compra."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path


NS = {
    "nfe": "http://www.portalfiscal.inf.br/nfe",
}


@dataclass
class Item:
    nfe_chave: str
    data_emissao: date
    cnpj_emitente: str
    nome_emitente: str
    codigo_produto: str
    descricao: str
    ncm: str
    unidade: str
    quantidade: float
    valor_unitario: float
    valor_total: float


def _text(element, path: str) -> str:
    node = element.find(path, NS)
    return node.text.strip() if node is not None and node.text else ""


def parse_xml(xml_path: Path) -> list[Item]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # aceita tanto <nfeProc> quanto <NFe> como raiz
    nfe = root.find("nfe:NFe", NS) or root
    inf_nfe = nfe.find("nfe:infNFe", NS)
    if inf_nfe is None:
        raise ValueError(f"infNFe não encontrado em {xml_path}")

    chave = inf_nfe.get("Id", "").lstrip("NFe")

    ide = inf_nfe.find("nfe:ide", NS)
    data_str = _text(ide, "nfe:dhEmi") or _text(ide, "nfe:dEmi")
    data_emissao = date.fromisoformat(data_str[:10])

    emit = inf_nfe.find("nfe:emit", NS)
    cnpj = _text(emit, "nfe:CNPJ")
    nome = _text(emit, "nfe:xNome")

    items = []
    for det in inf_nfe.findall("nfe:det", NS):
        prod = det.find("nfe:prod", NS)
        items.append(
            Item(
                nfe_chave=chave,
                data_emissao=data_emissao,
                cnpj_emitente=cnpj,
                nome_emitente=nome,
                codigo_produto=_text(prod, "nfe:cProd"),
                descricao=_text(prod, "nfe:xProd"),
                ncm=_text(prod, "nfe:NCM"),
                unidade=_text(prod, "nfe:uCom"),
                quantidade=float(_text(prod, "nfe:qCom") or 0),
                valor_unitario=float(_text(prod, "nfe:vUnCom") or 0),
                valor_total=float(_text(prod, "nfe:vProd") or 0),
            )
        )
    return items


def parse_directory(xml_dir: Path) -> list[Item]:
    all_items: list[Item] = []
    xmls = list(xml_dir.glob("*.xml"))
    if not xmls:
        return all_items
    for xml_path in xmls:
        try:
            all_items.extend(parse_xml(xml_path))
        except Exception as exc:
            print(f"[AVISO] {xml_path.name}: {exc}")
    return all_items
