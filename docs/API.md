# Sentinel.io Analytics API — Contrato

Documentação completa dos endpoints. A documentação interativa (Swagger) está sempre disponível em `/docs` com o servidor rodando — este documento é a referência estática, versionada junto com o código.

Todos os endpoints são **somente leitura** (`GET`), prefixados com `/api/v1`, e retornam JSON.

## Formato de erro (todos os endpoints)

```json
{ "error": { "code": "INVALID_PARAMETER", "message": "descrição legível" } }
```

| Status | Code | Quando |
|---|---|---|
| 400 | `INVALID_PARAMETER` | Combinação de filtros semanticamente inválida (ex.: `grupo_semantico` inexistente, anos sem dados suficientes para YoY) |
| 404 | `NOT_FOUND` | Recurso (indicador) não encontrado |
| 422 | `VALIDATION_ERROR` | Parâmetro com tipo/formato inválido (validação automática do Pydantic) |
| 500 | `INTERNAL_ERROR` | Erro não esperado — logado no servidor, nunca exposto ao cliente |
| 503 | `SERVICE_UNAVAILABLE` | PostgreSQL indisponível (só em `/health`) |

---

## `GET /api/v1/health`

Sem parâmetros. Retorna 200 (`database: "connected"`) ou 503 (`database: "disconnected"`).

```json
{ "status": "ok", "service": "atlas-api", "database": "connected" }
```

---

## `GET /api/v1/indicators`

Lista os 31 indicadores. Sem parâmetros.

```json
{
  "data": [
    { "id": 12, "evento": "Homicídio doloso", "familia_medida": "vitima", "unidade": "pessoas", "tipo_indicador": "Vítima - Violência Letal Intencional", "grupo_semantico": "Vítimas" }
  ],
  "total": 31
}
```

## `GET /api/v1/indicators/{indicator_id}`

Metadados de um indicador. 404 se não existir.

---

## `GET /api/v1/kpis`

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `indicator_id` | int | não | filtra por 1 indicador |
| `uf` | string(2) | não | sigla da UF |
| `municipio` | string | não | nome exato do município |
| `ano` | int | não | |
| `abrangencia` | string | não | Estadual \| Polícia Federal \| Polícia Rodoviária Federal |

Cada item da resposta é de **um único indicador** — nunca uma soma cross-indicador, mesmo sem `indicator_id`.

```json
{
  "filters": { "indicator_id": 12, "uf": "PB", "municipio": null, "ano": 2025, "abrangencia": null },
  "data": [
    { "indicator_id": 12, "indicator": "Homicídio doloso", "familia_medida": "vitima", "value": 198.0, "unit": "pessoas", "n_registros": 36 }
  ]
}
```

---

## `GET /api/v1/temporal`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `indicator_id` | int | **sim** |
| `uf`, `municipio`, `abrangencia` | string | não |
| `ano_inicio`, `ano_fim` | int | não |

```json
{
  "indicator": "Homicídio doloso", "indicator_id": 12, "familia_medida": "vitima", "unit": "pessoas",
  "data": [{ "year": 2025, "month": 1, "value": 3053.0, "is_partial_year": false }]
}
```

## `GET /api/v1/temporal/yoy`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `indicator_id` | int | **sim** |
| `base_year` | int | não (padrão: `comparison_year - 1`) |
| `comparison_year` | int | não (padrão: o último ano disponível) |

`months_compared` é sempre o mesmo para os dois anos — nunca compara Jan-Dez com Jan-Jun.

```json
{
  "indicator": "Homicídio doloso", "indicator_id": 12, "unit": "pessoas",
  "base_value": 16081.0, "comparison_value": 13931.0,
  "variation_absolute": -2150.0, "variation_percent": -13.37,
  "comparison": { "base_year": 2025, "comparison_year": 2026, "months_compared": 6, "partial_period": true }
}
```

---

