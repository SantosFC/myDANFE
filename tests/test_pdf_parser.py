"""Testes do parser de DANFE NFC-e em PDF (via regex sobre o texto extraído)."""

import pytest

from src.pdf_parser import RE_ITEM_RESUMO as RE_ITEM, RE_CHAVE_RESUMO as RE_CHAVE, RE_EMISSAO_RESUMO as RE_EMISSAO, _num

SAMPLE_TEXT = """NH10 Comercio de Alimentos Ltda
CNPJ: 35.794.786/0003-02
Rua Euclides Da Cunha , 214 , , POMPEIA , Santos , SP
PERA WILLIAMS PREMIUM KG (Código: 167 )
Qtde.:0,55UN: kgVl. Unit.:   14,98
Vl. Total
8,24
MACA GALA KG (Código: 100 )
Qtde.:0,685UN: kgVl. Unit.:   19,98
Vl. Total
13,69
Número: 163875 Série: 4 Emissão: 10/06/2026 08:29:16 - Via Consumidor
Chave de acesso:
3526 0635 7947 8600 0302 6500 4000 1638 7513 7426 5845
"""


def test_itens():
    matches = list(RE_ITEM.finditer(SAMPLE_TEXT))
    assert len(matches) == 2
    pera = matches[0]
    assert pera.group("desc").strip() == "PERA WILLIAMS PREMIUM KG"
    assert pera.group("cod") == "167"
    assert _num(pera.group("qtd")) == pytest.approx(0.55)
    assert _num(pera.group("vunit")) == pytest.approx(14.98)
    assert _num(pera.group("vtotal")) == pytest.approx(8.24)


def test_chave_e_emissao():
    chave = RE_CHAVE.search(SAMPLE_TEXT)
    assert chave is not None
    assert "".join(chave.group(1).split()) == "35260635794786000302650040001638751374265845"
    assert RE_EMISSAO.search(SAMPLE_TEXT).group(1) == "10/06/2026"


def test_num_formato_brasileiro():
    assert _num("1.234,56") == pytest.approx(1234.56)
    assert _num("0,685") == pytest.approx(0.685)
