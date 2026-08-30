# ATLAS — Public Safety Analytics Platform

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-produção-FFF000?logo=duckdb&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7?logo=render&logoColor=white)
![Tests](https://img.shields.io/badge/tests-89%2F89%20passing-brightgreen)

Plataforma de engenharia e análise de dados de segurança pública, construída
do zero sobre os dados oficiais do **Sinesp VDE** (Sistema Nacional de
Informações de Segurança Pública — Visualizador de Dados Estatísticos), do
Ministério da Justiça e Segurança Pública.

> Projeto independente de portfólio, com dados públicos oficiais — **não é**
> um produto oficial do Governo Federal. A API se identifica no OpenAPI como
> "Sentinel.io Analytics API"; o repositório e a camada de dados são o ATLAS.

📚 **Documentação completa: [`docs/`](docs/README.md)**

---

## Overview

O ATLAS transforma 3 planilhas Excel (~2 milhões de linhas de estatística
criminal) num modelo analítico consultável por uma API REST — com cada
camada validada antes da próxima começar, e rastreabilidade total da fonte.

## Problem

| Dado bruto do Sinesp | O que o ATLAS entrega |
|---|---|
| 3 planilhas sem modelo, difíceis de cruzar | Esquema estrela: fato (5,29 M linhas) + 8 dimensões |
| Impossível verificar se um agregado está certo | Reconciliação evento a evento: RAW = FACT, 31/31 |
| "Não informado" vira zero e distorce a média | As duas situações são distinguidas; nada é preenchido com zero |
| Somar "vítimas + ocorrências + kg de droga" produz lixo | A API nunca soma unidades diferentes |
| Comparar ano completo com ano parcial engana | YoY sempre no mesmo intervalo de meses |
| Publicar exige hospedar um banco | Um arquivo DuckDB de 17 MB serve a API inteira |

## Solution

```
Sinesp .xlsx → ETL (Python) → PostgreSQL 16 (fonte da verdade) → 31 views SQL
                     │
                     └→ Parquet → builder → atlas_public.duckdb (17 MB) → FastAPI → Render
```

**Desenvolvimento** roda sobre PostgreSQL. **Produção** roda sobre um dataset
DuckDB read-only, derivado automaticamente dos mesmos dados — sem PostgreSQL,
sem servidor de banco, deploy gratuito. Os dois modos são selecionados por
`DATABASE_ENGINE` e produzem resultados **idênticos** (garantido por 25
testes de paridade).

## Architecture

Visão detalhada + diagramas Mermaid: [`docs/02-ARCHITECTURE.md`](docs/02-ARCHITECTURE.md).

```
DESENVOLVIMENTO                          PRODUÇÃO
──────────────────────                  ─────────────────────
data/raw/*.xlsx                         data/production/atlas_public.duckdb
   │ ETL (src/ingestion,                    │  (17 MB, read-only, versionado)
   │      transformation,                   │
   │      validation, loading)              ▼
   ▼                                    FastAPI (DATABASE_ENGINE=duckdb)
PostgreSQL 16 (Docker)  ──────┐             │
   │ src/analytics/build_views │             ▼
   ▼                          │         Render (Web Service Python, free)
schema analytics (31 views)   │             │
   │                          │             ▼
   ├─→ Power BI (Import + DAX) │         consumidores (HTTPS / JSON)
   │                          │
   └─→ data/processed/*.parquet ─→ src.production.build_dataset ─→ atlas_public.duckdb
```

## Features

| Capacidade | Endpoint(s) |
|---|---|
| Catálogo de 31 indicadores + classificação semântica | `/indicators` |
| KPIs por indicador, com filtros combináveis | `/kpis` |
| Série temporal mensal | `/temporal` |
| Comparação ano a ano em período comparável | `/temporal/yoy` |
| Totais por UF e por município (paginado) | `/geography/uf`, `/geography/municipalities` |
| Rankings (UF, município, indicador dentro do grupo) | `/rankings/uf`, `/rankings/municipalities`, `/rankings/indicators` |
| Radar de desvios da média histórica (z-score, sem ML) | `/radar` |
| Metadados e listas de valores para filtros | `/metadata`, `/metadata/{ufs,years,abrangencias,municipalities}` |

17 rotas `GET`, somente leitura, sem autenticação.

## Tech Stack

| Camada | Tecnologias (versões reais) |
|---|---|
| Engenharia de dados | Python 3.11 · pandas ≥ 2.2 · NumPy ≥ 1.26 · openpyxl ≥ 3.1 · pyarrow ≥ 15.0 |
| Banco (dev) | PostgreSQL 16 (`postgres:16-alpine`) · psycopg 3 |
| Banco (produção) | DuckDB ≥ 1.1 · duckdb-engine ≥ 0.13 |
| API | FastAPI ≥ 0.115 · SQLAlchemy ≥ 2.0 · Pydantic ≥ 2.0 · Uvicorn ≥ 0.32 |
| Infra | Docker · Docker Compose |
| Deploy | Render (Web Service Python, plano free) · `render.yaml` · `Procfile` |
| Testes | pytest ≥ 8.0 — 89 testes |
| BI | Power BI (Import Mode + DAX) — especificado |

## Data Pipeline

`python -m src.run_etl` — detalhe em [`docs/04-ETL_PIPELINE.md`](docs/04-ETL_PIPELINE.md).

```
RAW (lê .xlsx, não altera nada)
 → STAGING (tipagem; ASSERT: linhas == RAW)          → 1.996.058 linhas
 → agregação pelo grão real (SUM, nunca dedup)        → ~197 mil combinações
 → dimensões (surrogate keys determinísticas) + fato (unpivot → formato longo)  → 5.291.040 linhas
 → data quality (8 checks) + reconciliação (31/31 PASS)
 → carga PostgreSQL (COPY) + data/processed/*.parquet
```

### Principais achados do projeto

- **O Distrito Federal quebra a granularidade esperada.** O DF não tem
  municípios; a fonte reporta um nível mais granular que colapsa em
  "Brasília" no export. O ETL agrega por `SUM`, nunca remove "duplicatas" —
  senão a criminalidade da capital seria subcontada.
- **"Não aplicável" e "não informado" são coisas diferentes** — e os dados
  provam. Nenhum caso é preenchido com zero; cada um é contado e reportado
  separadamente.
- **Outliers em apreensão de drogas não são erro — são o fenômeno.** Nunca
  removidos; a camada analítica mostra o efeito deles ao lado da média real.
- **Um pico estatisticamente atípico apareceu no radar**, com z-score
  explicável (sem ML): "Morte por intervenção de Agente do Estado" em
  out/2025, 3σ acima da média histórica do indicador — candidato a
  investigação qualitativa, nunca afirmação causal automática.
- **2026 é sempre tratado como ano parcial** (6 de 12 meses), com a flag
  calculada dos dados — nunca hardcoded.

## API

- **Produção**: `https://sentinel-api-sjie.onrender.com` · base
  `/api/v1` · Swagger `/docs`
- **Local**: `uvicorn src.api.main:app --reload --port 8000` →
  <http://localhost:8000/docs>
- Contrato completo: [`docs/06-API_REFERENCE.md`](docs/06-API_REFERENCE.md).

```
Router → Service → Repository → SQL (PostgreSQL | DuckDB) → JSON
```

## Development

```bash
cp .env.example .env
docker compose up -d                 # PostgreSQL (5433) + API (8000)
pip install -r requirements.txt
python -m src.run_etl                 # precisa dos .xlsx em data/raw/
python -m src.analytics.build_views
pytest
```

Guia completo: [`docs/12-CONTRIBUTING.md`](docs/12-CONTRIBUTING.md).

## Production

```bash
python -m src.production.build_dataset          # → data/production/atlas_public.duckdb (17 MB)

DATABASE_ENGINE=duckdb CORS_ORIGINS=http://localhost:3000 \
  uvicorn src.api.main:app --port 8000          # roda sem PostgreSQL
```

Detalhe dos dois modos: [`docs/07-PRODUCTION.md`](docs/07-PRODUCTION.md).

## Testing

```bash
pytest                                  # 89 testes (engine postgres)
DATABASE_ENGINE=duckdb pytest tests/test_api.py     # 31 testes contra DuckDB
pytest tests/test_production_parity.py   # 25 testes de paridade
python -m scripts.bench_engines          # benchmark PostgreSQL × DuckDB
```

| Suíte | Testes |
|---|--:|
| ETL (staging, dimensões, fato, reconciliação) | 18 |
| Camada analítica (SQL) | 15 |
| API (17 endpoints) | 31 |
| Paridade PostgreSQL × DuckDB | 25 |
| **Total** | **89** |

Detalhe: [`docs/09-TESTING.md`](docs/09-TESTING.md).

## Deployment

Web Service Python no Render, plano **free**, servindo o DuckDB versionado —
**sem banco provisionado**. `render.yaml` e `Procfile` na raiz.

```yaml
buildCommand: pip install -r requirements-api.txt
startCommand: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
healthCheckPath: /api/v1/health
env: DATABASE_ENGINE=duckdb · DUCKDB_PATH · CORS_ORIGINS · PYTHON_VERSION=3.11.9
```

Detalhe: [`docs/08-DEPLOYMENT.md`](docs/08-DEPLOYMENT.md).

## Documentation

| # | Documento | # | Documento |
|---|---|---|---|
| 01 | [Visão do produto](docs/01-PRODUCT_OVERVIEW.md) | 08 | [Deploy](docs/08-DEPLOYMENT.md) |
| 02 | [Arquitetura](docs/02-ARCHITECTURE.md) | 09 | [Testes e qualidade](docs/09-TESTING.md) |
| 03 | [Arquitetura de dados](docs/03-DATA_ARCHITECTURE.md) | 10 | [Runbook — atualização de dados](docs/10-DATA_REFRESH.md) |
| 04 | [Pipeline ETL](docs/04-ETL_PIPELINE.md) | 11 | [Variáveis de ambiente](docs/11-ENVIRONMENT_VARIABLES.md) |
| 05 | [Banco de dados](docs/05-DATABASE.md) | 12 | [Contribuição / setup local](docs/12-CONTRIBUTING.md) |
| 06 | [Referência da API](docs/06-API_REFERENCE.md) | 13 | [Troubleshooting](docs/13-TROUBLESHOOTING.md) |
| 07 | [Produção (PostgreSQL × DuckDB)](docs/07-PRODUCTION.md) | | |

Referências técnicas por fase de construção (`DATA_PROFILE`,
`MODEL_VALIDATION`, `METHODOLOGY`, `ANALYTICS_MODEL`, `PRODUCTION_ARCHITECTURE`,
`POWERBI_*`): ver o [índice da documentação](docs/README.md).

## Princípios que atravessam o projeto

1. **Nada é inventado.** Indicador ou UF não mapeado → o pipeline falha
   explicitamente.
2. **Duplicatas se agregam com `SUM`, nunca se descartam.**
3. **Nenhuma métrica mistura unidades incompatíveis** (exceção deliberada:
   `z_score` no `/radar`).
4. **Outliers nunca são removidos.**
5. **Ano parcial é sempre identificado**, nunca comparado a ano completo sem
   normalização.

## Roadmap

- **[ATUAL]** Pipeline ETL, 31 views analíticas, API REST (17 endpoints, 89
  testes), dataset DuckDB de produção, `render.yaml` pronto para deploy
  gratuito.
- **[ATUAL]** Modelo semântico e catálogo de medidas DAX para Power BI
  especificados (`.pbix` não versionado).
- **[PLANEJADO]** Deploy da API em produção no Render; frontend consumidor
  (projeto separado) na Vercel.
- **[FUTURO]** Atualização de dados automatizada (CI); observabilidade/
  monitoramento; cache de resposta; mais anos históricos conforme o Sinesp
  publica; materialização das views de agregação no DuckDB para acelerar os
  endpoints de ponto.

> `[PLANEJADO]` e `[FUTURO]` são intenções, não funcionalidades entregues.

## Fonte dos dados

Sinesp VDE — Ministério da Justiça e Segurança Pública. Nenhum dado externo,
simulado ou de outra fonte, exceto o mapeamento oficial UF → Região (IBGE).
