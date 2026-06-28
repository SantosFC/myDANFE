import csv
import io
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import (
    get_notas_csv,
    ingest_nota,
    nota_already_imported,
    nota_exists_by_cnpj_numero_data,
    upsert_nota_csv,
)
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


class CsvStatusRequest(BaseModel):
    conteudo_csv: str


def _limpa_cnpj(cnpj: str) -> str:
    """Remove formatação do CNPJ: '02.914.460/0444-41' → '02914460044441'"""
    return "".join(c for c in cnpj if c.isdigit())


def _data_para_iso(data_br: str) -> str | None:
    """Converte 'DD/MM/YYYY' para 'YYYY-MM-DD'. Retorna None se inválida."""
    try:
        return datetime.strptime(data_br.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


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
        "nota": {
            **n,
            "data_emissao": str(n["data_emissao"]) if n["data_emissao"] else None,
        },
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


@router.get("/status-csv")
def get_status_csv():
    """Retorna todos os registros já salvos do CSV com status de importação."""
    return {"notas": get_notas_csv()}


@router.post("/status-csv")
def status_csv(req: CsvStatusRequest):
    """Lê o CSV exportado do portal Nota Fiscal Paulista e retorna cada nota
    com o status de importação: 'importada' ou 'pendente'.

    O CSV pode estar em UTF-16 LE (exportação padrão do portal) ou UTF-8.
    """
    conteudo = req.conteudo_csv

    # O portal exporta em UTF-16 LE com BOM (﻿). Se o frontend enviou o
    # arquivo como texto, o BOM pode aparecer como primeiro caractere.
    conteudo = conteudo.lstrip("﻿")

    try:
        reader = csv.DictReader(
            io.StringIO(conteudo),
            delimiter="\t",
            quotechar='"',
        )
        linhas = list(reader)
    except Exception as e:
        raise HTTPException(400, detail=f"Erro ao ler CSV: {e}")

    if not linhas:
        raise HTTPException(400, detail="CSV vazio ou sem linhas de dados.")

    # Normaliza os nomes das colunas removendo espaços extras e BOM residual
    def _limpa_chave(k: str) -> str:
        return k.strip().lstrip("﻿").strip('"')

    resultado = []
    for i, linha in enumerate(linhas, start=2):  # linha 1 é o cabeçalho
        linha_limpa = {
            _limpa_chave(k): (v or "").strip().strip('"') for k, v in linha.items()
        }

        cnpj_raw = linha_limpa.get("CNPJ emit.", "") or linha_limpa.get(
            "CNPJ emitente", ""
        )
        emitente = linha_limpa.get("Emitente", "")
        numero = linha_limpa.get("No.", "") or linha_limpa.get("Número", "")
        data_emissao_br = linha_limpa.get("Data Emissão", "") or linha_limpa.get(
            "Data Emissao", ""
        )
        valor_raw = linha_limpa.get("Valor NF", "")
        situacao_credito = linha_limpa.get(
            "Situação do Crédito", ""
        ) or linha_limpa.get("Situacao do Credito", "")

        if not cnpj_raw or not numero:
            continue

        cnpj = _limpa_cnpj(cnpj_raw)
        data_iso = _data_para_iso(data_emissao_br)

        # Converte valor brasileiro "70,17" → 70.17
        try:
            valor = float(valor_raw.replace(".", "").replace(",", "."))
        except (ValueError, AttributeError):
            valor = None

        # Persiste no banco (incremental — ignora duplicatas pelo índice único)
        upsert_nota_csv(
            cnpj_emitente=cnpj,
            nome_emitente=emitente,
            numero=numero,
            data_emissao=data_iso,
            valor_total=valor,
            situacao_credito=situacao_credito,
        )

        importada = False
        if data_iso:
            importada = nota_exists_by_cnpj_numero_data(cnpj, numero, data_iso)

        resultado.append(
            {
                "linha": i,
                "cnpj": cnpj,
                "emitente": emitente,
                "numero": numero,
                "data_emissao": data_emissao_br,
                "valor": valor,
                "situacao_credito": situacao_credito,
                "importada": importada,
            }
        )

    return {"notas": resultado}
