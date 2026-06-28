"""Camada de persistência MariaDB.

Configuração via variáveis de ambiente (ou arquivo .env):
    DB_HOST      (default: localhost)
    DB_PORT      (default: 3306)
    DB_USER      (default: mydanfe)
    DB_PASSWORD
    DB_NAME      (default: mydanfe)
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
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER", "mydanfe"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "mydanfe"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
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
        FOREIGN KEY (cnpj_emitente) REFERENCES emitente(cnpj)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS produto_canonico (
        id              INT AUTO_INCREMENT PRIMARY KEY,
        nome            VARCHAR(255) NOT NULL,
        ncm             VARCHAR(8),
        unidade_padrao  VARCHAR(10),
        ean             VARCHAR(14) UNIQUE
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
        FOREIGN KEY (id_produto_canonico) REFERENCES produto_canonico(id)
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
        FOREIGN KEY (chave_nota) REFERENCES nota(chave),
        FOREIGN KEY (id_produto_canonico) REFERENCES produto_canonico(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS nota_csv (
        id                  INT AUTO_INCREMENT PRIMARY KEY,
        cnpj_emitente       VARCHAR(14)  NOT NULL,
        nome_emitente       VARCHAR(255),
        numero              VARCHAR(20)  NOT NULL,
        data_emissao        DATE,
        valor_total         DECIMAL(15,2),
        situacao_credito    VARCHAR(50),
        UNIQUE KEY uk_nota_csv (cnpj_emitente, numero, data_emissao)
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
    with _conn() as con:
        with con.cursor() as cur:
            for stmt in SCHEMA_STATEMENTS:
                cur.execute(stmt)


def upsert_emitente(
    cnpj: str,
    nome: str,
    nome_fantasia: str = "",
    logradouro: str = "",
    municipio: str = "",
    uf: str = "",
) -> None:
    sql = """
        INSERT INTO emitente (cnpj, nome, nome_fantasia, logradouro, municipio, uf)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nome_fantasia = IF(VALUES(nome_fantasia) <> '', VALUES(nome_fantasia), nome_fantasia),
            logradouro    = IF(VALUES(logradouro)    <> '', VALUES(logradouro),    logradouro),
            municipio     = IF(VALUES(municipio)     <> '', VALUES(municipio),     municipio),
            uf            = IF(VALUES(uf)            <> '', VALUES(uf),            uf)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(sql, (cnpj, nome, nome_fantasia, logradouro, municipio, uf))


def upsert_nota(
    chave: str,
    cnpj_emitente: str,
    data_emissao,
    numero: str = "",
    serie: str = "",
    valor_total=None,
) -> None:
    sql = """
        INSERT IGNORE INTO nota (chave, cnpj_emitente, data_emissao, numero, serie, valor_total)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                sql, (chave, cnpj_emitente, data_emissao, numero, serie, valor_total)
            )


def insert_item(
    chave_nota: str,
    codigo_produto_nota: str,
    descricao_nota: str,
    ncm: str,
    unidade: str,
    quantidade,
    valor_unitario,
    valor_total,
) -> int:
    sql = """
        INSERT INTO item
        (chave_nota, codigo_produto_nota, descricao_nota, ncm, unidade,
         quantidade, valor_unitario, valor_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                sql,
                (
                    chave_nota,
                    codigo_produto_nota,
                    descricao_nota,
                    ncm,
                    unidade,
                    quantidade,
                    valor_unitario,
                    valor_total,
                ),
            )
            return con.insert_id()


def nota_already_imported(chave: str) -> bool:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM item WHERE chave_nota = %s", (chave,)
            )
            return cur.fetchone()["n"] > 0


