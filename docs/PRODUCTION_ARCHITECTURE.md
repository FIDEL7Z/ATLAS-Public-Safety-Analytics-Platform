# Arquitetura de Produção — Sentinel Public Data Mode (Fase 6)

Separação explícita entre a **plataforma de dados** (ATLAS) e o **produto de
dados** (Sentinel.io). O PostgreSQL continua sendo a fonte de verdade; a API
pública passa a servir a partir de um arquivo DuckDB read-only, portátil.

```
                    ATLAS DEVELOPMENT  (local — fonte da verdade)
  BancoVDE *.xlsx
        │  python -m src.run_etl        (ETL + Data Quality + reconciliação)
        ▼
  PostgreSQL 16  ─────────  RAW · STAGING · FACT (5,29M) · 8 dims · analytics (31 views)
        │  python -m src.analytics.build_views
        ▼
  data/processed/*.parquet              (output validado do ETL — ~3,3 MB)
        │
        │  python -m src.production.build_dataset      ◄── passo novo da Fase 6
        ▼
  data/production/atlas_public.duckdb   (~17 MB · read-only · manifest.json ao lado)

════════════════════════════════════════════════════════════════════════════════

                    SENTINEL PRODUCTION  (deploy — read-only)
  atlas_public.duckdb
        │  DATABASE_ENGINE=duckdb
        ▼
  FastAPI (uvicorn)   Router → Service → Repository → DuckDB   — só GET
        │  HTTPS / JSON  (contrato dos 16 endpoints inalterado)
        ▼
  Sentinel.io Web (Next.js) → Vercel → usuários
```

## 1. ATLAS Development

Ambiente de engenharia de dados, **inalterado** pela Fase 6. Roda em Docker
(`atlas_postgres`, `atlas_api`). É onde os dados são processados, validados e
versionados analiticamente. Continua usando `requirements.txt` (pandas, numpy,
psycopg, etc.) e `DATABASE_ENGINE=postgres` (o padrão).

## 2. Sentinel Production

O que vai para produção é **um arquivo** (`atlas_public.duckdb`) + a FastAPI.
Sem servidor de banco, sem `pg_dump`/`pg_restore`, sem limite de free tier de
PostgreSQL. Runtime mínimo: `requirements-api.txt` (fastapi, uvicorn,
sqlalchemy, pydantic, duckdb, duckdb-engine).

## 3. PostgreSQL como source of truth

O DuckDB **nunca** é editado à mão e **nunca** recebe carga direta. Ele é
100% derivado de `data/processed/*.parquet`, que por sua vez é o output do
ETL que também alimenta o PostgreSQL. Qualquer correção de dado acontece no
ETL → Postgres → parquet → rebuild. O Postgres permanece disponível para
Power BI, exploração ad-hoc e para a suíte de paridade.

## 4. DuckDB como serving database

- **Somente leitura.** A conexão abre com `read_only=True`. Nenhum endpoint
  de escrita existe (`test_only_get_methods_exposed_read_only_api` garante).
- **Grão completo.** `fact_indicadores` mantém as 5.291.040 linhas — nada é
  agregado ou removido. Isso preserva `COUNT(*)` (ex.: `n_registros` do
  `/kpis`) idêntico ao Postgres.
- **`valor`** é convertido de `DOUBLE` (parquet) para `DECIMAL(14,3)` na
  carga — espelha o `NUMERIC(14,3)` do Postgres e garante que `SUM` não
  acumule erro de ponto flutuante.
- **Staging fora.** `stg_sinesp` (213 MB) não entra. `vw_qualidade_resumo` é
  materializada como tabela de 1 linha, calculada pela SQL **real** da view
  007 numa conexão em memória com a staging (que nunca toca o arquivo final).
- **Views verbatim.** Os arquivos `sql/analytics/002,003,004,006.sql` são
  aplicados sem alteração. `001` e `005` são omitidos: a única view deles que
  poderia importar (`vw_fato_enriquecido`) referencia `f.fact_id`, coluna
  surrogate que não é portada, e nenhum endpoint a usa.

## 5. Production Dataset Builder

```
python -m src.production.build_dataset [--out CAMINHO]
```

Pacote `src/production/`:

| Arquivo | Papel |
|---|---|
| `build_dataset.py` | orquestra: carrega parquet → aplica views → materializa resumo → valida → escreve manifest |
| `validation.py` | 17 checks estruturais + invariantes analíticas (2026 parcial, unidades não misturadas, anomalia do radar) |
| `manifest.py` | grava `data/production/manifest.json` (quando, de quais parquet + hash, o que contém, tamanho) |

O comando é reprodutível e idempotente (recria o arquivo do zero). Sai com
código ≠ 0 se qualquer check falhar.

## 6. Processo de atualização (dados atuais)

