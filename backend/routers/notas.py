import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import ingest_nota, nota_already_imported
from backend.parsers.nfe_tab_parser import parse_nfe_tab
from backend.parsers.txt_parser import parse_txt

router = APIRouter()


class ParseRequest(BaseModel):
    texto_nfe: str
    texto_prod: str


class SaveRequest(BaseModel):
    emitente: dict
    nota: dict
    itens: list[dict]


@router.post("/processar")
def processar(req: ParseRequest):
    try:
        cabecalho = parse_nfe_tab(req.texto_nfe)
    except ValueError as e:
        raise HTTPException(400, detail=f"Erro no campo NFe: {e}")

    with tempfile.NamedTemporaryFile(
        suffix=".txt", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(req.texto_prod)
        tmp = Path(f.name)
    try:
        itens = parse_txt(tmp)
    except ValueError as e:
        raise HTTPException(400, detail=f"Erro nos produtos: {e}")
    finally:
        tmp.unlink(missing_ok=True)

    e = cabecalho["emitente"]
    n = cabecalho["nota"]
    ja_importada = nota_already_imported(n["chave"])

    return {
        "emitente": e,
        "nota": {**n, "data_emissao": str(n["data_emissao"]) if n["data_emissao"] else None},
        "itens": [
            {
                "descricao": i.descricao,
                "quantidade": i.quantidade,
                "unidade": i.unidade,
                "valor_unitario": i.valor_unitario,
                "valor_total": i.valor_total,
                "ean": i.ean or "",
                "ncm": i.ncm,
                "codigo_produto": i.codigo_produto,
            }
            for i in itens
        ],
        "ja_importada": ja_importada,
    }


@router.post("/salvar")
def salvar(req: SaveRequest):
    try:
        count = ingest_nota(req.emitente, req.nota, req.itens)
    except ValueError as e:
        raise HTTPException(409, detail=str(e))
    except Exception as e:
        raise HTTPException(500, detail=str(e))
    return {"itens_salvos": count}
