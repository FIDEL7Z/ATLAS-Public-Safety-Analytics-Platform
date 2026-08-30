# 11 — Variáveis de Ambiente

> Navegação: [Índice](README.md) · ← [Atualização de dados](10-DATA_REFRESH.md) · Próximo → [Contribuição](12-CONTRIBUTING.md)

Carregadas via `python-dotenv` (`load_dotenv` em `src/config.py` e
`src/api/config.py`). Em desenvolvimento vêm de um arquivo `.env` na raiz
(template: `.env.example`); em produção, do painel do Render / `render.yaml`.
Nenhuma variável guarda segredo real de terceiros.

## Seleção de engine (Fase 6/7)

| Variável | Descrição | Dev | Produção | Obrigatória |
|---|---|---|---|---|
| `DATABASE_ENGINE` | `postgres` ou `duckdb` — escolhe o backend da API | `postgres` (ou ausente) | `duckdb` | não (default `postgres`) |
| `DUCKDB_PATH` | caminho do arquivo DuckDB (só usado quando engine=`duckdb`) | — | `data/production/atlas_public.duckdb` | não (default aponta para o arquivo no repo) |

## PostgreSQL (usadas quando `DATABASE_ENGINE=postgres`)

| Variável | Descrição | Dev (`.env.example`) | Obrigatória |
|---|---|---|---|
| `POSTGRES_HOST` | host do PostgreSQL | `localhost` | não (default `localhost`) |
| `POSTGRES_PORT` | porta | `5433` | não (default `5433`) |
| `POSTGRES_DB` | nome do banco | `atlas` | não (default `atlas`) |
| `POSTGRES_USER` | usuário | `atlas` | não (default `atlas`) |
| `POSTGRES_PASSWORD` | senha | `atlas_dev_only` | não (default `atlas_dev_only`) |

> `atlas_dev_only` é uma senha **exclusiva de desenvolvimento local**
> (`POSTGRES_HOST_AUTH_METHOD: trust` no `docker-compose.yml`). Não é um
> segredo de produção — produção não usa PostgreSQL.
>
> Dentro do `docker-compose`, o serviço `api` sobrescreve
> `POSTGRES_HOST=postgres` e `POSTGRES_PORT=5432` (rede interna do Docker).

## API

| Variável | Descrição | Dev | Produção | Obrigatória |
|---|---|---|---|---|
| `CORS_ORIGINS` | origens permitidas, **separadas por vírgula** — nunca `*` | `http://localhost:3000,http://localhost:5173` | domínio(s) real(is) do(s) consumidor(es) | sim em produção |
| `API_HOST` | informativo; **não** controla o bind | `0.0.0.0` | (ignorado) | não |
| `API_PORT` | informativo; **não** controla o bind | `8000` | (ignorado) | não |
| `PYTHON_VERSION` | versão do Python (runtime nativo do Render) | — | `3.11.9` | Render |

> O bind real da porta vem sempre do start command
> (`uvicorn ... --port $PORT` em produção, `--port 8000` local). `API_HOST`/
> `API_PORT` existem por herança da Fase 5 e não são lidos para o bind.

### `CORS_ORIGINS` — comportamento

`src/api/config.py`:

```python
cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
```

`src/api/main.py` aplica `CORSMiddleware(allow_origins=settings.cors_origins,
allow_methods=["GET"], ...)`. **Nunca `["*"]`** — se a variável não for
definida em produção, cai no default de localhost e o consumidor real toma
erro de CORS (sintoma esperado, corrige-se definindo a variável).

## `.env.example` (template)

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=atlas
POSTGRES_USER=atlas
POSTGRES_PASSWORD=atlas_dev_only

API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Fase 6/7 — engine do banco.
#   postgres (padrão): desenvolvimento / engenharia de dados
#   duckdb           : produção (serving read-only sobre atlas_public.duckdb)
# DATABASE_ENGINE=duckdb
# DUCKDB_PATH=data/production/atlas_public.duckdb
```

## Resumo por ambiente

| Ambiente | Variáveis que importam |
|---|---|
| **Dev — API com PostgreSQL** | `POSTGRES_*` (ou os defaults), `CORS_ORIGINS` |
| **Dev — API com DuckDB** (teste de produção) | `DATABASE_ENGINE=duckdb`, `DUCKDB_PATH` (opcional), `CORS_ORIGINS` |
| **Dev — ETL** | `POSTGRES_*` (para a carga; o resto do ETL não precisa) |
| **Produção (Render)** | `DATABASE_ENGINE=duckdb`, `DUCKDB_PATH`, `CORS_ORIGINS`, `PYTHON_VERSION` |
