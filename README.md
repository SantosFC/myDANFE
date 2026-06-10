# myDANFE — Inflação Pessoal

Calcula sua inflação pessoal a partir de XMLs de Nota Fiscal Eletrônica (NFe/DANFE) e compara com o IPCA oficial.

## Estrutura

```
myDANFE/
├── data/
│   ├── xmls/        ← coloque seus XMLs aqui
│   └── db/          ← banco SQLite gerado automaticamente
├── src/
│   ├── parser.py    ← leitura de XMLs de NFe
│   ├── db.py        ← persistência SQLite
│   ├── inflation.py ← cálculos de inflação pessoal
│   ├── ipca.py      ← série IPCA via API IBGE
│   └── dashboard.py ← painel Streamlit
├── ingest.py        ← importação via CLI
└── tests/
```

## Instalação

```bash
pip install -r requirements.txt
```

## Uso

### 1. Importar XMLs

Coloque os XMLs de NFe na pasta `data/xmls/` e execute:

```bash
python ingest.py
```

### 2. Abrir o painel

```bash
streamlit run src/dashboard.py
```

O painel exibe:
- Variação mensal da sua cesta vs IPCA oficial
- Top 15 produtos por gasto
- Evolução de preço de qualquer produto ao longo do tempo
- Tabela completa de compras

## Como obter seus XMLs de NFe

- **App Meu Imposto de Renda** (Receita Federal): permite baixar XMLs de NFe vinculados ao seu CPF
- **QR Code da nota**: aponte a câmera e baixe o XML no portal estadual
- **Consumidor.gov.br** / portais de notas fiscais de cada estado