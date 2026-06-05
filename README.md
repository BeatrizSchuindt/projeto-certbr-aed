# Análise Exploratória de Dados — CERT.br

Pesquisa exploratória sobre incidentes de segurança notificados ao CERT.br
(Centro de Estudos, Resposta e Tratamento de Incidentes de Segurança no Brasil),
no contexto da disciplina de **Segurança de Sistemas de Computação** do curso
de Engenharia da Computação do **IFMT Campus Cuiabá**.

## Fonte dos dados

Os dados são extraídos da API interna do CERT.br em
[`stats.cert.br/data/incidentes`](https://stats.cert.br/data/incidentes/),
sob licença Creative Commons CC BY-NC-ND 4.0. A pasta `dados_certbr/`
**não está versionada** neste repositório — é gerada localmente pelo
script `extrair_api_certbr.py`.

## Estrutura do projeto

```
projeto-certbr/
├── .gitignore
├── README.md
├── extrair_api_certbr.py      # Script de extração dos dados
├── aed_apresentacao.ipynb     # Notebook da análise exploratória
└── dados_certbr/              # Gerado pelo script (ignorado pelo Git)
    ├── raw/                   # Arquivos .txt brutos da API
    └── *.csv                  # CSVs processados (1 por gráfico do site)
```

## Como executar (passo a passo)

### 1. Pré-requisitos

- **Python 3.10 ou superior** instalado
- **Git** instalado
- Aproximadamente **5 minutos** para baixar todos os dados

Verifique as versões:

```bash
python3 --version
git --version
```

### 2. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd projeto-certbr
```

### 3. Criar e ativar o ambiente virtual

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Você deve ver `(.venv)` aparecer no início do prompt do terminal.

### 4. Instalar dependências

```bash
pip install --upgrade pip
pip install requests pandas matplotlib seaborn jupyter ipykernel
```

### 5. Extrair os dados do CERT.br

```bash
python extrair_api_certbr.py
```

O script vai baixar cerca de 80 arquivos da API e gerar 9 CSVs processados
na pasta `dados_certbr/`. Demora 1 a 2 minutos. Saída esperada:

```
[Grupo A] Séries históricas globais
  · incidentes    OK (28 linhas → incidentes_anual.csv)
  · dos           OK (28 linhas → dos_anual.csv)

[Grupo B] Detalhamento por ano
  · 2016: ...
  · 2017: ...
  ...

Concluído. Arquivos em: /caminho/projeto-certbr/dados_certbr
```

### 6. Abrir e rodar o notebook

**No VS Code** (recomendado):

1. Abra a pasta `projeto-certbr` em **File → Open Folder**
2. Instale a extensão **Python** da Microsoft (se ainda não tiver)
3. Abra o arquivo `aed_apresentacao.ipynb`
4. No canto superior direito, clique em **Select Kernel** e escolha o `.venv`
5. Clique em **Run All** no topo do notebook

**No Jupyter clássico:**

```bash
jupyter notebook aed_apresentacao.ipynb
```

## Sobre os datasets gerados

O script gera **9 arquivos CSV**, cada um correspondendo a um gráfico do
portal `stats.cert.br/incidentes/`:

| Arquivo | Conteúdo | Cobertura |
|---|---|---|
| `incidentes_anual.csv` | Total geral por ano | 1999–presente |
| `dos_anual.csv` | Notificações DoS por ano | 1999–presente |
| `tipos_incidente.csv` | Agregado anual por categoria | 2016–presente |
| `tipos_incidente_mensal.csv` | Detalhe mês × categoria | 2016–presente |
| `incidentes_mensal.csv` | Totais mensais | 2016–presente |
| `tipos_fraude_mensal.csv` | Phishing vs Malware | 2016–presente |
| `top_portas.csv` | Top portas atacadas por ano | 2016–presente |
| `top_cc.csv` | Top países de origem por ano | 2016–presente |
| `top_asn.csv` | Top sistemas autônomos por ano | 2016–presente |

## Solução de problemas

**`ModuleNotFoundError` ao rodar o notebook**

Verifique se o kernel selecionado é o do `.venv`. No VS Code, canto superior
direito do notebook, deve estar escrito algo como `Python 3.X.X ('.venv')`.

**`Diretório dados_certbr não encontrado`**

Você esqueceu de rodar o script de extração. Volte ao passo 5.

**Script de extração retorna erro de rede**

Verifique sua conexão com a internet. Se o erro persistir, o CERT.br pode
estar fora do ar momentaneamente — tente novamente em alguns minutos.

**`.venv` não aparece no VS Code**

Abra a pasta `projeto-certbr` como workspace (não a pasta-mãe). No VS Code:
**File → Close Folder** e depois **File → Open Folder** apontando para
`projeto-certbr/`.

## Licença

Os dados utilizados pertencem ao CERT.br/NIC.br sob licença CC BY-NC-ND 4.0.
Este projeto é de uso acadêmico no contexto da disciplina.

## Autores

- IFMT Campus Cuiabá — Engenharia da Computação
- Período letivo: 2026/1
