#!/usr/bin/env python3
"""Script CLI para importar XMLs de NFe sem abrir o painel."""

from pathlib import Path
from src.parser import parse_directory
from src.db import init_db, insert_items

XML_DIR = Path("data/xmls")


def main():
    init_db()
    items = parse_directory(XML_DIR)
    if not items:
        print("Nenhum XML encontrado em data/xmls/")
        return
    inserted = insert_items(items)
    print(f"{inserted} novos itens inseridos de {len(items)} registros lidos.")


if __name__ == "__main__":
    main()
