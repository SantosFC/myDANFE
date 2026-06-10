Parse two text blocks pasted by the user (NFe tab + Produtos tab from the Sefaz-SP NFC-e portal) and display a formatted table.

## Instructions

The user will paste two text blocks from the Sefaz-SP NFC-e consultation page:
1. The **NFe tab** (contains emitter data, note header, date, value)
2. The **Produtos/Serviços tab** (contains item list)

Both blocks are pasted together in the user's message. Identify them by their content:
- NFe tab contains: "Emitente", "CNPJ", "Nome / Razão Social", "Valor Total da Nota Fiscal"
- Produtos tab contains: "Dados dos Produtos e Serviços", "Código do Produto", "Valor unitário de comercialização"

## Steps

1. Split the user input into the two blocks (NFe and Produtos)
2. Run this Python code to parse them:

```python
import sys, tempfile, pathlib
sys.path.insert(0, '.')
from src.nfe_tab_parser import parse_nfe_tab
from src.txt_parser import parse_txt

# parse NFe tab
cabecalho = parse_nfe_tab(nfe_text)

# parse Produtos tab
with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', encoding='utf-8', delete=False) as f:
    f.write(prod_text)
    tmp = pathlib.Path(f.name)
itens = parse_txt(tmp)
tmp.unlink()
```

3. Display the results as a markdown table with columns:
   - **#** (item number)
   - **Descrição**
   - **Qtd**
   - **Un**
   - **Vl. Unit.**
   - **Vl. Total**
   - **EAN** (show "—" if empty)
   - **NCM**

4. Show a summary header before the table:
   - Emitente: nome (CNPJ)
   - Data: data_emissao
   - Nota: série / número
   - Total: valor_total

5. Show the grand total at the bottom of the table.

6. If parsing fails, show the error clearly and ask the user to check which tab they copied.