```
python -m src.run_etl                     # RAW → STAGING → FACT → Postgres + parquet
python -m src.analytics.build_views       # camada analítica no Postgres
pytest                                    # 64 testes ETL/analytics/API (Postgres)
python -m src.production.build_dataset     # gera atlas_public.duckdb
pytest tests/test_production_parity.py     # 25 testes: Postgres × DuckDB idênticos
python -m scripts.bench_engines            # (opcional) benchmark comparativo
# deploy: publicar o novo atlas_public.duckdb + a API
```

## 7. Quando chegar `BancoVDE 2027.xlsx`

1. `cp BancoVDE\ 2027.xlsx data/raw/`
2. registrar o arquivo em `src/config.py` (`RAW_FILES`) — o ETL falha
   explicitamente para ano não mapeado, nunca assume.
3. `python -m src.run_etl` → reconciliação 3x/3x deve passar
4. `python -m src.analytics.build_views`
5. `pytest` (a fixture de ano parcial em `conftest.py` cobre a lógica)
6. `python -m src.production.build_dataset`
7. `pytest tests/test_production_parity.py` → paridade em cima do dado novo
8. deploy do novo `atlas_public.duckdb`

O flag `is_partial_year` é derivado dos dados (não hardcoded), então 2027
parcial e 2026 deixando de ser o "último ano" são absorvidos automaticamente.

## Publicação do arquivo

O `atlas_public.duckdb` (~17 MB) **é versionado** em `data/production/` — é o
que o `render.yaml` publica junto com a API (o repo é o artefato de deploy no
Render). Todo o resto de `data/production/` continua gitignored.

Regenerar depois de novos dados: `python -m src.production.build_dataset`,
depois commitar o `.duckdb` e o `manifest.json` atualizados. Alternativas para
datasets maiores no futuro: Git LFS ou download de object storage no boot via
`DUCKDB_PATH`.

## Production Deployment

### Desenvolvimento

PostgreSQL local (Docker: `atlas_postgres`). `DATABASE_ENGINE` ausente ou
`postgres`. É a fonte da verdade — ETL, analytics, Power BI, testes de paridade.

```bash
docker compose up -d
uvicorn src.api.main:app --reload --port 8000
```

### Produção

DuckDB embarcado. **Nenhum PostgreSQL, Docker, banco externo ou cartão.**
Runtime: `requirements-api.txt` (fastapi, uvicorn, sqlalchemy, duckdb,
duckdb-engine, pydantic, python-dotenv — sem pandas/numpy/psycopg).

Verificado: com `DATABASE_ENGINE=duckdb`, `import src.api.main` **não carrega**
`psycopg`, `psycopg2`, `pandas` nem `numpy`.

### Gerar o dataset

```bash
python -m src.production.build_dataset       # → data/production/atlas_public.duckdb
```

### Rodar produção localmente (Postgres pode estar desligado)

```bash
DATABASE_ENGINE=duckdb \
DUCKDB_PATH=data/production/atlas_public.duckdb \
CORS_ORIGINS=http://localhost:3000 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Deploy

```
GitHub  →  Render Free (Web Service Python)  →  FastAPI + atlas_public.duckdb  →  JSON
                                                        ▲
                                          Sentinel.io Web (Vercel) consome
```

- `render.yaml` na raiz — **só** `type: web`, sem bloco `databases:`.
- `Procfile` na raiz — mesmo start command, para Koyeb/Railway.
- Start command respeita `$PORT` (injetado pelo provedor) — nunca fixa 8000.
- Passos: Render → New → Blueprint → apontar para o repo → ajustar
  `CORS_ORIGINS` para o domínio real do Sentinel.io.
- Free tier hiberna após ~15 min ocioso (cold start ~50 s; a 1ª query DuckDB
  do processo custa +~0,5 s para parsear as views).

### Variáveis de ambiente (produção)

| Variável | Valor | Obrigatória |
|---|---|---|
| `DATABASE_ENGINE` | `duckdb` | sim |
| `DUCKDB_PATH` | `data/production/atlas_public.duckdb` | não (é o default) |
| `CORS_ORIGINS` | `http://localhost:3000,https://<vercel>` | sim (nunca `*`) |
| `PYTHON_VERSION` | `3.11.9` | Render (runtime nativo) |

**O PostgreSQL NÃO é necessário em produção.**

## Configuração

| Variável | Default | Efeito |
|---|---|---|
| `DATABASE_ENGINE` | `postgres` | `duckdb` → serving read-only |
| `DUCKDB_PATH` | `data/production/atlas_public.duckdb` | localização do arquivo |
| `POSTGRES_*` | ver `.env.example` | usados só quando engine=postgres |
| `CORS_ORIGINS` | localhost | domínio do Sentinel.io em produção |
