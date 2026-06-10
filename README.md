# myDANFE — Inflação Pessoal

Calcula sua inflação pessoal a partir de XMLs de Nota Fiscal Eletrônica (NFe/DANFE) e compara com o IPCA oficial.

## Estrutura

```
myDANFE/
├── data/
│   └── xmls/        ← coloque seus XMLs aqui
├── src/
│   ├── parser.py    ← leitura de XMLs de NFe
│   ├── db.py        ← persistência MariaDB
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

## Configuração do banco (MariaDB)

No seu VPS, crie o banco e o usuário:

```sql
CREATE DATABASE mydanfe CHARACTER SET utf8mb4;
CREATE USER 'danfe'@'%' IDENTIFIED BY 'sua-senha';
GRANT ALL PRIVILEGES ON mydanfe.* TO 'danfe'@'%';
FLUSH PRIVILEGES;
```

Depois copie `.env.example` para `.env` e preencha host, usuário e senha.
A tabela é criada automaticamente na primeira execução.

> **Dica de segurança**: prefira restringir o usuário ao IP da sua máquina
> (`'danfe'@'seu.ip'`) ou usar um túnel SSH em vez de expor a porta 3306.

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