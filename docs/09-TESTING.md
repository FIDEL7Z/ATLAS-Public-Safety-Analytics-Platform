# 09 — Testes e Qualidade

> Navegação: [Índice](README.md) · ← [Deploy](08-DEPLOYMENT.md) · Próximo → [Atualização de dados](10-DATA_REFRESH.md)

**89 testes automatizados** (pytest). Config em `pytest.ini`
(`pythonpath = .`, `testpaths = tests`).

```bash
pytest                    # tudo (engine padrão = postgres)
pytest -q                 # resumido
pytest tests/test_api.py  # só um arquivo
```

## Distribuição (verificada)

| Arquivo | Testes | O que cobre | Precisa de |
|---|--:|---|---|
| `tests/test_staging.py` | 4 | staging preserva linhas, tipagem, `total_vitima` removida | fixture sintética |
| `tests/test_dimensions.py` | 4 | surrogate keys determinísticas, `is_partial_year`, região IBGE | fixture sintética |
| `tests/test_fact.py` | 8 | agregação por grão (SUM, nunca dedup), unpivot, nulos omitidos, sem negativos | fixture sintética |
| `tests/test_reconciliation.py` | 2 | RAW == FACT por evento | fixture sintética |
| `tests/test_analytics_sql.py` | 15 | as 31 views: paridade com o cálculo Python, regras de unidade, período comparável | **PostgreSQL** |
| `tests/test_api.py` | 31 | os 17 endpoints: contratos, 404/422/400, valores conhecidos, read-only | **PostgreSQL** ou **DuckDB** |
| `tests/test_production_parity.py` | 25 | mesma query no PostgreSQL e no DuckDB → resultado idêntico + invariantes | **PostgreSQL + DuckDB** |
| **Total** | **89** | | |

Testes de integração (`test_analytics_sql`, `test_api`, `test_production_parity`)
**pulam automaticamente** se a dependência não estiver disponível — não
quebram a suíte.

## Estratégia por camada

### ETL (18 testes) — fixture sintética

`tests/conftest.py` fornece `sample_raw_by_year`: um dataset minúsculo que
reproduz os padrões críticos dos dados reais —

- linhas "duplicadas" na mesma chave dimensional (padrão DF) que devem
  somar, não descartar;
- um valor "não informado" dentro da família aplicável (não vira linha 0,
  não quebra o pipeline);
- as 3 famílias de medida;
- `agente`/`arma`/`faixa_etaria` como parte do grão;
- um ano completo (12 meses) e um ano parcial (3 meses) — para testar
  `is_partial_year`.

Roda sem PostgreSQL e sem os arquivos `.xlsx` reais.

### Camada analítica (15 testes) — contra PostgreSQL

Valida que as views SQL produzem os mesmos números que o cálculo de
referência em Python (ex.: `vw_qualidade_nao_informado` vs
`compute_nao_informado_stats`), e as regras estruturais (nenhuma view soma
unidades incompatíveis; período comparável nunca é 12 vs 6).

### API (31 testes) — contra PostgreSQL **ou** DuckDB

`tests/test_api.py` sobe o app com `TestClient` e valida cada endpoint. Os
asserts incluem **valores conhecidos** conferidos manualmente:

- `/temporal/yoy` Homicídio doloso 2025→2026: `base_value == 16081.0`,
  `comparison_value == 13931.0`, `variation_percent == -13.37`,
  `months_compared == 6`.
- `/geography/uf` Homicídio doloso 2025: 1º lugar `BA / Nordeste / 3663.0`.
- `/radar` `min_abs_z=3`: contém "Morte por intervenção de Agente do Estado"
  em out/2025 com `z_score == 3.03`.
- `/metadata`: `dataset == {start:"2024-01", end:"2026-06", partial_year:true}`,
  `coverage == {indicators:31, ufs:27, municipalities:5298}`.
- `test_only_get_methods_exposed_read_only_api`: percorre o `openapi.json` e
  garante que nenhum path expõe método de escrita.

Rodar contra o DuckDB (prova de equivalência):

```bash
DATABASE_ENGINE=duckdb pytest tests/test_api.py    # 31 passed em ~1,3 s
```

Os mesmos 31 testes (com os mesmos valores conhecidos) passam nos dois
engines.

### Paridade PostgreSQL × DuckDB (25 testes) — `tests/test_production_parity.py`

Para cada endpoint, roda a **mesma consulta** nos dois bancos e exige
resultado idêntico (`_both(pg, ddb, sql, params)` → `assert p == d`),
normalizando `Decimal`/`float` para 3 casas (a API serializa como `float`) e
datas para ISO. Cobre:

- paridade: `/indicators`, `/kpis` (com e sem filtro, 3 combinações),
  `/temporal` (3 indicadores), `/temporal/yoy`, `/geography/uf` e
  `/municipalities`, `/rankings/uf` (3 casos) `/municipalities`
  `/indicators`, `/radar`, `/metadata` + listas;
- invariantes (§13): unidades nunca misturadas (`max(count(distinct
  familia_medida)) == 1`); 2026 parcial de 6 meses; `meses_incluidos`
  sempre 6 (nunca 12 vs 6); anomalia do radar `z ≈ 3.03`; `is_partial_year`
  é data-driven (só 2026).

Pula se faltar PostgreSQL **ou** o arquivo `atlas_public.duckdb`.

## Validações do dataset de produção (não-pytest)

O builder (`python -m src.production.build_dataset`) roda **17 checks**
internos (`src/production/validation.py`) e sai com código ≠ 0 se algum
falhar. Cobrem: contagem da fato, staging ausente, 8 dimensões, cada view da
API responde, `vw_qualidade_resumo` materializada, 2026 parcial, 1 família
por indicador, anomalia do radar.

## Data Quality do ETL (não-pytest)

`python -m src.run_etl` gera:

- `data/quality_reports/DATA_QUALITY_REPORT.md` — 8 checks estruturais +
  contagem por camada + "não informado" por evento.
- `docs/ETL_RECONCILIATION.md` — RAW × STAGING × FACT por evento (31/31
  PASS).

`run_etl` sai com código `1` se algum check de qualidade ou reconciliação
falhar.

## Benchmarks — `python -m scripts.bench_engines`

Sobe a API em cada engine (uvicorn subprocess), aquece, mede N repetições
por endpoint. Requer PostgreSQL + `atlas_public.duckdb`.

Resultado medido (mesma máquina, `QueuePool`, 25 reps):

| Endpoint | PostgreSQL (média) | DuckDB (média) | Ganho |
|---|--:|--:|--:|
| `/kpis` (sem filtro) | 957 ms | 53 ms | **18×** |
| `/rankings/uf` | 611 ms | 47 ms | **13×** |
| `/rankings/municipalities` | 591 ms | 41 ms | **14×** |
| `/rankings/indicators` | 240 ms | 15 ms | **15×** |
| `/temporal/yoy` | 375 ms | 22 ms | **17×** |
| `/radar` | 830 ms | 21 ms | **39×** |
| `/health` | 3,7 ms | 2,2 ms | 1,7× |
| `/temporal`, `/geography/uf`, `/kpis` filtrado | 7–13 ms | 10–18 ms | leve regressão |

PostgreSQL: end-to-end via `curl`, `work_mem=128MB`, 2 workers paralelos.
DuckDB: query pura, 1 processo. Corpo da resposta idêntico em todos os
endpoints, exceto `/radar` (diferença de representação de `float` em
`historical_mean`/`standard_deviation`; `z_score` idêntico).