def nota_exists_by_cnpj_numero_data(cnpj: str, numero: str, data_emissao: str) -> bool:
    """Verifica se uma nota já foi importada usando CNPJ + número + data.

    Usado para cruzar com o CSV da Nota Fiscal Paulista, que não tem a chave de acesso.
    O número é comparado como inteiro para ignorar zeros à esquerda.
    A data deve estar no formato YYYY-MM-DD.
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM nota n
                JOIN item i ON i.chave_nota = n.chave
                WHERE n.cnpj_emitente = %s
                  AND CAST(n.numero AS UNSIGNED) = CAST(%s AS UNSIGNED)
                  AND n.data_emissao = %s
                """,
                (cnpj, numero, data_emissao),
            )
            return cur.fetchone()["n"] > 0


def get_notas_csv() -> list[dict]:
    """Retorna todos os registros da tabela nota_csv com status de importação."""
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    nc.cnpj_emitente,
                    nc.nome_emitente,
                    nc.numero,
                    nc.data_emissao,
                    nc.valor_total,
                    nc.situacao_credito,
                    EXISTS (
                        SELECT 1 FROM nota n
                        JOIN item i ON i.chave_nota = n.chave
                        WHERE n.cnpj_emitente = nc.cnpj_emitente
                          AND CAST(n.numero AS UNSIGNED) = CAST(nc.numero AS UNSIGNED)
                          AND n.data_emissao = nc.data_emissao
                    ) AS importada
                FROM nota_csv nc
                ORDER BY nc.data_emissao DESC, nc.cnpj_emitente
                """
            )
            rows = cur.fetchall()
    result = []
    for r in rows:
        result.append(
            {
                "cnpj": r["cnpj_emitente"],
                "emitente": r["nome_emitente"],
                "numero": r["numero"],
                "data_emissao": r["data_emissao"].strftime("%d/%m/%Y")
                if r["data_emissao"]
                else "",
                "valor": float(r["valor_total"])
                if r["valor_total"] is not None
                else None,
                "situacao_credito": r["situacao_credito"] or "",
                "importada": bool(r["importada"]),
            }
        )
    return result


def upsert_nota_csv(
    cnpj_emitente: str,
    nome_emitente: str,
    numero: str,
    data_emissao,
    valor_total=None,
    situacao_credito: str = "",
) -> None:
    """Insere ou atualiza um registro vindo do CSV da Nota Fiscal Paulista.

    A chave única é (cnpj_emitente, numero, data_emissao).
    Em caso de conflito, atualiza apenas nome_emitente e situacao_credito.
    """
    sql = """
        INSERT INTO nota_csv
            (cnpj_emitente, nome_emitente, numero, data_emissao, valor_total, situacao_credito)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nome_emitente    = VALUES(nome_emitente),
            situacao_credito = VALUES(situacao_credito)
    """
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                sql,
                (
                    cnpj_emitente,
                    nome_emitente,
                    numero,
                    data_emissao,
                    valor_total,
                    situacao_credito,
                ),
            )


def ingest_nota(emitente: dict, nota: dict, itens: list[dict]) -> int:
    if nota_already_imported(nota["chave"]):
        raise ValueError("Nota já importada anteriormente.")
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
        insert_item(
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


def query_all() -> list:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    i.id, i.chave_nota, i.codigo_produto_nota, i.descricao_nota,
                    i.ncm, i.unidade, i.quantidade, i.valor_unitario, i.valor_total,
                    n.data_emissao, n.cnpj_emitente,
                    e.nome AS nome_emitente, e.nome_fantasia
                FROM item i
                JOIN nota n ON n.chave = i.chave_nota
                JOIN emitente e ON e.cnpj = n.cnpj_emitente
                ORDER BY n.data_emissao DESC
                """
            )
            return cur.fetchall()


def get_unique_descriptions() -> list[str]:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT descricao_nota FROM item ORDER BY descricao_nota"
            )
            return [r["descricao_nota"] for r in cur.fetchall() if r["descricao_nota"]]


def rename_descricao(old: str, new: str) -> int:
    with _conn() as con:
        with con.cursor() as cur:
            cur.execute(
                "UPDATE item SET descricao_nota = %s WHERE descricao_nota = %s",
                (new, old),
            )
            return cur.rowcount


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
