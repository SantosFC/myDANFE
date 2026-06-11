"""Camada de persistência PostgreSQL (Supabase).

Configuração via variáveis de ambiente (ou arquivo .env):
    DANFE_DB_HOST      (default: localhost)
    DANFE_DB_PORT      (default: 5432)
    DANFE_DB_USER      (default: postgres)
    DANFE_DB_PASSWORD
    DANFE_DB_NAME      (default: postgres)
"""

import difflib
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _get(key: str, default: str = "") -> str:
    """Lê configuração do st.secrets (Streamlit Cloud) ou os.environ (local)."""
    try:
        import streamlit as st
        return st.secrets.get(key, os.environ.get(key, default))
    except Exception:
        return os.environ.get(key, default)


def _config() -> dict:
    return {
        "host":     _get("DANFE_DB_HOST", "localhost"),
        "port":     int(_get("DANFE_DB_PORT", "5432")),
        "user":     _get("DANFE_DB_USER", "postgres"),
        "password": _get("DANFE_DB_PASSWORD", ""),
        "dbname":   _get("DANFE_DB_NAME", "postgres"),
    }


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS emitente (
        cnpj            VARCHAR(14)  NOT NULL PRIMARY KEY,
        nome            VARCHAR(255),
        nome_fantasia   VARCHAR(255),
        logradouro      VARCHAR(255),
        municipio       VARCHAR(100),
        uf              CHAR(2)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS nota (
        chave           VARCHAR(44)   NOT NULL PRIMARY KEY,
        cnpj_emitente   VARCHAR(14)   NOT NULL REFERENCES emitente(cnpj),
        data_emissao    DATE,
        numero          VARCHAR(9),
        serie           VARCHAR(3),
        valor_total     NUMERIC(15,2)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS produto_canonico (
        id              SERIAL PRIMARY KEY,
        nome            VARCHAR(255) NOT NULL,
        ncm             VARCHAR(8),
        unidade_padrao  VARCHAR(10),
        ean             VARCHAR(14) UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS produto_alias (
        id                      SERIAL PRIMARY KEY,
        id_produto_canonico     INT NOT NULL REFERENCES produto_canonico(id),
        cnpj_emitente           VARCHAR(14),
        codigo_produto_nota     VARCHAR(60),
        descricao_nota          VARCHAR(255),
        confirmado              BOOLEAN DEFAULT FALSE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS item (
        id                      SERIAL PRIMARY KEY,
        chave_nota              VARCHAR(44) NOT NULL REFERENCES nota(chave),
        id_produto_canonico     INT REFERENCES produto_canonico(id),
        codigo_produto_nota     VARCHAR(60),
        descricao_nota          VARCHAR(255),
        ncm                     VARCHAR(8),
        unidade                 VARCHAR(10),
        quantidade              NUMERIC(15,4),
        valor_unitario          NUMERIC(15,4),
        valor_total             NUMERIC(15,2)
    )
    """,
]


@contextmanager
def _conn():
    con = psycopg2.connect(**_config(), cursor_factory=psycopg2.extras.RealDictCursor)
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


def upsert_emitente(cnpj: str, nome: str, nome_fantasia: str = "",
                    logradouro: str = "", municipio: str = "", uf: str = "") -> None:
    sql = """
        INSERT INTO emitente (cnpj, nome, nome_fantasia, logradouro, municipio, uf)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (cnpj) DO UPDATE SET
            nome_fantasia = EXCLUDED.nome_fantasia,
            logradouro    = EXCLUDED.logradouro,
            municipio     = EXCLUDED.municipio,
            uf            = EXCLUDED.uf
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (cnpj, nome, nome_fantasia, logradouro, municipio, uf))


def upsert_nota(chave: str, cnpj_emitente: str, data_emissao, numero: str = "", serie: str = "", valor_total=None) -> None:
    sql = """
        INSERT INTO nota (chave, cnpj_emitente, data_emissao, numero, serie, valor_total)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (chave) DO NOTHING
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (chave, cnpj_emitente, data_emissao, numero, serie, valor_total))


def insert_item(chave_nota: str, codigo_produto_nota: str, descricao_nota: str,
                ncm: str, unidade: str, quantidade, valor_unitario, valor_total) -> int:
    sql = """
        INSERT INTO item
        (chave_nota, codigo_produto_nota, descricao_nota, ncm, unidade,
         quantidade, valor_unitario, valor_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (chave_nota, codigo_produto_nota, descricao_nota,
                              ncm, unidade, quantidade, valor_unitario, valor_total))
            return cur.fetchone()["id"]


def link_item_to_produto(item_id: int, id_produto_canonico: int) -> None:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE item SET id_produto_canonico = %s WHERE id = %s",
                (id_produto_canonico, item_id),
            )


def find_produto_by_ean(ean: str):
    if not ean or ean.upper() in ("SEM GTIN", ""):
        return None
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM produto_canonico WHERE ean = %s", (ean,))
            return cur.fetchone()


def find_alias(cnpj_emitente: str, codigo_produto_nota: str):
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
    sql = """
        INSERT INTO produto_canonico (nome, ncm, unidade_padrao, ean)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (nome, ncm, unidade_padrao, ean or None))
            return cur.fetchone()["id"]


def create_alias(id_produto_canonico: int, cnpj_emitente: str,
                 codigo_produto_nota: str, descricao_nota: str, confirmado: bool = False) -> int:
    sql = """
        INSERT INTO produto_alias
        (id_produto_canonico, cnpj_emitente, codigo_produto_nota, descricao_nota, confirmado)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (id_produto_canonico, cnpj_emitente,
                              codigo_produto_nota, descricao_nota, confirmado))
            return cur.fetchone()["id"]


def get_unlinked_items() -> list:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT i.*, n.data_emissao, n.cnpj_emitente
                FROM item i
                JOIN nota n ON n.chave = i.chave_nota
                WHERE i.id_produto_canonico IS NULL
                ORDER BY n.data_emissao DESC
                """
            )
            return cur.fetchall()


def ingest_nota(emitente: dict, nota: dict, itens: list[dict]) -> int:
    """Orquestra a ingestão completa de uma nota. Retorna itens inseridos."""
    upsert_emitente(
        cnpj=emitente["cnpj"],
        nome=emitente.get("nome", ""),
        nome_fantasia=emitente.get("nome_fantasia", ""),
        logradouro=emitente.get("logradouro", ""),
        municipio=emitente.get("municipio", ""),
        uf=emitente.get("uf", ""),
    )
    upsert_nota(
        chave=nota["chave"],
        cnpj_emitente=emitente["cnpj"],
        data_emissao=nota.get("data_emissao"),
        numero=nota.get("numero", ""),
        serie=nota.get("serie", ""),
        valor_total=nota.get("valor_total"),
    )
    count = 0
    for it in itens:
        item_id = insert_item(
            chave_nota=nota["chave"],
            codigo_produto_nota=it.get("codigo_produto", ""),
            descricao_nota=it.get("descricao", ""),
            ncm=it.get("ncm", ""),
            unidade=it.get("unidade", ""),
            quantidade=it.get("quantidade", 0),
            valor_unitario=it.get("valor_unitario", 0),
            valor_total=it.get("valor_total", 0),
        )
        count += 1
    return count


# --- Compatibilidade com parsers existentes (Item dataclass) ---

def insert_items(items) -> int:
    """Shim de compatibilidade: aceita lista de Item e chama ingest_nota."""
    from itertools import groupby
    inserted = 0
    key = lambda i: i.nfe_chave
    for chave, grupo in groupby(sorted(items, key=key), key=key):
        grupo = list(grupo)
        first = grupo[0]
        emitente = {
            "cnpj": first.cnpj_emitente,
            "nome": first.nome_emitente,
        }
        nota = {
            "chave": chave,
            "data_emissao": first.data_emissao,
        }
        itens = [
            {
                "codigo_produto": i.codigo_produto,
                "descricao": i.descricao,
                "ncm": i.ncm,
                "unidade": i.unidade,
                "quantidade": i.quantidade,
                "valor_unitario": i.valor_unitario,
                "valor_total": i.valor_total,
            }
            for i in grupo
        ]
        inserted += ingest_nota(emitente, nota, itens)
    return inserted


def query_all() -> list:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    i.id,
                    i.chave_nota,
                    i.codigo_produto_nota,
                    i.descricao_nota,
                    i.ncm,
                    i.unidade,
                    i.quantidade,
                    i.valor_unitario,
                    i.valor_total,
                    n.data_emissao,
                    n.cnpj_emitente,
                    e.nome        AS nome_emitente,
                    e.nome_fantasia
                FROM item i
                JOIN nota n ON n.chave = i.chave_nota
                JOIN emitente e ON e.cnpj = n.cnpj_emitente
                ORDER BY n.data_emissao
                """
            )
            return cur.fetchall()
