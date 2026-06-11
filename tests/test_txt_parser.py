"""Testes do parser de texto copiado da Consulta Completa NFC-e."""

import pytest
import tempfile
from pathlib import Path
from src.txt_parser import parse_txt

SAMPLE = (
    "Chave de acesso \tNúmero NFC-e \tVersão XML\n"
    "35-2606-35.794.786/0003-02-65-004-000.163.875-137.426.584-5 \t000.163.875 \t4.00\n"
    "Dados dos Produtos e Serviços\n"
    "Num.\n\t\nDescrição\n\t\nQtd.\n\t\nUnidade Comercial\n\t\nValor(R$)\n"
    "1 \tPERA WILLIAMS PREMIUM KG \t0,5500 \tkg \t8,240\n"
    "Código do Produto\n167 \t\nCódigo NCM\n08083000 \t\n"
    "Valor unitário de comercialização\n14,9800000000 \t\n"
    "2 \tMACA GALA KG \t0,6850 \tkg \t13,690\n"
    "Código do Produto\n100 \t\nCódigo NCM\n08081000 \t\n"
    "Valor unitário de comercialização\n19,9800000000 \t\n"
    "Data/Hora: 10/06/2026 10:27\n"
)


def test_parse_txt():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8", delete=False) as f:
        f.write(SAMPLE)
        tmp = Path(f.name)
    try:
        items = parse_txt(tmp)
        assert len(items) == 2

        pera = items[0]
        assert pera.descricao == "PERA WILLIAMS PREMIUM KG"
        assert pera.codigo_produto == "167"
        assert pera.ncm == "08083000"
        assert pera.quantidade == pytest.approx(0.55)
        assert pera.valor_unitario == pytest.approx(14.98)
        assert pera.valor_total == pytest.approx(8.24)
        assert str(pera.data_emissao) == "2026-06-10"
        assert pera.nfe_chave == "35260635794786000302650040001638751374265845"
    finally:
        tmp.unlink()
