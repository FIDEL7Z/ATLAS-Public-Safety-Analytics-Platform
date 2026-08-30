# 02 — Arquitetura

> Navegação: [Índice](README.md) · ← [Visão do produto](01-PRODUCT_OVERVIEW.md) · Próximo → [Arquitetura de dados](03-DATA_ARCHITECTURE.md)

## Princípio central: dois ambientes, uma fonte da verdade

O ATLAS separa deliberadamente **engenharia de dados** de **serving**:

| | Desenvolvimento / Engenharia | Produção / Serving |
|---|---|---|
| Banco | PostgreSQL 16 (Docker) | DuckDB (arquivo embarcado) |
| Papel | fonte da verdade — ETL, validação, analytics, Power BI | réplica read-only derivada, servida pela API |
| Origem dos dados | planilhas `.xlsx` → ETL | `data/processed/*.parquet` → builder |
| Escrita | sim (carga do ETL) | nunca (`read_only=True`) |
| Como se seleciona | `DATABASE_ENGINE=postgres` (padrão) | `DATABASE_ENGINE=duckdb` |
| Onde roda | máquina do desenvolvedor / CI | Render (ou qualquer host Python) |

O PostgreSQL **nunca sai da máquina de engenharia**. Produção nunca depende
dele. Ver [07 — Produção](07-PRODUCTION.md) para a mecânica dos dois modos.

## Visão geral do ecossistema

```mermaid
flowchart TB
    subgraph DEV["DESENVOLVIMENTO — máquina local (fonte da verdade)"]
        direction TB
        XLSX["data/raw/BancoVDE 2024|2025|2026.xlsx<br/>(Sinesp VDE — não versionado)"]
        ETL["ETL — src/ingestion · transformation · validation · loading"]
        PARQUET["data/processed/*.parquet<br/>staging · 8 dimensões · fato"]
        PG[("PostgreSQL 16 — Docker (atlas_postgres)<br/>stg_sinesp · fact_indicadores (5.291.040) · 8 dims<br/>schema analytics: 31 views · ~1,23 GB")]
        DQ["Data Quality + Reconciliação<br/>data/quality_reports/*.md · docs/ETL_RECONCILIATION.md"]

        XLSX --> ETL
        ETL --> PARQUET
        ETL --> PG
        ETL --> DQ
        PG --> VIEWS["src/analytics/build_views.py<br/>aplica sql/analytics/*.sql"]
    end

    subgraph BUILD["BUILD DO DATASET DE PRODUÇÃO"]
        BUILDER["python -m src.production.build_dataset<br/>src/production/ · 17 checks de validação"]
        DUCK[("data/production/atlas_public.duckdb<br/>17,05 MB · read-only · versionado no Git<br/>10 tabelas · 26 views + 1 tabela materializada")]
        MANIFEST["manifest.json — proveniência da build"]
        PARQUET --> BUILDER
        BUILDER --> DUCK
        BUILDER --> MANIFEST
    end

    subgraph PROD["PRODUÇÃO — serving"]
        API["FastAPI (uvicorn) — src/api/<br/>Router → Service → Repository<br/>DATABASE_ENGINE=duckdb · QueuePool read-only<br/>17 endpoints GET · /docs · /redoc · /openapi.json"]
        RENDER["Render — Web Service Python (free)<br/>render.yaml · Procfile"]
        DUCK --> API --> RENDER
    end

    subgraph OTHER["OUTRAS SAÍDAS"]
        PBI["Power BI — Import Mode + DAX<br/>conecta direto no PostgreSQL"]
        PG --> PBI
    end

    RENDER -->|"HTTPS / JSON · CORS restrito"| CONSUMERS["Consumidores da API"]
```

## Arquitetura de desenvolvimento

```mermaid
flowchart LR
    A["RAW<br/>load_raw.py — lê os .xlsx sem alterar nada"]
    B["STAGING<br/>staging.py — normaliza tipos, preserva 100% das linhas"]
    C["Agregação pelo grão real<br/>fact.py — SUM, nunca dedup"]
    D["Dimensões + Fato (formato longo)<br/>dimensions.py · fact.py — unpivot das medidas"]
    E["Data Quality (8 checks) + Reconciliação (31 eventos)"]
    F["Carga PostgreSQL<br/>postgres_loader.py — COPY via psycopg"]
    G["Camada analítica<br/>build_views.py — 31 views SQL"]
    A --> B --> C --> D --> E --> F --> G
    D -. também grava .-> P["data/processed/*.parquet"]
```

Orquestrado por `python -m src.run_etl`. Detalhe em
[04 — Pipeline ETL](04-ETL_PIPELINE.md).

## Arquitetura de produção

```mermaid
flowchart LR
    P["data/processed/*.parquet<br/>(output validado do ETL)"]
    B["src.production.build_dataset<br/>· carrega fato + 8 dims (valor → DECIMAL(14,3))<br/>· aplica sql/analytics/002,003,004,006 verbatim<br/>· materializa vw_qualidade_resumo (sem staging)<br/>· 17 checks · escreve manifest.json"]
    D[("atlas_public.duckdb — 17 MB")]
    G["Git (arquivo versionado)"]
    R["Render — pip install -r requirements-api.txt<br/>uvicorn src.api.main:app --host 0.0.0.0 --port $PORT"]
    P --> B --> D --> G --> R
```

## Arquitetura da API

