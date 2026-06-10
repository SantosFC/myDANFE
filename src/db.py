"""Camada de persistência SQLite."""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

from .parser import Item

DEFAULT_DB = Path(__file__).parent.parent / "data" / "db" / "danfe.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS compras (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nfe_chave       TEXT NOT NULL,
    data_emissao    TEXT NOT NULL,
    cnpj_emitente   TEXT NOT NULL,
    nome_emitente   TEXT NOT NULL,
    codigo_produto  TEXT NOT NULL,
    descricao       TEXT NOT NULL,
    ncm             TEXT,
    unidade         TEXT,
    quantidade      REAL NOT NULL,
    valor_unitario  REAL NOT NULL,
    valor_total     REAL NOT NULL,
    UNIQUE(nfe_chave, codigo_produto)
);

CREATE INDEX IF NOT EXISTS idx_descricao ON compras(descricao);
CREATE INDEX IF NOT EXISTS idx_data      ON compras(data_emissao);
CREATE INDEX IF NOT EXISTS idx_cnpj      ON compras(cnpj_emitente);
"""


@contextmanager
def _conn(db_path: Path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(db_path: Path = DEFAULT_DB) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _conn(db_path) as con:
        con.executescript(SCHEMA)


def insert_items(items: list[Item], db_path: Path = DEFAULT_DB) -> int:
    """Insere itens ignorando duplicatas. Retorna quantos foram inseridos."""
    rows = [
        (
            i.nfe_chave, str(i.data_emissao), i.cnpj_emitente, i.nome_emitente,
            i.codigo_produto, i.descricao, i.ncm, i.unidade,
            i.quantidade, i.valor_unitario, i.valor_total,
        )
        for i in items
    ]
    sql = """
        INSERT OR IGNORE INTO compras
        (nfe_chave, data_emissao, cnpj_emitente, nome_emitente,
         codigo_produto, descricao, ncm, unidade,
         quantidade, valor_unitario, valor_total)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
    with _conn(db_path) as con:
        cur = con.executemany(sql, rows)
        return cur.rowcount


def query_all(db_path: Path = DEFAULT_DB):
    with _conn(db_path) as con:
        return con.execute(
            "SELECT * FROM compras ORDER BY data_emissao"
        ).fetchall()
