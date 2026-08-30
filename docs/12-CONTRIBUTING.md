# 12 — Contribuição e Setup Local

> Navegação: [Índice](README.md) · ← [Variáveis de ambiente](11-ENVIRONMENT_VARIABLES.md) · Próximo → [Troubleshooting](13-TROUBLESHOOTING.md)

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Python | 3.11 | tudo |
| Docker + Docker Compose | recente | subir o PostgreSQL de desenvolvimento |
| Git | recente | versionamento |

Não há frontend neste repositório — não é necessário Node.js.

## Clonar e instalar

```bash
git clone https://github.com/FIDEL7Z/ATLAS-Public-Safety-Analytics-Platform.git
cd "ATLAS — Public Safety Analytics Platform"

python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate

pip install -r requirements.txt          # dev completo (ETL + analytics + testes)
# ou, só para servir a API em modo produção:
pip install -r requirements-api.txt
```

## Configurar o ambiente

```bash
cp .env.example .env
```

Os defaults já funcionam com o `docker-compose`. Ajuste apenas se sua porta
5433 estiver ocupada.

## Subir o PostgreSQL de desenvolvimento

```bash
docker compose up -d
```

Sobe dois contêineres: `atlas_postgres` (porta host 5433) e `atlas_api`
(porta 8000, build a partir de `Dockerfile.api`). Para trabalhar só no
banco:

```bash
docker compose up -d postgres
```

## Rodar o ETL

Requer os 3 arquivos `BancoVDE <ano>.xlsx` em `data/raw/` (não versionados —
dados de origem externa e volumosos).

```bash
python -m src.run_etl                 # RAW → ... → PostgreSQL + data/processed/*.parquet
python -m src.analytics.build_views   # aplica as 31 views SQL
```

Sem os `.xlsx`, você ainda pode rodar toda a suíte de testes de ETL (usa uma
fixture sintética) e, se `data/processed/*.parquet` já existir, o builder de
produção.

## Rodar a API

### Modo desenvolvimento (PostgreSQL)

```bash
uvicorn src.api.main:app --reload --port 8000
# DATABASE_ENGINE ausente → postgres (default)
```

Swagger: <http://localhost:8000/docs>

### Modo produção (DuckDB) — localmente

```bash
python -m src.production.build_dataset       # gera data/production/atlas_public.duckdb (se ainda não existe)

DATABASE_ENGINE=duckdb CORS_ORIGINS=http://localhost:3000 \
  uvicorn src.api.main:app --port 8000
```

Docker/PostgreSQL podem estar desligados neste modo.

## Rodar os testes

```bash
pytest                                  # 89 testes (engine postgres)
pytest -q                               # resumido
DATABASE_ENGINE=duckdb pytest tests/test_api.py     # 31 testes contra DuckDB
pytest tests/test_production_parity.py   # 25 testes de paridade (precisa dos dois)
```

Detalhe em [09 — Testes](09-TESTING.md).

## Gerar o dataset de produção

```bash
python -m src.production.build_dataset
python -m scripts.bench_engines          # opcional — benchmark PostgreSQL × DuckDB
```

## Estrutura do repositório

```
src/
├── config.py               # caminhos, RAW_FILES, logger compartilhado
├── run_etl.py              # orquestrador do ETL
├── ingestion/              # camada RAW (leitura dos .xlsx)
├── transformation/         # staging, dimensões, fato, tabelas de referência
├── validation/             # data quality (8 checks) + reconciliação (31 eventos)
├── loading/                # carga no PostgreSQL (COPY)
├── analytics/              # build_views.py — aplica sql/analytics/*.sql
├── production/             # Fase 6 — builder do atlas_public.duckdb
└── api/                    # FastAPI
    ├── main.py             # app, CORS, handlers de erro
    ├── config.py           # settings + seleção de engine
    ├── database.py         # engine SQLAlchemy (postgres | duckdb)
    ├── dependencies.py     # get_db, PageParams
    ├── routers/            # 8 arquivos, 17 rotas GET
    ├── services/           # regras de negócio
    ├── repositories/       # SQL parametrizado
    └── schemas/            # modelos Pydantic de resposta

sql/
├── staging/  dimensions/  facts/    # DDL do PostgreSQL
└── analytics/                       # 001..007 — as 31 views

tests/          # 7 arquivos, 89 testes
docs/           # esta documentação + referências de fase
scripts/        # bench_engines.py
data/
├── raw/         # .xlsx (não versionado)
├── processed/   # *.parquet (não versionado)
├── production/  # atlas_public.duckdb + manifest.json (VERSIONADOS)
└── quality_reports/   # relatórios do ETL
```

## Convenções

- **Não inventar dados.** Um evento ou UF não mapeado faz o pipeline falhar
  explicitamente. Atualize as tabelas de referência com base em observação
  real.
- **SQL sempre parametrizado** nos repositories — nunca concatenação de
  string com input do usuário.
- **Rodar `pytest` antes de qualquer commit.** Baseline: 89 passed.
- **Rodar os testes de paridade** ao mexer em SQL analítico ou no builder.
- **Commit/push exigem autorização humana** — nada é automatizado.
- A camada analítica (`sql/analytics/`) é a fonte da lógica de ranking,
  z-score e período comparável. Não reimplementar essas regras em Python.

## Fluxo de contribuição

1. Criar branch a partir de `main`.
2. Implementar + `pytest` (+ testes de paridade se aplicável).
3. Se mexeu em dados/SQL: `python -m src.production.build_dataset` e
   commitar o `.duckdb` atualizado.
4. Abrir PR. Descrever o impacto em números (contagens, endpoints).
