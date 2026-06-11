#!/usr/bin/env python3
"""Script CLI para importar XMLs, PDFs e TXTs de NFe/NFC-e sem abrir o painel."""

from pathlib import Path
from src.parser import parse_directory
from src.pdf_parser import parse_pdf_directory
from src.txt_parser import parse_txt_directory
from src.db import init_db, insert_items

XML_DIR = Path("data/xmls")
PDF_DIR = Path("data/pdfs")
TXT_DIR = Path("data/txts")


def main():
    init_db()
    items = (
        parse_directory(XML_DIR)
        + parse_pdf_directory(PDF_DIR)
        + parse_txt_directory(TXT_DIR)
    )
    if not items:
        print("Nenhum arquivo encontrado em data/xmls/, data/pdfs/ ou data/txts/")
        return
    inserted = insert_items(items)
    print(f"{inserted} novos itens inseridos de {len(items)} registros lidos.")


if __name__ == "__main__":
    main()
