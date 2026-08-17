# ATLAS
### Public Safety Analytics Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-DAX-F2C811?logo=powerbi&logoColor=black)
![Tests](https://img.shields.io/badge/tests-33%2F33%20passing-brightgreen)

Plataforma de Business Intelligence para análise dos indicadores de segurança pública no Brasil, construída do zero sobre os dados oficiais do **Sinesp VDE** (Sistema Nacional de Informações de Segurança Pública — Visualizador de Dados Estatísticos), do Ministério da Justiça e Segurança Pública.

> O ATLAS **não é** um produto oficial do Governo Federal. É um projeto independente de portfólio, construído com dados públicos oficiais, para demonstrar um pipeline analítico completo — de dados brutos em Excel a um dashboard de BI — com o rigor técnico esperado de uma posição de Analista de Dados / BI pleno.

---

## O que este projeto demonstra

Não é um dashboard em cima de uma planilha. É um pipeline de ponta a ponta, com cada camada validada antes da próxima começar:

```
DADOS  →  DATA ENGINEERING  →  DATA QUALITY  →  DATA WAREHOUSE  →
SQL ANALYTICS  →  BUSINESS INTELLIGENCE  →  DATA VISUALIZATION  →  INSIGHTS
```

| Camada | Tecnologia | Status |
|---|---|---|
| Ingestão + ETL | Python / Pandas | ✅ 1.996.058 linhas processadas, 31/31 indicadores reconciliados |
| Data Warehouse | PostgreSQL (Docker) | ✅ fact table em formato longo, 5.291.040 linhas, 8 dimensões |
| Camada Analítica | SQL (views) | ✅ 25 views analíticas, 13/13 testes de integração |
| Business Intelligence | Power BI / DAX | 📐 modelo semântico e 43 medidas DAX especificados — construção final pendente (ver [Status](#status-e-próximos-passos)) |

## Arquitetura

```
data/raw/*.xlsx (Sinesp VDE, 3 arquivos: 2024, 2025, 2026)
        │
        ▼   ingestão (pandas + openpyxl)
   RAW — carregado em memória, arquivos originais nunca alterados
        │
        ▼   staging (tipagem, normalização — nenhuma linha removida)
   STAGING — stg_sinesp
        │
        ▼   agregação pelo grão real validado (SUM — nunca DROP DUPLICATES)
        ▼   unpivot para formato longo (feminino/masculino/... → valor)
   FACT — fact_indicadores + 8 dimensões
        │
        ▼   COPY (psycopg2)
   PostgreSQL 16 (Docker)
        │
        ▼   sql/analytics/*.sql
   Camada Analítica — schema `analytics`, 25 views
        │
        ▼   Import Mode + DAX
   Power BI — ATLAS Dashboard (6 páginas)
```

## Principais achados do projeto

Alguns resultados que só apareceram por validar cada etapa com os dados reais, em vez de assumir que a modelagem óbvia estava certa:

- **O Distrito Federal quebra a granularidade esperada.** Municípios brasileiros normalmente definem o grão geográfico, mas o DF não tem municípios — a fonte reporta um nível mais granular (provavelmente por Região Administrativa) que colapsa em "Brasília" no export. O ETL trata isso agregando por `SUM`, nunca removendo "duplicatas" — do contrário, a criminalidade da capital federal seria subcontada em até 33-66×.
- **"Não aplicável" e "não informado" são coisas diferentes**, e os dados provam isso: mesmo dentro da família de medida certa, 0% a 51% dos valores (dependendo do indicador) simplesmente não foram reportados pela fonte. Nenhum desses casos foi preenchido com zero — cada um é contabilizado e reportado separadamente.
- **Outliers em apreensão de drogas não são erro — são o fenômeno.** O 1% mais extremo de apreensões de maconha infla a média em até 28%. Os valores nunca são removidos da base; a plataforma mostra o efeito deles lado a lado com a média real.
- **Um evento estatisticamente atípico apareceu no radar analítico**, com z-score explicável (sem Machine Learning): `Morte por intervenção de Agente do Estado` teve um pico em outubro/2025 (3 desvios-padrão acima da média histórica do indicador) — candidato a investigação qualitativa, nunca uma afirmação causal automática.
- **2026 é sempre tratado como ano parcial** (6 de 12 meses), com a flag calculada dinamicamente a partir dos dados — nunca hardcoded — e toda comparação ano-a-ano usa períodos equivalentes (Jan-Jun vs. Jan-Jun), nunca ano completo contra ano parcial.

## Stack

Python · Pandas · NumPy · PostgreSQL · SQL · Power BI · DAX · Docker · pytest · Git

## Estrutura do repositório

```
atlas-public-safety-analytics/
├── data/
│   ├── raw/                  # XLSX originais (não versionado — ver .gitignore)
│   ├── processed/            # parquet intermediário do ETL (não versionado)
│   └── quality_reports/      # relatórios de qualidade + log de execução
├── src/
│   ├── ingestion/            # leitura dos XLSX (camada RAW)
│   ├── transformation/       # staging, dimensões, fact table
│   ├── validation/           # data quality + reconciliação
│   ├── loading/               # carga no PostgreSQL (COPY)
│   └── analytics/            # aplicação das views SQL analíticas
├── sql/
│   ├── staging/               # DDL da staging
│   ├── dimensions/            # DDL das dimensões
│   ├── facts/                 # DDL da fact table
│   └── analytics/             # as 25 views analíticas (Fases 2 e 3)
├── powerbi/
│   ├── atlas_theme.json       # tema visual, pronto para importar
│   └── measures.dax           # catálogo de 43 medidas DAX
├── docs/                      # documentação completa — ver índice abaixo
├── tests/                     # 33 testes automatizados (pytest)
├── docker-compose.yml
└── requirements.txt
```

## Como rodar

Pré-requisitos: Python 3.11+, Docker Desktop.

```bash
# 1. Subir o PostgreSQL
cp .env.example .env
docker compose up -d

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar o ETL completo (RAW → STAGING → FACT → PostgreSQL)
python -m src.run_etl

# 4. Aplicar a camada analítica (views SQL)
python -m src.analytics.build_views

# 5. Rodar os testes
pytest
```

O ETL espera os 3 arquivos `BancoVDE <ano>.xlsx` do Sinesp VDE em `data/raw/` (não incluídos no repositório por serem dados de origem externa e volumosos).

## Documentação

Cada fase foi documentada e validada antes da seguinte começar — a ordem abaixo é a ordem em que o projeto foi construído.

| Documento | Conteúdo |
|---|---|
| [`docs/DATA_PROFILE.md`](docs/DATA_PROFILE.md) | Perfil bruto dos 3 arquivos-fonte (Fase 0) |
| [`docs/MODEL_VALIDATION.md`](docs/MODEL_VALIDATION.md) | Validação do grão real e da arquitetura de modelagem antes do ETL (Fase 0.5) |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Como cada camada do ETL transforma os dados (Fase 1) |
| [`docs/ETL_RECONCILIATION.md`](docs/ETL_RECONCILIATION.md) | RAW vs. STAGING vs. FACT, indicador a indicador — 31/31 PASS |
| [`docs/ANALYTICS_MODEL.md`](docs/ANALYTICS_MODEL.md) | Auditoria do modelo, catálogo de views, métricas, performance (Fase 2) |
| [`docs/POWERBI_MODEL.md`](docs/POWERBI_MODEL.md) | Modelo semântico, conexão, relacionamentos (Fase 3) |
| [`docs/POWERBI_DAX_MEASURES.md`](docs/POWERBI_DAX_MEASURES.md) | Catálogo de medidas DAX explicado |
| [`docs/POWERBI_PAGES.md`](docs/POWERBI_PAGES.md) | Especificação das 6 páginas do dashboard |
| [`docs/POWERBI_DESIGN_SYSTEM.md`](docs/POWERBI_DESIGN_SYSTEM.md) | Identidade visual e paleta de cores |
| [`docs/POWERBI_BUILD_GUIDE.md`](docs/POWERBI_BUILD_GUIDE.md) | Passo a passo para montar o `.pbix` |
| [`docs/POWERBI_VALIDATION.md`](docs/POWERBI_VALIDATION.md) | Tabela de validação PostgreSQL vs. Power BI |
| [`docs/POWERBI_REFRESH_GUIDE.md`](docs/POWERBI_REFRESH_GUIDE.md) | Como atualizar o dashboard com novos dados |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Visão consolidada de toda a arquitetura |

## Princípios que atravessam todo o projeto

1. **Nada é inventado.** Toda classificação de indicador vem da observação real dos dados; um indicador não mapeado faz o pipeline falhar explicitamente em vez de seguir com uma suposição.
2. **Duplicatas se agregam, nunca se descartam.** `SUM` pelo grão real validado, sempre.
3. **Nenhuma métrica mistura unidades incompatíveis.** Vítimas (pessoas), ocorrências, apreensões (kg ou unidades) nunca são somadas entre si sem um filtro explícito de família.
4. **Outliers nunca são removidos** — a plataforma mostra o efeito deles, não os esconde.
5. **Ano parcial é sempre identificado como tal**, e nunca comparado a um ano completo sem normalização de período.

## Status e próximos passos

O pipeline de dados (Fases 1 e 2) está completo, testado e rodando: PostgreSQL carregado, camada analítica validada, 33 testes automatizados passando. A Fase 3 entregou o modelo semântico, o catálogo de medidas DAX e a especificação completa das páginas — a montagem final do arquivo `.pbix` no Power BI Desktop é o próximo passo, seguindo [`docs/POWERBI_BUILD_GUIDE.md`](docs/POWERBI_BUILD_GUIDE.md).

## Fonte dos dados

Sinesp VDE — Ministério da Justiça e Segurança Pública. Nenhum dado externo, simulado ou de outra fonte foi utilizado.