## `GET /api/v1/geography/uf`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `indicator_id` | int | **sim** |
| `ano`, `mes` | int | não |
| `regiao`, `abrangencia` | string | não |

```json
{ "indicator": "Homicídio doloso", "indicator_id": 12, "unit": "pessoas",
  "data": [{ "uf": "BA", "regiao": "Nordeste", "value": 3663.0 }] }
```

## `GET /api/v1/geography/municipalities`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `indicator_id` | int | **sim** |
| `uf`, `ano` | | não |
| `page` (≥1), `page_size` (1-100, padrão 50) | int | não |

```json
{ "page": 1, "page_size": 50, "total": 646, "indicator": "Homicídio doloso", "indicator_id": 12, "unit": "pessoas",
  "data": [{ "uf": "SP", "municipio": "SÃO PAULO", "value": 1122.0 }] }
```

---

## `GET /api/v1/rankings/uf`

`indicator_id` (obrig.), `ano` (obrig.), `limit` (1-27, padrão 10).

## `GET /api/v1/rankings/municipalities`

`indicator_id` (obrig.), `ano` (obrig.), `limit` (1-100, padrão 10).

## `GET /api/v1/rankings/indicators`

`grupo_semantico` (obrig. — um de: `Vítimas`, `Ocorrências`, `Ações Policiais`, `Apreensões (Peso)`, `Apreensões (Unidade)`, `Serviços`), `ano` (obrig.), `limit` (1-31, padrão 10). 400 se `grupo_semantico` inválido.

Todos retornam `data: [{ "rank": 1, ... , "value": ... }]`, rank sempre começando em 1.

---

## `GET /api/v1/radar`

| Parâmetro | Tipo | Obrigatório |
|---|---|---|
| `indicator_id` | int | não |
| `ano` | int | não |
| `min_abs_z` | float | não — só retorna \|z_score\| ≥ este valor |
| `limit` | int | não (padrão 50, máx 930) |

```json
{ "data": [
    { "indicator": "Morte por intervenção de Agente do Estado", "year": 2025, "month": 10,
      "value": 706.0, "historical_mean": 536.47, "standard_deviation": 55.98, "z_score": 3.03 }
  ], "total": 1 }
```

**`z_score` é um valor estatístico — nunca uma afirmação de causalidade, crime ou culpa.** Diferente de `/kpis`, este endpoint PODE retornar indicadores de famílias/unidades diferentes juntos, porque z-score é um desvio padronizado (adimensional), não um valor bruto — comparável entre indicadores por construção.

---

## `GET /api/v1/metadata`

```json
{ "dataset": { "start": "2024-01", "end": "2026-06", "partial_year": true },
  "coverage": { "indicators": 31, "ufs": 27, "municipalities": 5298 } }
```

## `GET /api/v1/metadata/ufs` · `/years` · `/abrangencias` · `/municipalities?uf=`

Listas de valores válidos para os filtros acima — sempre lidas do banco, nunca hardcoded.

---

## Exemplos de uso completo (curl)

```bash
curl "http://localhost:8000/api/v1/indicators"
curl "http://localhost:8000/api/v1/kpis?indicator_id=12&uf=PB&ano=2025"
curl "http://localhost:8000/api/v1/temporal?indicator_id=12&ano_inicio=2024&ano_fim=2026"
curl "http://localhost:8000/api/v1/temporal/yoy?indicator_id=12&base_year=2025&comparison_year=2026"
curl "http://localhost:8000/api/v1/geography/uf?indicator_id=12&ano=2025"
curl "http://localhost:8000/api/v1/geography/municipalities?indicator_id=12&uf=SP&page=1&page_size=20"
curl "http://localhost:8000/api/v1/rankings/uf?indicator_id=12&ano=2025&limit=10"
curl "http://localhost:8000/api/v1/radar?min_abs_z=2&limit=20"
curl "http://localhost:8000/api/v1/metadata"
```
