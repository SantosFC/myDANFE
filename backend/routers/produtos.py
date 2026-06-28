from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_unique_descriptions, rename_descricao

router = APIRouter()


class RenameRequest(BaseModel):
    novo_nome: str


@router.get("/")
def listar():
    return get_unique_descriptions()


@router.put("/{descricao:path}")
def renomear(descricao: str, req: RenameRequest):
    if not req.novo_nome.strip():
        raise HTTPException(400, detail="Nova descrição não pode ser vazia.")
    n = rename_descricao(descricao, req.novo_nome.strip())
    return {"atualizados": n}
