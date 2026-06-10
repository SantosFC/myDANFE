"""Testes unitários do parser de NFe."""

import textwrap
from pathlib import Path
import tempfile
import pytest

from src.parser import parse_xml

SAMPLE_XML = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe35240112345678000195550010000000011000000010">
      <ide>
        <dhEmi>2024-03-15T10:00:00-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>12345678000195</CNPJ>
        <xNome>SUPERMERCADO TESTE LTDA</xNome>
      </emit>
      <det nItem="1">
        <prod>
          <cProd>001</cProd>
          <xProd>ARROZ BRANCO 5KG</xProd>
          <NCM>10063021</NCM>
          <uCom>PCT</uCom>
          <qCom>2.0000</qCom>
          <vUnCom>18.9900</vUnCom>
          <vProd>37.98</vProd>
        </prod>
      </det>
      <det nItem="2">
        <prod>
          <cProd>002</cProd>
          <xProd>FEIJAO CARIOCA 1KG</xProd>
          <NCM>07133390</NCM>
          <uCom>PCT</uCom>
          <qCom>3.0000</qCom>
          <vUnCom>7.4900</vUnCom>
          <vProd>22.47</vProd>
        </prod>
      </det>
    </infNFe>
  </NFe>
</nfeProc>
""")


def test_parse_xml_basic():
    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
        f.write(SAMPLE_XML)
        tmp = Path(f.name)
    try:
        items = parse_xml(tmp)
        assert len(items) == 2
        arroz = items[0]
        assert arroz.descricao == "ARROZ BRANCO 5KG"
        assert arroz.quantidade == 2.0
        assert arroz.valor_unitario == pytest.approx(18.99)
        assert arroz.data_emissao.year == 2024
        assert arroz.nome_emitente == "SUPERMERCADO TESTE LTDA"
    finally:
        tmp.unlink()
