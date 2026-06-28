# myDANFE — Inflação Pessoal

Sistema pessoal para rastrear o preço das suas compras ao longo do tempo.
Você importa notas fiscais eletrônicas (NFC-e) brasileiras, o sistema guarda
os dados em um banco MariaDB e mostra gráficos comparando a variação dos seus
preços com o IPCA oficial.

---

## Como funciona (visão geral)

```
Nota fiscal (NFC-e)
        │
        ▼
  [Tela de Importação]   ← você cola o texto da nota aqui
        │
        ▼
  Backend (FastAPI)      ← faz o parsing e salva no banco
        │
        ▼
  MariaDB                ← armazena emitentes, notas e itens
        │
        ▼
  [Painel]               ← exibe gráficos e estatísticas
```

A interface roda no navegador (React). O servidor roda em Python (FastAPI).
O banco de dados é o MariaDB.

---

## Pré-requisitos

Você precisa ter instalado na sua máquina (ou VPS):

| Ferramenta | Versão mínima | Para que serve |
|---|---|---|
| Python | 3.11 | Rodar o backend |
| Node.js | 18 | Rodar/compilar o frontend |
| npm | 9 | Gerenciar pacotes do frontend |
| MariaDB | 10.6 | Banco de dados |

---

## Instalação passo a passo

### 1. Clonar o repositório

```bash
git clone https://github.com/SantosFC/myDANFE.git
cd myDANFE
```

---

### 2. Criar o banco de dados no MariaDB

Abra o terminal do MariaDB como root:

```bash
sudo mysql -u root -p
```

Dentro do MariaDB, execute os comandos abaixo (substitua `SUA_SENHA` por uma senha de sua escolha):

```sql
CREATE DATABASE mydanfe CHARACTER SET utf8mb4;
CREATE USER 'mydanfe'@'localhost' IDENTIFIED BY 'SUA_SENHA';
GRANT ALL PRIVILEGES ON mydanfe.* TO 'mydanfe'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

> **O que cada linha faz:**
> - `CREATE DATABASE` — cria o banco chamado `mydanfe`
> - `CREATE USER` — cria um usuário dedicado (não use o root na aplicação)
> - `GRANT ALL PRIVILEGES` — dá permissão total ao usuário apenas neste banco
> - `FLUSH PRIVILEGES` — aplica as permissões imediatamente

As tabelas são criadas automaticamente na primeira vez que o servidor inicia.
Você não precisa rodar nenhum SQL adicional.

---

### 3. Configurar as variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Abra o `.env` em qualquer editor de texto e preencha:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=mydanfe
DB_PASSWORD=SUA_SENHA
DB_NAME=mydanfe
```

> **Por que usar `.env`?**
> Para não colocar senha diretamente no código. O arquivo `.env` é ignorado
> pelo Git (está no `.gitignore`), então a senha nunca vai parar no repositório.

---

### 4. Instalar as dependências do backend (Python)

É boa prática usar um ambiente virtual para isolar as dependências do projeto:

```bash
# Criar o ambiente virtual (só precisa fazer uma vez)
python3 -m venv .venv

# Ativar o ambiente virtual
source .venv/bin/activate   # Linux/Mac
# ou
.venv\Scripts\activate      # Windows

# Instalar as dependências
pip install -r requirements.txt
```

> **O que é um ambiente virtual?**
> É uma pasta isolada com as bibliotecas Python do projeto. Assim você não
> mistura versões de bibliotecas entre projetos diferentes.

---

### 5. Instalar as dependências do frontend (Node.js)

```bash
cd frontend
npm install
cd ..
```

---

### 6. Rodar em modo desenvolvimento

Você vai precisar de **dois terminais abertos ao mesmo tempo**.

**Terminal 1 — Backend:**

```bash
# Certifique-se de estar na raiz do projeto com o ambiente virtual ativo
source .venv/bin/activate
uvicorn backend.main:app --reload
```

Você verá algo como:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Você verá algo como:
```
  VITE ready in 300ms
  ➜  Local:   http://localhost:5173/
```

Abra `http://localhost:5173` no navegador.

> **Como os dois se comunicam?**
> O frontend (porta 5173) envia requisições para `/api/...`, e o Vite
> redireciona automaticamente para o backend (porta 8000). Isso é configurado
> em `frontend/vite.config.js`.

