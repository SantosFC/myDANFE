"""Camada de persistência MariaDB.

Configuração via variáveis de ambiente (ou arquivo .env):
    DANFE_DB_HOST      (default: localhost)
    DANFE_DB_PORT      (default: 3306)
    DANFE_DB_USER      (default: danfe)
    DANFE_DB_PASSWORD
    DANFE_DB_NAME      (default: mydanfe)
"""

import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors

from .parser import Item

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _config() -> dict:
    return {
        "host": os.environ.get("DANFE_DB_HOST", "localhost"),
        "port": int(os.environ.get("DANFE_DB_PORT", "3306")),
        "user": os.environ.get("DANFE_DB_USER", "danfe"),
        "password": os.environ.get("DANFE_DB_PASSWORD", ""),
        "database": os.environ.get("DANFE_DB_NAME", "mydanfe"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
    }


SCHEMA = """
CREATE TABLE IF NOT EXISTS compras (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nfe_chave       VARCHAR(44)  NOT NULL,
    data_emissao    DATE         NOT NULL,
    cnpj_emitente   VARCHAR(14)  NOT NULL,
    nome_emitente   VARCHAR(255) NOT NULL,
    codigo_produto  VARCHAR(60)  NOT NULL,
    descricao       VARCHAR(255) NOT NULL,
    ncm             VARCHAR(8),
    unidade         VARCHAR(10),
    quantidade      DECIMAL(15,4) NOT NULL,
    valor_unitario  DECIMAL(15,4) NOT NULL,
    valor_total     DECIMAL(15,2) NOT NULL,
    UNIQUE KEY uq_nfe_produto (nfe_chave, codigo_produto),
    INDEX idx_descricao (descricao),
    INDEX idx_data (data_emissao),
    INDEX idx_cnpj (cnpj_emitente)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


@contextmanager
def _conn():
    con = pymysql.connect(**_config())
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(SCHEMA)


def insert_items(items: list[Item]) -> int:
    """Insere itens ignorando duplicatas. Retorna quantos foram inseridos."""
    rows = [
        (
            i.nfe_chave, i.data_emissao, i.cnpj_emitente, i.nome_emitente,
            i.codigo_produto, i.descricao, i.ncm, i.unidade,
            i.quantidade, i.valor_unitario, i.valor_total,
        )
        for i in items
    ]
    sql = """
        INSERT IGNORE INTO compras
        (nfe_chave, data_emissao, cnpj_emitente, nome_emitente,
         codigo_produto, descricao, ncm, unidade,
         quantidade, valor_unitario, valor_total)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.executemany(sql, rows)
            return cur.rowcount


def query_all() -> list[dict]:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM compras ORDER BY data_emissao")
            return cur.fetchall()
