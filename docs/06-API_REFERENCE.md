# 06 — Referência da API

> Navegação: [Índice](README.md) · ← [Banco de dados](05-DATABASE.md) · Próximo → [Produção](07-PRODUCTION.md)

Fonte da verdade: o código em `src/api/` e o `openapi.json` gerado pelo
FastAPI. A documentação interativa fica em **`/docs`** (Swagger) e
**`/redoc`** com o servidor no ar.

- **Base URL (produção)**: `https://sentinel-api-sjie.onrender.com/api/v1`
- **Base URL (local)**: `http://localhost:8000/api/v1`
- Todos os endpoints são **`GET`** (17 rotas). Não há `POST`/`PUT`/`PATCH`/
  `DELETE` — garantido pelo teste `test_only_get_methods_exposed_read_only_api`.
- Respostas em JSON. Sem autenticação.
- CORS: apenas método `GET`, origens da variável `CORS_ORIGINS` (nunca `*`).

## Formato de erro (todos os endpoints)

```json
{ "error": { "code": "INVALID_PARAMETER", "message": "descrição legível" } }
```

| HTTP | `code` | Quando |
|---|---|---|
| 400 | `INVALID_PARAMETER` | filtro semanticamente inválido (ex.: `grupo_semantico` inexistente; anos sem dados para YoY) |
| 404 | `NOT_FOUND` | indicador não encontrado |
| 422 | `VALIDATION_ERROR` | parâmetro com tipo/formato inválido (validação automática do Pydantic) |
| 500 | `INTERNAL_ERROR` | erro inesperado — logado no servidor, nunca exposto |
| 503 | `SERVICE_UNAVAILABLE` | banco indisponível (**apenas** em `/health`) |

Stack traces e detalhes internos nunca aparecem na resposta.

---

## Health

### `GET /health`

Sem parâmetros. Verifica a conexão com o banco (PostgreSQL ou o arquivo
DuckDB, conforme `DATABASE_ENGINE`).

**200**
```json
{ "status": "ok", "service": "atlas-api", "database": "connected" }
```
**503** — `{ "status": "error", "service": "atlas-api", "database": "disconnected" }`

---

## Indicators

### `GET /indicators`

Lista os 31 indicadores, lidos de `analytics.vw_dim_indicador`.

**200**
```json
{
  "data": [
    {
      "id": 1,
      "evento": "Apreensão de Cocaína",
      "familia_medida": "peso",
      "unidade": "kg (não confirmado pela fonte)",
      "tipo_indicador": "Apreensão - Peso",
      "grupo_semantico": "Apreensões (Peso)"
    }
  ],
  "total": 31
}
```

### `GET /indicators/{indicator_id}`

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int (path) | sim | ID do indicador |

**200** — mesmo objeto de item acima. **404** se não existir.

---

## KPIs

### `GET /kpis`

Totais agregados **por indicador**, com filtros opcionais combináveis. Cada
item da resposta é de **um único indicador** — a API nunca soma unidades
diferentes.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | não | filtra por um indicador |
| `uf` | string (2) | não | sigla da UF (ex.: `PB`) — normalizada para maiúsculas |
| `municipio` | string | não | nome do município |
| `ano` | int (2000–2100) | não | ano |
| `abrangencia` | string | não | `Estadual` \| `Polícia Federal` \| `Polícia Rodoviária Federal` |

**Fonte**: `fact_indicadores` + dimensões (SQL agregado, `GROUP BY` por
indicador).

**200**
```json
{
  "filters": { "indicator_id": 1, "uf": null, "municipio": null, "ano": null, "abrangencia": null },
  "data": [
    {
      "indicator_id": 1,
      "indicator": "Apreensão de Cocaína",
      "familia_medida": "peso",
      "value": 499195.813,
      "unit": "kg (não confirmado pela fonte)",
      "n_registros": 1493
    }
  ]
}
```
`n_registros` = quantidade de linhas de fato somadas naquele valor.
**422** se `uf` não tiver exatamente 2 caracteres.

---

## Temporal

### `GET /temporal`

Série mensal de **um** indicador.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | **sim** | a série é sempre de uma única unidade |
| `uf` | string (2) | não | |
| `municipio` | string | não | |
| `abrangencia` | string | não | |
| `ano_inicio` | int (2000–2100) | não | |
| `ano_fim` | int (2000–2100) | não | |

**Fonte**: `fact_indicadores` agregada por `(ano, mes)`.

**200**
```json
{
  "indicator": "Roubo de veículo",
  "indicator_id": 25,
  "familia_medida": "contagem",
  "unit": "ocorrências",
  "data": [
    { "year": 2026, "month": 1, "value": 21345.0, "is_partial_year": true }
  ]
}
```
**404** se o indicador não existir.

### `GET /temporal/yoy`

Comparação ano a ano **sempre em período comparável** — nunca Jan–Dez de um
ano contra Jan–Jun de outro. Usa `analytics.vw_comparacao_anual_comparavel`.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | **sim** | |
| `base_year` | int | não | padrão: `comparison_year - 1` |
| `comparison_year` | int | não | padrão: último ano disponível |

**200** (Homicídio doloso (id 12), 2025 vs 2026)
```json
{
  "indicator": "Homicídio doloso",
  "indicator_id": 12,
  "unit": "pessoas",
  "base_value": 16081.0,
  "comparison_value": 13931.0,
  "variation_absolute": -2150.0,
  "variation_percent": -13.37,
  "comparison": {
    "base_year": 2025,
    "comparison_year": 2026,
    "months_compared": 6,
    "partial_period": true
  }
}
```
**404** indicador inexistente · **400** anos sem dados suficientes para
comparar.