---

## Como importar uma nota fiscal

1. Abra a página de consulta pública da NFC-e pelo QR code do cupom
2. Na tela de importação do myDANFE:
   - **Campo 1 (Aba NFe):** cole o conteúdo da aba "NFe" do portal
   - **Campo 2 (Aba Produtos):** cole o conteúdo da aba "Dados dos Produtos"
3. Clique em **Processar** — o sistema valida os dados e mostra uma prévia
4. Confira os itens e clique em **Salvar**

O sistema detecta automaticamente se a nota já foi importada antes e bloqueia
o botão de salvar para evitar duplicatas.

---

## Estrutura do projeto

```
myDANFE/
├── backend/                  Servidor Python (FastAPI)
│   ├── main.py               Ponto de entrada da API
│   ├── db.py                 Conexão e queries do MariaDB
│   ├── inflation.py          Cálculos de inflação pessoal
│   ├── ipca.py               Série histórica IPCA via API do IBGE
│   ├── parsers/
│   │   ├── xml_parser.py     Leitura de arquivos XML de NFe
│   │   ├── txt_parser.py     Leitura de texto copiado do portal NFC-e
│   │   ├── pdf_parser.py     Leitura de PDF do DANFE NFC-e
│   │   └── nfe_tab_parser.py Leitura da aba NFe (formato tabular)
│   └── routers/
│       ├── notas.py          Endpoints: processar e salvar notas
│       ├── produtos.py       Endpoints: listar e renomear produtos
│       └── painel.py         Endpoints: resumo, gráficos, registros
├── frontend/                 Interface web (React + Vite)
│   ├── src/
│   │   ├── App.jsx           Roteamento e menu de navegação
│   │   ├── api.js            Cliente HTTP (axios)
│   │   └── pages/
│   │       ├── ImportarNota.jsx  Tela de importação de notas
│   │       ├── Painel.jsx        Tela de gráficos e métricas
│   │       └── Produtos.jsx      Tela de edição de descrições
│   └── vite.config.js        Configuração do Vite (proxy para o backend)
├── deploy/
│   ├── mydanfe.service       Serviço systemd (para VPS)
│   └── nginx.conf            Configuração Nginx (para VPS)
├── tests/                    Testes automatizados (pytest)
├── .env.example              Modelo de configuração
├── requirements.txt          Dependências Python
└── .github/workflows/ci.yml  CI: lint, testes e segurança
```

---

## Deploy em produção (VPS Ubuntu 24)

Este processo configura o sistema para rodar automaticamente como um serviço,
sem precisar manter um terminal aberto.

### 1. Compilar o frontend

```bash
cd frontend
npm run build
cd ..
```

Isso gera os arquivos estáticos em `backend/static/`. O Nginx vai servir esses
arquivos diretamente.

### 2. Copiar os arquivos para o servidor

```bash
sudo cp -r . /opt/mydanfe
sudo cp .env /opt/mydanfe/.env
```

### 3. Instalar as dependências Python no servidor

```bash
cd /opt/mydanfe
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configurar o serviço systemd

```bash
sudo cp deploy/mydanfe.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mydanfe
sudo systemctl start mydanfe
```

Para verificar se está rodando:

```bash
sudo systemctl status mydanfe
```

### 5. Configurar o Nginx

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/mydanfe
sudo ln -s /etc/nginx/sites-available/mydanfe /etc/nginx/sites-enabled/
sudo nginx -t          # testa a configuração
sudo systemctl reload nginx
```

> **Como funciona em produção:**
> - O Nginx recebe as requisições na porta 80
> - Requisições para `/api/` são repassadas para o uvicorn (porta 8000)
> - As demais requisições servem os arquivos estáticos do React

---

## Rodando os testes

```bash
# Com o ambiente virtual ativo:
pytest tests/ -v
```

Para ver a cobertura de código:

```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
```

---

## Modelo de dados

O banco usa cinco tabelas:

- **emitente** — estabelecimento comercial (CNPJ, nome, endereço)
- **nota** — cabeçalho da NFC-e (chave de acesso, data, número, série, valor total)
- **item** — cada linha de produto dentro de uma nota
- **produto_canonico** — nome padronizado de produto (para comparar entre lojas)
- **produto_alias** — mapeamento entre a descrição na nota e o produto canônico
