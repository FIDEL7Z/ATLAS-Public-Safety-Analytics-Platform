# Sentinel.io — Metodologia do ETL (Fase 1)

Este documento descreve, camada por camada, as transformações aplicadas pelo pipeline `src/run_etl.py`. As decisões de modelagem aqui implementadas foram validadas na Fase 0.5 (`docs/MODEL_VALIDATION.md`) — este documento explica *como* elas foram implementadas em código, não repete a justificativa (ver o documento de validação para o "porquê").

## Visão geral do pipeline

```
data/raw/*.xlsx (intocado)
      │  src/ingestion/load_raw.py
      ▼
RAW (em memória, por ano)
      │  src/transformation/staging.py
      ▼
STAGING — stg_sinesp (1:1 com RAW, sem total_vitima, sem agregação)
      │  src/transformation/fact.py :: aggregate_to_real_grain
      ▼
Grão real agregado (SUM por chave dimensional completa — nunca dedup)
      │  src/transformation/fact.py :: build_fact_indicadores
      │  (unpivot: feminino/masculino/nao_informado/total/total_peso -> valor)
      ▼
FACT — fact_indicadores (formato longo)
      │  src/validation/{data_quality,reconciliation}.py
      ▼
Relatórios de qualidade + reconciliação
      │  src/loading/postgres_loader.py (COPY)
      ▼
PostgreSQL (Docker)
```

## Camada RAW

`src/ingestion/load_raw.py` lê cada `BancoVDE <ano>.xlsx` com `pandas.read_excel` (engine `openpyxl`), sem qualquer alteração de valores. Os arquivos em `data/raw/` nunca são escritos pelo pipeline.

## Camada STAGING

`src/transformation/staging.py` concatena os 3 anos, adiciona `ano_origem`, tipa as colunas (strings, numéricos, data) e seleciona exatamente as colunas definidas em `STAGING_COLUMNS`. A única coluna do RAW **não** transportada é `total_vitima` (sempre derivável, nunca persistida — Fase 0.5 §4).

**Garantia testada:** `len(staging) == len(raw)` sempre — a função lança `AssertionError` se isso não for verdade. Staging não remove, não agrega, não deduplica.

## Agregação pelo grão real

`aggregate_to_real_grain()` agrupa a staging por:

```
uf, municipio, evento, data_referencia, abrangencia, agente, arma, faixa_etaria, ano_origem
```

usando `groupby(..., dropna=False).sum(min_count=1)`. Duas decisões técnicas aqui são deliberadas:

1. **`dropna=False`**: por padrão, o `groupby` do pandas descarta grupos cuja chave contém `NaN` — o que apagaria silenciosamente todas as linhas onde `agente`/`arma`/`faixa_etaria` são nulos (a imensa maioria dos dados). `dropna=False` trata `NaN` como um valor de agrupamento válido, preservando a semântica "não aplicável" como parte legítima da chave.
2. **`min_count=1`**: por padrão, `sum()` de um grupo 100% nulo retorna `0`, não `NaN`. Isso apagaria a diferença entre "somei e deu zero" e "não havia nenhum valor para somar" — exatamente a distinção entre um indicador aplicável com valor 0 reportado e um indicador sem nenhum dado reportado (`nao_informado`, ver seção abaixo). `min_count=1` faz o `sum()` retornar `NaN` quando todas as entradas do grupo são nulas.

Esta é a etapa que implementa a regra 1 e 2 da Fase 1 ("nunca `DROP DUPLICATES`", "agregar conforme a granularidade real") — o padrão de "duplicatas" do DF (e do resíduo em outras UFs, Fase 0.5 §2) é resolvido aqui por soma, nunca por remoção de linha.

## Dimensões

`src/transformation/dimensions.py` constrói 8 dimensões a partir da staging (mais a tabela de referência estática de indicadores):

| Dimensão | Origem | Observação |
|---|---|---|
| `dim_tempo` | valores distintos de `data_referencia` | `is_partial_year` é calculada contando meses distintos por `ano` — **não** é hardcoded para 2026; qualquer ano futuro com cobertura incompleta é sinalizado automaticamente. |
| `dim_localidade` | pares distintos `(uf, municipio)` | `regiao` vem do mapeamento oficial IBGE UF→Região (`reference_data.UF_REGIAO`) — única informação externa introduzida no pipeline, não presente na fonte. |
| `dim_indicador` | tabela estática `reference_data.INDICADOR_CLASSIFICATION` | Classificação semântica dos 31 eventos (Fase 0.5 §3). Se um evento não mapeado aparecer numa carga futura, `validate_evento_coverage()` **lança exceção** em vez de seguir com uma classificação inventada. |
| `dim_abrangencia`, `dim_agente`, `dim_arma`, `dim_faixa_etaria` | valores distintos não-nulos da staging | Chaves substitutas sequenciais determinísticas (valores ordenados → 1..N). |
| `dim_sexo` | fixa (Feminino / Masculino / Não Informado) | Usada apenas para linhas da família `vitima`. |

