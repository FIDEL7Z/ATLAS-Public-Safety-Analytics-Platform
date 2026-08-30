# 05 — Banco de Dados

> Navegação: [Índice](README.md) · ← [Pipeline ETL](04-ETL_PIPELINE.md) · Próximo → [Referência da API](06-API_REFERENCE.md)

Dois bancos, o mesmo modelo lógico. DDL versionado em `sql/`.

## PostgreSQL 16 (desenvolvimento)

Sobe via `docker compose up -d` (`docker-compose.yml`): imagem
`postgres:16-alpine`, porta host **5433** (a 5432 costuma estar ocupada por
uma instância nativa), `work_mem=128MB` (justificado: a camada analítica
agrega a fato inteira em algumas views — ver [`ANALYTICS_MODEL.md`](ANALYTICS_MODEL.md)).

### DDL

| Arquivo | Cria |
|---|---|
| `sql/staging/001_create_stg_sinesp.sql` | `stg_sinesp` + 3 índices |
| `sql/dimensions/001_create_dimensions.sql` | as 8 dimensões |
| `sql/facts/001_create_fact_indicadores.sql` | `fact_indicadores` + 6 índices |
| `sql/analytics/001..007_*.sql` | schema `analytics` + 31 views |

### `stg_sinesp` (staging)

Cópia normalizada e tipada dos 3 arquivos, **sem nenhuma linha removida ou
agregada**. 1.996.058 linhas. Colunas de medida `NUMERIC(12,3)` /
`total_peso NUMERIC(14,3)`, nuláveis (`NULL` = não aplicável). Índices:
`ix_stg_sinesp_ano`, `ix_stg_sinesp_evento`, `ix_stg_sinesp_uf`.

### `fact_indicadores`

```sql
fact_id         BIGSERIAL PRIMARY KEY
tempo_id        INTEGER NOT NULL  REFERENCES dim_tempo(tempo_id)
localidade_id   INTEGER NOT NULL  REFERENCES dim_localidade(localidade_id)
indicador_id    INTEGER NOT NULL  REFERENCES dim_indicador(indicador_id)
abrangencia_id  INTEGER NOT NULL  REFERENCES dim_abrangencia(abrangencia_id)
agente_id       INTEGER           REFERENCES dim_agente(agente_id)          -- nullable
arma_id         INTEGER           REFERENCES dim_arma(arma_id)              -- nullable
faixa_etaria_id INTEGER           REFERENCES dim_faixa_etaria(faixa_etaria_id) -- nullable
sexo_id         INTEGER           REFERENCES dim_sexo(sexo_id)              -- nullable
valor           NUMERIC(14,3) NOT NULL  CHECK (valor >= 0)
ano_origem      SMALLINT NOT NULL
```

- **Grão**: `tempo × localidade × indicador × abrangencia × [agente] × [arma]
  × [faixa_etaria] × [sexo]`. As 4 FKs entre colchetes são `NULL` quando não
  se aplicam ao indicador (espelha a semântica dos nulos da fonte).
- **Métrica**: `valor` (único). Sempre `>= 0`, nunca nulo.
- `ano_origem`: ano do arquivo fonte, redundante com `dim_tempo.ano` por
  conveniência de filtro direto nas agregações.
- **Não guarda `total_vitima`** — é sempre `SUM(valor)` sem filtro de sexo.

### Índices de `fact_indicadores`

| Índice | Colunas | Papel |
|---|---|---|
| `fact_indicadores_pkey` | `fact_id` | PK |
| `ux_fact_grain` | `tempo, localidade, indicador, abrangencia, COALESCE(agente,-1), COALESCE(arma,-1), COALESCE(faixa,-1), COALESCE(sexo,-1)` | **UNIQUE** — garante o grão real na carga |
| `ix_fact_tempo` | `tempo_id` | join/filtro |
| `ix_fact_localidade` | `localidade_id` | join/filtro |
| `ix_fact_indicador` | `indicador_id` | filtro (o mais usado pela API) |
| `ix_fact_abrangencia` | `abrangencia_id` | join/filtro |
| `ix_fact_ano_origem` | `ano_origem` | filtro por ano |

### Dimensões

| Tabela | PK | Rótulo (UNIQUE) | Linhas | Colunas extras |
|---|---|---|--:|---|
| `dim_tempo` | `tempo_id` | `data_referencia` | 30 | `ano, mes, trimestre, nome_mes, is_partial_year` |
| `dim_localidade` | `localidade_id` | `(uf, municipio)` | 5.597 | `regiao` |
| `dim_indicador` | `indicador_id` | `evento` | 31 | `familia_medida, unidade, tipo_indicador` |
| `dim_abrangencia` | `abrangencia_id` | `abrangencia` | 3 | — |
| `dim_agente` | `agente_id` | `agente` | 9 | — |
| `dim_arma` | `arma_id` | `arma` | 9 | — |
| `dim_faixa_etaria` | `faixa_etaria_id` | `faixa_etaria` | 3 | — |
| `dim_sexo` | `sexo_id` | `sexo` | 3 | — |