```mermaid
flowchart TB
    REQ["GET /api/v1/..."] --> ROUTER
    subgraph APP["src/api/"]
        ROUTER["routers/*.py<br/>valida query params (Pydantic / FastAPI Query)"]
        SERVICE["services/*.py<br/>regras de negócio: 404, grupo_semântico válido,<br/>defaults de YoY, checagem de indicador"]
        REPO["repositories/*.py<br/>SQL parametrizado (text() + bind params)"]
        SCHEMA["schemas/*.py<br/>modelos Pydantic de resposta"]
        DBMOD["database.py<br/>engine: postgres (pool) | duckdb (QueuePool RO)"]
    end
    ROUTER --> SERVICE --> REPO --> DBMOD
    DBMOD --> DB[("PostgreSQL  ou  atlas_public.duckdb")]
    SERVICE --> SCHEMA
    SCHEMA --> RESP["JSON"]
```

- **Router**: uma função por endpoint; validação de tipo/formato dos
  parâmetros é declarativa (FastAPI + Pydantic → 422 automático).
- **Service**: regras que não são SQL — 404 quando o indicador não existe,
  validação de `grupo_semantico`, defaults de `base_year`/`comparison_year`,
  cálculo da variação percentual.
- **Repository**: só SQL. Todo valor vindo do cliente é *bind parameter* —
  nunca concatenação de string. Alguns endpoints leem views prontas da
  camada analítica; outros (`/kpis`, `/temporal`, `/geography/*`) agregam
  `fact_indicadores` diretamente porque precisam de combinações de filtro
  que nenhuma view fixa cobre.
- **Schema**: contrato de saída. O que não está no schema não sai na
  resposta.

## Decisões arquiteturais

### Por que PostgreSQL no ambiente de engenharia

- Transações e `FOREIGN KEY` reais durante a carga (`fact_indicadores`
  referencia 8 dimensões).
- `UNIQUE INDEX ux_fact_grain` garante, no nível do banco, que o grão real
  validado nunca é violado por uma carga duplicada.
- `EXPLAIN ANALYZE`, `pg_stat_*`, `pg_depend` — ferramental maduro para
  auditar a camada analítica.
- Conecta com Power BI (Import Mode) sem intermediários.
- É o padrão que um time de dados espera encontrar.

### Por que DuckDB em produção

- **Tamanho**: a `fact_indicadores` ocupa ~969 MB no PostgreSQL (385 MB de
  dados + 586 MB de índices). Em DuckDB, colunar e comprimida, o dataset
  inteiro (fato + dimensões + views) são **17 MB**. O problema de tamanho
  desaparece.
- **Sem servidor**: DuckDB é embarcado no processo da API. Não há banco para
  hospedar, logo não há tier gratuito de banco para estourar. O deploy é uma
  unidade só (código + arquivo).
- **Performance de leitura**: nos endpoints que agregam a fato inteira
  (`/kpis`, `/rankings/*`, `/radar`), DuckDB foi 10–39× mais rápido que o
  PostgreSQL no mesmo hardware (benchmark real — ver [09 — Testes](09-TESTING.md)).
- **Dialeto compatível**: DuckDB fala um SQL quase idêntico ao PostgreSQL.
  Das 7 folhas de SQL analítico, 4 são aplicadas **sem nenhuma alteração**;
  o ajuste no código dos repositories foi trocar `CAST(:x AS CHAR(2))` por
  `CAST(:x AS VARCHAR)` (equivalente nos dois bancos).

### Qual problema essa arquitetura resolve

Publicar um produto de dados de portfólio **de graça, sem cartão de
crédito**, sem abrir mão do rigor de engenharia. O warehouse pesado fica
onde ele deve ficar (na engenharia); o que vai para a internet é um
artefato pequeno, imutável e reproduzível.

### Vantagens

- Custo de produção: R$ 0.
- Deploy trivial (um `git push`).
- Resultados idênticos aos do PostgreSQL — garantido por 25 testes de
  paridade que rodam a mesma query nos dois engines.
- Atualização de dados versionada: o `.duckdb` entra no histórico do Git
  junto com o código que o produz.

### Limitações

- **Atualização = redeploy.** Não há escrita em produção; dado novo exige
  rodar o ETL, reconstruir o `.duckdb` e fazer push. Adequado para dados
  mensais (a cadência do Sinesp), não para tempo real.
- **Concorrência.** Um processo, arquivo read-only. Ótimo para tráfego
  baixo/médio; escala horizontal é trivial (cada instância tem sua cópia),
  mas não há um banco central compartilhado.
- **Primeira query fria.** O processo parseia as 26 views na primeira
  consulta (~0,4 s); as seguintes são rápidas.
- **Free tier hiberna.** No plano gratuito do Render, o serviço dorme após
  ~15 min sem tráfego (cold start ~50 s).

## Fluxo de atualização dos dados

```mermaid
flowchart LR
    A["Novo BancoVDE 20XX.xlsx"] --> B["registrar em src/config.py (RAW_FILES)"]
    B --> C["python -m src.run_etl"]
    C --> D["python -m src.analytics.build_views"]
    D --> E["pytest  (89 testes, PostgreSQL)"]
    E --> F["python -m src.production.build_dataset"]
    F --> G["pytest tests/test_production_parity.py  (25 testes)"]
    G --> H["git commit do atlas_public.duckdb + manifest.json"]
    H --> I["git push → Render redeploy automático"]
    I --> J["validar /api/v1/health e /docs"]
```

Runbook detalhado: [10 — Atualização de dados](10-DATA_REFRESH.md).