---

## Geography

### `GET /geography/uf`

Totais por UF de um indicador.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | **sim** | |
| `ano` | int (2000–2100) | não | |
| `mes` | int (1–12) | não | |
| `regiao` | string | não | |
| `abrangencia` | string | não | |

**200**
```json
{
  "indicator": "Homicídio doloso",
  "indicator_id": 12,
  "unit": "pessoas",
  "data": [
    { "uf": "BA", "regiao": "Nordeste", "value": 3663.0 }
  ]
}
```
Ordenado por `value` decrescente. **404** indicador inexistente.

### `GET /geography/municipalities`

Totais por município, **paginado**.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | **sim** | |
| `uf` | string (2) | não | |
| `ano` | int (2000–2100) | não | |
| `page` | int (≥ 1) | não | padrão 1 |
| `page_size` | int (1–100) | não | padrão 50 |

**200**
```json
{
  "page": 1, "page_size": 5, "total": 1284,
  "indicator": "Homicídio doloso", "indicator_id": 12, "unit": "pessoas",
  "data": [ { "uf": "SP", "municipio": "SÃO PAULO", "value": 812.0 } ]
}
```
**422** se `page_size > 100`. **404** indicador inexistente.

---

## Rankings

Todos os rankings são particionados por `(evento, ano)` — nunca misturam
unidades e nunca comparam ano parcial com ano completo dentro do mesmo
ranking. `rank` começa em 1.

### `GET /rankings/uf`

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | **sim** | |
| `ano` | int | **sim** | |
| `limit` | int (1–27) | não | padrão 10 |

**Fonte**: `analytics.vw_ranking_uf`.

**200**
```json
{
  "indicator": "Roubo de veículo", "indicator_id": 25, "unit": "ocorrências", "ano": 2025,
  "data": [
    { "rank": 1, "uf": "RJ", "regiao": "Sudeste", "value": 25235.0 },
    { "rank": 2, "uf": "SP", "regiao": "Sudeste", "value": 25024.0 },
    { "rank": 3, "uf": "PE", "regiao": "Nordeste", "value": 11955.0 }
  ]
}
```

### `GET /rankings/municipalities`

Params: `indicator_id` (sim), `ano` (sim), `limit` (1–100, padrão 10).
Fonte: `analytics.vw_ranking_municipio` (só municípios com total > 0).
Item: `{ rank, uf, municipio, value }`.

### `GET /rankings/indicators`

Ranking de indicadores **dentro do mesmo grupo semântico**.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `grupo_semantico` | string | **sim** | `Vítimas` \| `Ações Policiais` \| `Ocorrências` \| `Apreensões (Peso)` \| `Apreensões (Unidade)` \| `Serviços` |
| `ano` | int | **sim** | |
| `limit` | int (1–31) | não | padrão 10 |

**Fonte**: `analytics.vw_ranking_indicador`.

**200**
```json
{
  "grupo_semantico": "Ocorrências", "ano": 2025,
  "data": [ { "rank": 1, "evento": "Tráfico de drogas", "grupo_semantico": "Ocorrências", "value": 231044.0 } ]
}
```
**400** (`INVALID_PARAMETER`) se `grupo_semantico` não for um dos 6 valores.

---

## Radar

### `GET /radar`

Desvios de cada mês em relação à **média histórica do próprio indicador**
(z-score, método explicável, sem Machine Learning). Usa
`analytics.vw_desvio_media_historica`.

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | não | filtra por indicador |
| `ano` | int (2000–2100) | não | |
| `min_abs_z` | float (≥ 0) | não | só retorna \|z_score\| ≥ este valor |
| `limit` | int (1–930) | não | padrão 50 |

> `z_score` é um valor **estatístico**. A API não afirma causalidade nem
> rotula nada como "crime" ou "problema" — a interpretação é de quem
> consome. É o único endpoint que pode retornar indicadores de unidades
> diferentes juntos (z-score é adimensional).

**200**
```json
{
  "data": [
    {
      "indicator": "Morte por intervenção de Agente do Estado",
      "year": 2025, "month": 10, "value": 706.0,
      "historical_mean": 536.4666666666667,
      "standard_deviation": 55.981385795240506,
      "z_score": 3.03
    }
  ],
  "total": 1
}
```
Ordenado por `|z_score|` decrescente.

---

## Metadata

### `GET /metadata`

Visão geral do dataset. Lê 6 colunas de `analytics.vw_qualidade_resumo`.

**200**
```json
{
  "dataset": { "start": "2024-01", "end": "2026-06", "partial_year": true },
  "coverage": { "indicators": 31, "ufs": 27, "municipalities": 5298 }
}
```

### Listas de valores para filtros

| Endpoint | Resposta | Fonte |
|---|---|---|
| `GET /metadata/ufs` | `[{ "uf": "AC", "regiao": "Norte" }, ...]` (27) | `dim_localidade` |
| `GET /metadata/years` | `[2024, 2025, 2026]` | `dim_tempo` |
| `GET /metadata/abrangencias` | `[{ "abrangencia": "Estadual" }, ...]` (3) | `dim_abrangencia` |
| `GET /metadata/municipalities?uf=PB` | `[{ "uf": "PB", "municipio": "AGUIAR" }, ...]` | `dim_localidade` |

`GET /metadata/municipalities` aceita `uf` opcional (string, 2 chars).

---

## Endpoints utilitários (FastAPI)

| Rota | O que é |
|---|---|
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc |
| `GET /openapi.json` | especificação OpenAPI 3.1 — `info.title = "Sentinel.io Analytics API"`, `info.version = "1.0.0"` |
