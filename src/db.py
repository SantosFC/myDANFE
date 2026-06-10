"""Camada de persistência MariaDB.

Configuração via variáveis de ambiente (ou arquivo .env):
    DANFE_DB_HOST      (default: localhost)
    DANFE_DB_PORT      (default: 3306)
    DANFE_DB_USER      (default: danfe)
    DANFE_DB_PASSWORD
    DANFE_DB_NAME      (default: mydanfe)
"""

import difflib
import os
from contextlib import contextmanager

import pymysql
import pymysql.cursors

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


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS emitente (
        cnpj        VARCHAR(14)  NOT NULL PRIMARY KEY,
        nome        VARCHAR(255),
        logradouro  VARCHAR(255),
        municipio   VARCHAR(100),
        uf          CHAR(2)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS nota (
        chave           VARCHAR(44)   NOT NULL PRIMARY KEY,
        cnpj_emitente   VARCHAR(14)   NOT NULL,
        data_emissao    DATE,
        numero          VARCHAR(9),
        serie           VARCHAR(3),
        valor_total     DECIMAL(15,2),
        CONSTRAINT fk_nota_emitente FOREIGN KEY (cnpj_emitente)
            REFERENCES emitente(cnpj)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS produto_canonico (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        nome            VARCHAR(255) NOT NULL,
        ncm             VARCHAR(8),
        unidade_padrao  VARCHAR(10),
        ean             VARCHAR(14),
        UNIQUE KEY uq_ean (ean)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS produto_alias (
        id                      INT AUTO_INCREMENT PRIMARY KEY,
        id_produto_canonico     INT NOT NULL,
        cnpj_emitente           VARCHAR(14),
        codigo_produto_nota     VARCHAR(60),
        descricao_nota          VARCHAR(255),
        confirmado              TINYINT(1) DEFAULT 0,
        CONSTRAINT fk_alias_canonico FOREIGN KEY (id_produto_canonico)
            REFERENCES produto_canonico(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS item (
        id                      INT AUTO_INCREMENT PRIMARY KEY,
        chave_nota              VARCHAR(44) NOT NULL,
        id_produto_canonico     INT,
        codigo_produto_nota     VARCHAR(60),
        descricao_nota          VARCHAR(255),
        ncm                     VARCHAR(8),
        unidade                 VARCHAR(10),
        quantidade              DECIMAL(15,4),
        valor_unitario          DECIMAL(15,4),
        valor_total             DECIMAL(15,2),
        CONSTRAINT fk_item_nota FOREIGN KEY (chave_nota)
            REFERENCES nota(chave),
        CONSTRAINT fk_item_canonico FOREIGN KEY (id_produto_canonico)
            REFERENCES produto_canonico(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


@contextmanager
def _conn():
    con = pymysql.connect(**_config())
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    """Cria todas as tabelas se não existirem."""
    with _conn() as con:
        with con.cursor() as cur:
            for stmt in SCHEMA_STATEMENTS:
                cur.execute(stmt)


def upsert_emitente(cnpj: str, nome: str, logradouro: str = "", municipio: str = "", uf: str = "") -> None:
    """INSERT IGNORE no emitente."""
    sql = """
        INSERT IGNORE INTO emitente (cnpj, nome, logradouro, municipio, uf)
        VALUES (%s, %s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (cnpj, nome, logradouro, municipio, uf))


def upsert_nota(chave: str, cnpj_emitente: str, data_emissao, numero: str = "", serie: str = "", valor_total=None) -> None:
    """INSERT IGNORE na nota."""
    sql = """
        INSERT IGNORE INTO nota (chave, cnpj_emitente, data_emissao, numero, serie, valor_total)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (chave, cnpj_emitente, data_emissao, numero, serie, valor_total))


def insert_item(chave_nota: str, codigo_produto_nota: str, descricao_nota: str,
                ncm: str, unidade: str, quantidade, valor_unitario, valor_total) -> int:
    """Insere um item e retorna o id inserido."""
    sql = """
        INSERT INTO item
        (chave_nota, codigo_produto_nota, descricao_nota, ncm, unidade,
         quantidade, valor_unitario, valor_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (chave_nota, codigo_produto_nota, descricao_nota,
                               ncm, unidade, quantidade, valor_unitario, valor_total))
            return cur.lastrowid


def link_item_to_produto(item_id: int, id_produto_canonico: int) -> None:
    """Atualiza o item com o produto_canonico vinculado."""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE item SET id_produto_canonico = %s WHERE id = %s",
                (id_produto_canonico, item_id),
            )


def find_produto_by_ean(ean: str):
    """Retorna a linha de produto_canonico pelo EAN, ou None."""
    if not ean or ean.upper() in ("SEM GTIN", ""):
        return None
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM produto_canonico WHERE ean = %s", (ean,))
            return cur.fetchone()


def find_alias(cnpj_emitente: str, codigo_produto_nota: str):
    """Retorna a linha de produto_alias correspondente, ou None."""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM produto_alias
                WHERE cnpj_emitente = %s AND codigo_produto_nota = %s
                LIMIT 1
                """,
                (cnpj_emitente, codigo_produto_nota),
            )
            return cur.fetchone()


def find_similar_aliases(descricao: str, limit: int = 5) -> list:
    """Retorna lista de (alias, produto_canonico) ordenada por similaridade com descricao."""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT pa.*, pc.nome AS pc_nome, pc.ncm AS pc_ncm,
                       pc.unidade_padrao, pc.ean
                FROM produto_alias pa
                JOIN produto_canonico pc ON pc.id = pa.id_produto_canonico
                """
            )
            rows = cur.fetchall()

    scored = []
    for row in rows:
        score = difflib.SequenceMatcher(
            None, descricao.upper(), (row.get("descricao_nota") or "").upper()
        ).ratio()
        scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(row, score) for score, row in scored[:limit]]


def create_produto_canonico(nome: str, ncm: str = "", unidade_padrao: str = "", ean: str = None) -> int:
    """Cria um novo produto_canonico e retorna o id."""
    sql = """
        INSERT INTO produto_canonico (nome, ncm, unidade_padrao, ean)
        VALUES (%s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (nome, ncm, unidade_padrao, ean or None))
            return cur.lastrowid


def create_alias(id_produto_canonico: int, cnpj_emitente: str, codigo_produto_nota: str,
                 descricao_nota: str, confirmado: bool = False) -> int:
    """Cria um novo produto_alias e retorna o id."""
    sql = """
        INSERT INTO produto_alias
        (id_produto_canonico, cnpj_emitente, codigo_produto_nota, descricao_nota, confirmado)
        VALUES (%s, %s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (id_produto_canonico, cnpj_emitente, codigo_produto_nota,
                               descricao_nota, int(confirmado)))
            return cur.lastrowid


def get_unlinked_items() -> list:
    """Retorna itens onde id_produto_canonico IS NULL."""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM item WHERE id_produto_canonico IS NULL")
            return cur.fetchall()


def ingest_nota(emitente_data: dict, nota_data: dict, items_data: list) -> int:
    """
    Orquestra upsert_emitente + upsert_nota + insert_item para cada item,
    depois chama o linker para cada item inserido.
    Retorna a contagem de itens inseridos.
    """
    from .linker import link_item as _link_item

    upsert_emitente(
        cnpj=emitente_data["cnpj"],
        nome=emitente_data.get("nome", ""),
        logradouro=emitente_data.get("logradouro", ""),
        municipio=emitente_data.get("municipio", ""),
        uf=emitente_data.get("uf", ""),
    )
    upsert_nota(
        chave=nota_data["chave"],
        cnpj_emitente=emitente_data["cnpj"],
        data_emissao=nota_data.get("data_emissao"),
        numero=nota_data.get("numero", ""),
        serie=nota_data.get("serie", ""),
        valor_total=nota_data.get("valor_total"),
    )

    count = 0
    for it in items_data:
        item_id = insert_item(
            chave_nota=nota_data["chave"],
            codigo_produto_nota=it.get("codigo_produto_nota", ""),
            descricao_nota=it.get("descricao_nota", ""),
            ncm=it.get("ncm", ""),
            unidade=it.get("unidade", ""),
            quantidade=it.get("quantidade", 0),
            valor_unitario=it.get("valor_unitario", 0),
            valor_total=it.get("valor_total", 0),
        )
        count += 1
        result = _link_item({**it, "cnpj_emitente": emitente_data["cnpj"]})
        if result["status"] == "linked" and result["id_produto_canonico"] is not None:
            link_item_to_produto(item_id, result["id_produto_canonico"])

    return count


def query_all() -> list:
    """Compatibilidade: retorna itens com campos equivalentes ao esquema antigo."""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    i.id,
                    n.chave   AS nfe_chave,
                    n.data_emissao,
                    e.cnpj    AS cnpj_emitente,
                    e.nome    AS nome_emitente,
                    i.codigo_produto_nota AS codigo_produto,
                    i.descricao_nota      AS descricao,
                    i.ncm,
                    i.unidade,
                    i.quantidade,
                    i.valor_unitario,
                    i.valor_total
                FROM item i
                JOIN nota n ON n.chave = i.chave_nota
                JOIN emitente e ON e.cnpj = n.cnpj_emitente
                ORDER BY n.data_emissao
                """
            )
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Compatibility shim — used by ingest.py and dashboard.py (old flat Item flow)
# ---------------------------------------------------------------------------

def insert_items(items) -> int:
    """
    Compatibilidade com o fluxo antigo que passa uma lista de Item dataclass.
    Agrupa por nota e chama ingest_nota para cada grupo.
    """
    from collections import defaultdict

    groups: dict = defaultdict(list)
    meta: dict = {}

    for it in items:
        key = it.nfe_chave
        if key not in meta:
            meta[key] = {
                "emitente": {
                    "cnpj": it.cnpj_emitente,
                    "nome": it.nome_emitente,
                },
                "nota": {
                    "chave": it.nfe_chave,
                    "data_emissao": it.data_emissao,
                },
            }
        groups[key].append({
            "codigo_produto_nota": it.codigo_produto,
            "descricao_nota": it.descricao,
            "ncm": it.ncm,
            "unidade": it.unidade,
            "quantidade": it.quantidade,
            "valor_unitario": it.valor_unitario,
            "valor_total": it.valor_total,
            "ean": getattr(it, "ean", None),
        })

    total = 0
    for key, item_list in groups.items():
        total += ingest_nota(meta[key]["emitente"], meta[key]["nota"], item_list)
    return total
