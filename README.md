# myDANFE — Inflação Pessoal

Sistema pessoal de rastreamento de preços que importa notas fiscais eletrônicas brasileiras (NFC-e) em formatos XML, PDF e TXT, armazena os dados em MariaDB e calcula a inflação da sua cesta de compras ao longo do tempo, comparando com o IPCA oficial.

## Como funciona

- Importe o CSV do portal da Sefaz (ou obtenha os XMLs pelo app Meu Imposto de Renda) para identificar as notas pendentes.
- Para cada nota: abra o QR code do cupom no navegador, copie as abas "Emitente" e "Produtos" e salve como TXT (ou baixe o XML, ou salve como PDF).
- Execute `python ingest.py` (ou clique em "Processar notas agora" no painel): o sistema salva os dados no MariaDB, vincula automaticamente os produtos que possuem EAN e sugere vínculos para os demais com base em similaridade de descrição.
- Confirme os produtos não vinculados pelo painel — a partir daí o histórico de preços fica consistente entre notas de diferentes estabelecimentos.
- O painel exibe a variação mensal da sua cesta vs IPCA, evolução de preço por produto e ranking de gasto.

## Modelo de dados

O banco usa cinco tabelas normalizadas:

- **emitente** — cadastro do estabelecimento (CNPJ, nome, endereço). Chave primária: `cnpj`.
- **nota** — cabeçalho da NFC-e (chave de acesso, data de emissão, número, série, valor total). Referencia `emitente`.
- **produto_canonico** — entidade canônica de produto (nome padronizado, NCM, unidade, EAN). Permite comparar o mesmo produto comprado em lojas diferentes.
- **produto_alias** — mapeamento entre a descrição/código que aparece em cada nota e o produto canônico correspondente. Armazena o `cnpj_emitente` para distinguir lojas que usam o mesmo código para produtos diferentes.
- **item** — linha de produto dentro de uma nota (quantidade, valor unitário, valor total). Referencia `nota` e, quando vinculado, `produto_canonico`.

## Configuração

### MariaDB

```sql
CREATE DATABASE mydanfe CHARACTER SET utf8mb4;
CREATE USER 'danfe'@'%' IDENTIFIED BY 'sua-senha';
GRANT ALL PRIVILEGES ON mydanfe.* TO 'danfe'@'%';
FLUSH PRIVILEGES;
```

Prefira restringir o usuário ao IP da sua máquina (`'danfe'@'seu.ip'`) ou usar túnel SSH em vez de expor a porta 3306.

### Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```
DANFE_DB_HOST=localhost
DANFE_DB_PORT=3306
DANFE_DB_USER=danfe
DANFE_DB_PASSWORD=sua-senha
DANFE_DB_NAME=mydanfe
```

As tabelas são criadas automaticamente na primeira execução.

## Formatos de entrada suportados

- **XML** — arquivo XML de NFe/NFC-e padrão SEFAZ (namespace `http://www.portalfiscal.inf.br/nfe`). Coloque em `data/xmls/`.
- **PDF** — DANFE NFC-e salvo como PDF a partir da página de consulta pública da Sefaz-SP (Ctrl+P → Salvar como PDF). Dois layouts suportados: resumido e completo. Coloque em `data/pdfs/`.
- **TXT** — texto copiado da aba "Consulta Completa" do portal NFC-e (formato tabular com cabeçalho de chave de acesso). Coloque em `data/txts/`.

## Estrutura do projeto

```
myDANFE/
├── data/
│   ├── xmls/           XMLs de NFe/NFC-e
│   ├── pdfs/           PDFs de DANFE NFC-e
│   └── txts/           Textos copiados do portal
├── src/
│   ├── parser.py       Leitura de XMLs de NFe
│   ├── pdf_parser.py   Leitura de PDFs de DANFE NFC-e
│   ├── txt_parser.py   Leitura de TXTs copiados do portal
│   ├── db.py           Persistência MariaDB (esquema normalizado)
│   ├── linker.py       Vinculação de itens a produto_canonico
│   ├── inflation.py    Cálculos de inflação pessoal
│   ├── ipca.py         Série IPCA via API IBGE
│   └── dashboard.py    Painel Streamlit
├── ingest.py           Importação via CLI
├── .env.example        Modelo de configuração
└── tests/
```

## Como usar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco
cp .env.example .env
# edite .env com host, usuário e senha do MariaDB

# 3. Importar notas (XMLs, PDFs e TXTs)
python ingest.py

# 4. Abrir o painel
streamlit run src/dashboard.py
```
