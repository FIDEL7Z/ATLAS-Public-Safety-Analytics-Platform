# ATLAS — Catálogo de Medidas DAX

Código completo, pronto para colar no Power BI, em [`powerbi/measures.dax`](../powerbi/measures.dax). Este documento explica o *porquê* de cada grupo — para o *como* (sintaxe exata), usar o `.dax`.

## Como aplicar

No Power BI Desktop: clique direito em **Fato Indicadores** → **Nova Medida** → colar o texto após o `=` de cada bloco do `.dax`, um de cada vez, respeitando a ordem dentro de cada grupo (medidas de baixo reusam as de cima via `[Nome da Medida]`).

## Os 6 grupos

| Grupo | Nº de medidas | O que resolve |
|---|---:|---|
| 01 — Core Metrics | 8 | Total/contagem básicos + a medida "trava" contra mistura de unidade |
| 02 — Temporal | 9 | Variação mês a mês, YoY, média móvel, comparação de período justa (2026 parcial) |
| 03 — Ranking | 5 | `RANKX` reativo a slicers (UF, município, região, indicador, abrangência) |
| 04 — Participation | 4 | % sempre calculado **dentro** da mesma família/indicador, nunca contra o total geral |
| 05 — Statistical | 9 | Percentis (peso), impacto de outliers, z-score contra média histórica |
| 06 — Data Quality | 8 | KPIs da página de auditoria, lidos das duas views satélite |

## O padrão central: "nunca misturar unidades"

A regra mais importante de todo o catálogo é a medida `Total Valor (Seguro)` (Grupo 01):

```dax
Total Valor (Seguro) =
IF([Unidades Distintas em Contexto] > 1, BLANK(), [Total Valor])
```

Qualquer card de KPI "genérico" (que não tenha um slicer de indicador fixando o contexto) deve usar **esta** medida, não `[Total Valor]` puro. Se o card estiver num contexto onde mais de uma `unidade` está presente ao mesmo tempo (ex.: nenhum filtro de indicador aplicado), a medida retorna `BLANK()` em vez de uma soma sem sentido — o card fica vazio, o que é um sinal visível de "escolha um indicador", em vez de mostrar um número que parece válido mas mistura pessoas + kg + ocorrências.

Nos cards de "Executive Overview" (Página 01), que precisam mostrar 5 números por grupo semântico simultaneamente, use as medidas por família (`Total Vítimas`, `Total Ocorrências e Ações`, `Total Peso Apreendido (kg)`) — cada uma já filtrada por `familia_medida`, então nunca cai no caso de mistura.

## Time intelligence e 2026 parcial

Todas as medidas de Grupo 02 dependem de **`Dim Tempo` estar marcada como Date Table** no Power BI (clique na tabela → aba Table Tools → "Mark as Date Table" → coluna `data_referencia`). Sem isso, `DATEADD`/`SAMEPERIODLASTYEAR`/`DATESINPERIOD` não funcionam corretamente.

`Mês Limite Comparável` e `Total Período Comparável` implementam a regra da Fase 3 (seção 5): nunca comparar Jan-Jun de um ano parcial contra Jan-Dez de um ano completo. O cálculo não tem `2026` nem `6` escritos no código — ele deriva o mês-limite de `is_partial_year`, então continua correto se um ano futuro também vier parcial.

## Estatística explicável, sem Machine Learning

Z-Score (Grupo 05) usa média e desvio padrão populacional (`STDEVX.P`) — os mesmos métodos já usados na camada SQL da Fase 2 (`analytics.vw_desvio_media_historica`), não uma técnica nova. `|Z| > 2` é candidato a mês atípico, `|Z| > 3` é forte candidato — limiares de leitura estatística padrão (não um teste de hipótese formal), usados apenas para priorizar o que olhar na página Analytical Radar.

## O que não virou medida DAX (ficou em SQL de propósito)

- `grupo_semantico` — classificação estrutural, vem de `analytics.vw_dim_indicador` (Fase 3, SQL). Repeti-la em DAX seria a "reprodução de lógica" que o princípio fundamental da Fase 3 pede para evitar.
- `% não informado` por indicador — vem de `analytics.vw_qualidade_nao_informado` (view nova da Fase 3, paridade validada 1:1 contra o cálculo em Python da Fase 1 — ver `tests/test_analytics_sql.py`). Recalcular em DAX exigiria reimportar a granularidade de `stg_sinesp` (2M linhas) só para a página de qualidade — desperdício de modelo para um número que já está certo no Postgres.