## Unpivot para o formato longo (`fact_indicadores`)

Para cada linha do grão real agregado, `build_fact_indicadores()` tenta gerar até 5 linhas de fato — uma por coluna de medida (`feminino`, `masculino`, `nao_informado`, `total`, `total_peso`) — mas **só gera a linha se o valor não for nulo**. Não há distinção de código entre "não aplicável" (a maioria dos casos — a coluna nunca se aplica àquele evento) e "não informado" (o evento é da família certa, mas o valor específico não foi reportado): em ambos os casos, **nenhuma linha é gerada e nenhum valor é inventado** (regra 4). A distinção entre as duas causas é reportada separadamente em `DATA_QUALITY_REPORT.md`, calculada por `compute_nao_informado_stats()`.

Isso significa que:
- Um evento da família `vitima` gera até 3 linhas (uma por sexo), cada uma com seu próprio `valor`.
- Um evento das famílias `contagem` ou `peso` gera no máximo 1 linha, com `sexo_id = NULL`.
- `total_vitima` nunca existe fisicamente — é sempre `SUM(valor)` sobre as linhas de sexo de um mesmo indicador/localidade/tempo/etc., sem filtro de sexo.

### Chaves substitutas nulas por design

`agente_id`, `arma_id`, `faixa_etaria_id` e `sexo_id` são colunas **nullable** em `fact_indicadores`. Um valor nulo nessas colunas significa exatamente o que significava na fonte: "não aplicável a este indicador" — não há valor sentinela nem categoria inventada (regra 4 da Fase 1, aplicada literalmente).

## Validação de qualidade (`src/validation/data_quality.py`)

Executada sobre o resultado final. Checks: contagem de linhas por camada, duplicidade no grão final da fact table, valores negativos, nulos em campos obrigatórios, consistência de sexo (toda linha `vitima` tem `sexo_id`; nenhuma linha `contagem`/`peso` tem), consistência de família por indicador (nenhum indicador contribui simultaneamente para mais de uma família de medida), consistência de unidade (toda linha de `dim_indicador` tem unidade definida) e consistência temporal (meses contínuos por ano, flag `is_partial_year` correta). Resultado em `data/quality_reports/DATA_QUALITY_REPORT.md`.

## Reconciliação (`src/validation/reconciliation.py`)

Para cada um dos 31 eventos, soma o valor bruto (RAW, recalculado diretamente dos 3 arquivos fonte segundo a família de medida do evento) e compara com a soma correspondente em `fact_indicadores`. Como nenhuma etapa do pipeline preenche nulos com valores inventados, e `sum()` do pandas ignora `NaN` tanto no cálculo do RAW quanto no cálculo do FACT, os dois totais devem ser **matematicamente idênticos** por construção — a reconciliação é o teste que confirma isso empiricamente, linha a linha, para os dados reais. Resultado em `docs/ETL_RECONCILIATION.md`.

## Carga no PostgreSQL

`src/loading/postgres_loader.py` executa as DDLs (`sql/staging`, `sql/dimensions`, `sql/facts`, nesta ordem — dimensões antes do fato, por causa das *foreign keys*) e carrega os dados via `COPY` (não `INSERT` linha a linha — necessário para volumes de milhões de linhas em tempo hábil). O `fact_indicadores` tem um índice único sobre a combinação completa de chaves de dimensão (com `COALESCE` para tratar `NULL` como um valor de agrupamento), reforçando em nível de banco a mesma garantia de unicidade de grão validada em Python.

## Testes automatizados (`tests/`)

Os testes usam uma fixture sintética pequena (`tests/conftest.py`), não os dados reais — permite testar em segundos, não minutos, e cobre deliberadamente os casos de risco identificados nas Fases 0/0.5: duplicação estilo-DF que deve ser somada, um valor "não informado" que não deve virar 0, e uma dimensão condicional (arma) que não pode ser erroneamente somada entre categorias diferentes.