### Tamanho do PostgreSQL (medido)

| Objeto | Dados | Índices | Total |
|---|--:|--:|--:|
| `fact_indicadores` | 385 MB | 586 MB | 969 MB |
| `stg_sinesp` | 213 MB | 38 MB | 251 MB |
| 8 dimensões | ~0,4 MB | ~0,9 MB | ~1,3 MB |
| schema `analytics` (views) | 0 | 0 | 0 |
| **Banco** | | | **~1.229 MB** |

## Camada analítica — 31 views (schema `analytics`)

Aplicadas por `python -m src.analytics.build_views`. As views com prefixo
`_` (`_agg_*`, `_dim_ano`) são internas — existem para não repetir a
agregação pesada. Estratégia de performance: agregar primeiro em chaves
inteiras direto sobre `fact_indicadores`, depois juntar os rótulos sobre o
resultado já pequeno.

| Arquivo | Views | Consumida pela API? |
|---|---|---|
| `001` | `vw_fato_enriquecido` | não (base para 005) |
| `002` | `_agg_indicador_ano`, `_agg_indicador_localidade_ano`, `_agg_indicador_abrangencia_ano`, `_dim_ano`, `vw_nacional`, **`vw_uf`**, **`vw_municipio`**, **`vw_indicador`**, `vw_abrangencia`, `vw_sexo`, `vw_faixa_etaria`, `vw_agente`, `vw_arma` | `vw_uf`/`vw_municipio`/`vw_indicador` (indireto, via rankings) |
| `003` | `_agg_indicador_tempo`, **`vw_evolucao_temporal`**, `vw_evolucao_temporal_metricas`, `vw_periodo_comparavel`, **`vw_comparacao_anual_comparavel`**, **`vw_desvio_media_historica`** | sim (`/temporal/yoy`, `/radar`) |
| `004` | **`vw_ranking_uf`**, **`vw_ranking_municipio`**, `vw_ranking_regiao`, **`vw_ranking_indicador`**, `vw_ranking_abrangencia`, `vw_participacao_uf` | sim (`/rankings/*`) |
| `005` | `vw_pesos_percentis`, `vw_pesos_impacto_outliers` | não (análise de outliers de peso) |
| `006` | **`vw_dim_indicador`** | sim (`/indicators`) |
| `007` | `vw_qualidade_nao_informado`, **`vw_qualidade_resumo`** | `vw_qualidade_resumo` (6 de 11 colunas) — `/metadata` |

Em **negrito**: consumidas direta ou indiretamente pela API. As demais
existem para Power BI e exploração.

## DuckDB (produção) — `data/production/atlas_public.duckdb`

Objetivo: réplica **read-only** e portátil dos dados que a API consome,
derivada automaticamente dos Parquet do ETL. Gerada por
`python -m src.production.build_dataset`.

| Métrica | Valor |
|---|---|
| Tamanho | **17,05 MB** (17.051.648 bytes) |
| Tabelas | 10 — `fact_indicadores` (5.291.040) + 8 dimensões + `analytics.vw_qualidade_resumo` (1 linha, materializada) |
| Views | 26 (schema `analytics`) |
| `valor` | `DECIMAL(14,3)` (convertido de `DOUBLE` no Parquet — garante paridade de `SUM` com o `NUMERIC` do PostgreSQL) |
| Índices | nenhum (DuckDB é colunar; os filtros da API rodam por varredura vetorizada) |
| `fact_id` | **omitido** (a API nunca filtra por ele) |

### O que muda entre PostgreSQL (31 views) e DuckDB (26 views + 1 tabela)

| Objeto | No DuckDB | Motivo |
|---|---|---|
| `vw_fato_enriquecido` (001) | **ausente** | seleciona `f.fact_id`, coluna não portada; não usada pela API |
| `vw_pesos_percentis`, `vw_pesos_impacto_outliers` (005) | **ausentes** | dependem de `vw_fato_enriquecido`; não usadas pela API |
| `vw_qualidade_nao_informado` (007) | **ausente** | depende de `stg_sinesp` (não copiada); não usada pela API |
| `vw_qualidade_resumo` (007) | **tabela de 1 linha** | materializada no build (calculada pela SQL real da view, contra a staging em memória) — evita carregar 213 MB de staging para 6 valores escalares |
| `002`, `003`, `004`, `006` | idênticas ao PostgreSQL | aplicadas verbatim |

`stg_sinesp` **não existe** no dataset de produção. Detalhe do processo de
build em [07 — Produção](07-PRODUCTION.md).

### Manifesto

Todo build grava `data/production/manifest.json`: quando foi construído, de
quais Parquet (com hash SHA-256), versão do DuckDB, e o inventário
(tabelas + contagens, lista de views, tamanho do arquivo).
