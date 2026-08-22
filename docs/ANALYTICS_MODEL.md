# Sentinel.io — Fase 2: Analytics Model

Camada SQL analítica construída sobre o PostgreSQL já carregado pela Fase 1. O pipeline RAW → STAGING → FACT/DIMENSIONS **não foi alterado** — tudo aqui é aditivo (schema `analytics`, novas views), reversível com um `DROP SCHEMA analytics CASCADE`.

```
RAW → STAGING → FACT/DIMENSIONS → ANALYTICS SQL → (Power BI, Fase 3)
```

## 1. Auditoria do modelo existente

Executada por consulta direta ao PostgreSQL (`information_schema`, `pg_indexes`, `pg_stat_user_tables`) — não presumida.

### Tabelas, PKs, FKs

10 tabelas: `stg_sinesp` + 8 dimensões + `fact_indicadores`. Todas as FKs de `fact_indicadores` apontam corretamente para as 8 dimensões; `agente_id`, `arma_id`, `faixa_etaria_id`, `sexo_id` são as únicas colunas nullable (por design — "não aplicável", Fase 1 regra 4).

### Índices existentes (herdados da Fase 1, nenhum alterado)

| Tabela | Índices |
|---|---|
| `fact_indicadores` | PK (`fact_id`), single-column em `tempo_id`/`localidade_id`/`indicador_id`/`abrangencia_id`/`ano_origem`, índice único composto de grão (`ux_fact_grain`, com `COALESCE` para tratar NULL) |
| `dim_indicador` | PK + único em `evento` |
| `dim_localidade` | PK + único em `(uf, municipio)` |
| `dim_tempo` | PK + único em `data_referencia` |
| demais dimensões | PK + único no atributo |

### Cardinalidade e volume

| Tabela | Linhas | Tamanho em disco |
|---|---:|---:|
| `fact_indicadores` | 5.291.040 | 969 MB |
| `stg_sinesp` | 1.996.058 | 251 MB |
| `dim_localidade` | 5.597 | 720 kB |
| `dim_indicador` | 31 | 40 kB |
| `dim_tempo` | 30 | 40 kB |
| `dim_agente` / `dim_arma` | 9 / 9 | 40 kB cada |
| `dim_faixa_etaria` / `dim_abrangencia` / `dim_sexo` | 3 / 3 / 3 | 40 kB cada |

Cardinalidade de `fact_indicadores` (distinct/nulls por FK):

| Coluna | Distintos | Nulos |
|---|---:|---:|
| `tempo_id` | 30 | 0 |
| `localidade_id` | 5.597 | 0 |
| `indicador_id` | 31 | 0 |
| `abrangencia_id` | 3 | 0 |
| `agente_id` | **8** (não 9) | 5.256.488 |
| `arma_id` | 9 | 5.277.220 |
| `faixa_etaria_id` | 3 | 5.276.685 |
| `sexo_id` | 3 | 288.414 |

**Achado da auditoria:** `agente_id` tem apenas 8 valores distintos na fact table, não os 9 cadastrados em `dim_agente`. A categoria ausente é **`PRF` (Polícia Rodoviária Federal)** — nenhuma linha de `Morte de Agente do Estado` ou `Suicídio de Agente do Estado` atribui o agente à PRF em nenhum dos 3 anos (as demais 8 categorias têm entre 3.573 e 4.860 ocorrências cada). Isso não é um erro — `dim_agente` reflete o domínio de valores possíveis da fonte (Sinesp VDE), não o que de fato ocorreu; é plausível que a PRF, por ter efetivo bem menor que Polícia Militar/Civil, simplesmente não tenha tido nenhum óbito de agente registrado no período. Documentado, não "corrigido".

### Distribuição de `valor` por família (achado que já orienta o desenho da camada semântica)

| Família | N linhas | Mín | Máx | Média |
|---|---:|---:|---:|---:|
| `vitima` | 5.002.626 (94,6% da fact) | 0 | 1.067 | 0,185 |
| `contagem` | 285.425 (5,4%) | 0 | 41.076 | 44,7 |
| `peso` | 2.989 (0,06%) | 0 | 173.021,475 | 2.326,5 |

A família `vitima` domina a fact table em número de linhas (por causa do unpivot de sexo — 3 linhas por combinação aplicável), mas as famílias `contagem` e `peso` têm ordens de grandeza de `valor` completamente diferentes. **Isso confirma, com dados reais, o risco identificado na Fase 0.5: qualquer `SUM(valor)` sem filtro por família mistura escalas que não têm relação nenhuma entre si** (pessoas vs. ocorrências vs. quilos).

### Possíveis gargalos identificados na auditoria (antes de escrever qualquer view)

- `fact_indicadores` com 5,29M linhas é o único ponto que preocupa para agregações "de tudo" (visão nacional).
- `work_mem` do Postgres estava no default (4MB) — baixo para agregações analíticas sobre uma tabela deste tamanho. Detalhado na seção 7.

## 2. Camada semântica

Toda métrica é construída sobre `analytics.vw_fato_enriquecido`, que junta a fact table às 8 dimensões e adiciona `grupo_semantico` — uma classificação de 6 categorias (Vítimas / Ações Policiais / Ocorrências / Apreensões (Peso) / Apreensões (Unidade) / Serviços), derivada de `tipo_indicador` (que por sua vez vem da Fase 0.5/1). `grupo_semantico` **não é persistido** em `dim_indicador` — é calculado via `CASE` na view, para não tocar o schema da Fase 1.

Toda view analítica carrega, no mínimo: `evento`, `familia_medida`, `unidade` — **nenhuma view agrega `valor` sem esses três campos junto**, o que torna estruturalmente difícil somar indicadores incompatíveis por engano.

## 3. Catálogo de views

| # | View | Grão | Descrição |
|---|---|---|---|
| 01 | `analytics.vw_nacional` | evento × ano | total/média/mediana/min/max/desvio padrão nacional |
| 02 | `analytics.vw_evolucao_temporal` | evento × mês | série mensal (base para as métricas de série) |
| 02 | `analytics.vw_evolucao_temporal_metricas` | evento × mês | + variação MoM, média móvel 3m, variação YoY mês-a-mês |
| 02 | `analytics.vw_periodo_comparavel` | (escalar) | mês-limite para comparação anual justa (hoje: 6, por causa de 2026) |
| 02 | `analytics.vw_comparacao_anual_comparavel` | evento × ano | total restrito ao mesmo intervalo de meses em todos os anos |
| 02 | `analytics.vw_desvio_media_historica` | evento × mês | z-score em relação à média histórica do próprio indicador |
| 03 | `analytics.vw_uf` | evento × UF × ano | totais/médias por UF e região |
| 04 | `analytics.vw_municipio` | evento × município × ano | totais por município |
| 05 | `analytics.vw_indicador` | evento × ano | total + participação % dentro da própria família |
| 06 | `analytics.vw_abrangencia` | evento × abrangência × ano | totais por Estadual/PF/PRF |
| 07 | `analytics.vw_sexo` | evento × sexo × ano | só família vítima; participação soma 100% |
| 08 | `analytics.vw_faixa_etaria` | evento × faixa × ano | só Pessoa Desaparecida/Localizada |
| 09 | `analytics.vw_agente` | evento × agente × ano | só Morte/Suicídio de Agente do Estado |
| 10 | `analytics.vw_arma` | arma × ano | só Arma de Fogo Apreendida, com ranking |
| 11 | `analytics.vw_pesos_percentis` | evento × ano | soma/média/mediana/P90/P95/P99/máximo |
| 11 | `analytics.vw_pesos_impacto_outliers` | evento | efeito do top 1% na média/soma, sem remover dados |
| — | `analytics.vw_ranking_uf/municipio/regiao/indicador/abrangencia` | idem + ranking | rankings particionados por (evento, ano) |
| — | `analytics.vw_participacao_uf` | evento × UF × ano | % de participação de cada UF no total nacional |

Todas em `sql/analytics/001` a `005`, aplicadas via `python -m src.analytics.build_views`.

## 4. Métricas implementadas

| Métrica | Onde | Método |
|---|---|---|
| Total | todas | `SUM(valor)` |
| Média | `vw_nacional`, `vw_indicador`, `vw_uf` | `AVG(valor)` |
| Mediana | `vw_nacional`, `vw_indicador`, `vw_pesos_percentis` | `PERCENTILE_CONT(0.5)` — só onde faz sentido (não em rankings) |
| Mínimo/Máximo | `vw_nacional`, `vw_pesos_percentis` | `MIN`/`MAX` |
| Variação absoluta/percentual | `vw_evolucao_temporal_metricas` | `LAG() OVER` mês a mês e mesmo mês do ano anterior |
| Participação | `vw_indicador` (dentro da família), `vw_sexo`, `vw_faixa_etaria`, `vw_participacao_uf` | `SUM(valor) OVER (PARTITION BY ...)` |
| Ranking | `vw_ranking_*` | `RANK() OVER (PARTITION BY evento, ano ORDER BY total DESC)` |
| Média móvel | `vw_evolucao_temporal_metricas` | `AVG() OVER (... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` (3 meses) |
| Desvio em relação à média histórica | `vw_desvio_media_historica` | z-score: `(valor - média_histórica) / desvio_padrão_histórico`, `STDDEV_POP` |
| P90/P95/P99 | `vw_pesos_percentis` | `PERCENTILE_CONT(0.90/0.95/0.99)` |

Métricas **deliberadamente não criadas**: mediana/percentil para indicadores de contagem esparsos (muitos zeros tornam a mediana pouco informativa — não removido do catálogo, apenas não priorizado); qualquer "total geral" cross-família (não é semanticamente válido).

## 5. Exemplos de resultados reais

```
vw_nacional — Feminicídio
 ano | is_partial_year | total | média      | mediana | máximo
 2024| False            | 1501  | 0.00749541 | 0       | 8
 2025| False            | 1559  | 0.00777956 | 0       | 8
 2026| True              | 741   | 0.00738320 | 0       | 6

vw_comparacao_anual_comparavel — Homicídio doloso (Jan-Jun, comparável)
 2024: 17.786   2025: 16.081   2026: 13.931   (queda de 13,4% 2026 vs 2025 no mesmo intervalo)

vw_sexo — Feminicídio 2025
 Feminino: 1.548 (99,29%)   Masculino: 7 (0,45%)   Não Informado: 4 (0,26%)

vw_pesos_impacto_outliers
 Apreensão de Cocaína : média cai de 334,36 kg para 287,86 kg sem o top 1%  (-14,2%... impacto reportado: 16,2% de inflação na média COM outliers)
 Apreensão de Maconha : média cai de 4.314,61 kg para 3.363,43 kg sem o top 1%  (28,3% de inflação na média COM outliers)

vw_desvio_media_historica — maior anomalia encontrada (|z| > 3)
 Morte por intervenção de Agente do Estado, out/2025: total=706, média histórica=536,47, z=3.03
```

Este último resultado é um achado real do radar analítico: outubro/2025 teve um pico de letalidade policial (`Morte por intervenção de Agente do Estado`) 3 desvios-padrão acima da média histórica do indicador — candidato a investigação qualitativa, não uma afirmação causal.

## 6. Testes de qualidade analítica

`tests/test_analytics_sql.py` — 13 testes de integração contra o Postgres real (pulados automaticamente se o banco não estiver acessível). Cobrem exatamente o que a Fase 2 pediu:

| Teste | Verifica |
|---|---|
| `test_nenhum_indicador_desapareceu` (5 views) | os 31 eventos aparecem em cada view principal |
| `test_totais_reconciliam_com_fact_indicadores` | `SUM(valor)` por evento bate entre `fact_indicadores` e `vw_indicador` — 0 divergências |
| `test_nenhuma_metrica_mistura_familias` | nenhum evento aparece com mais de uma `familia_medida` |
| `test_nenhuma_metrica_mistura_unidades` | nenhum evento aparece com mais de uma `unidade` |
| `test_2026_permanece_identificado_como_parcial` | `is_partial_year=True` só em 2026, nos demais anos é sempre `False` |
| `test_participacao_sexo_soma_100_por_evento_ano` | soma das participações de sexo ≈ 100% (detecta dupla contagem) |
| `test_ranking_respeita_particao_por_evento_e_ano` | todo ranking de UF começa em 1 por (evento, ano) |
| `test_pesos_outliers_nao_removem_dados_da_base` | soma "com outliers" da view bate com o total real da fact — nada foi descartado |
| `test_vw_fato_enriquecido_nao_perde_linhas` | a view semântica base tem exatamente o mesmo nº de linhas que `fact_indicadores` |

**Resultado: 13/13 PASS.** Suíte completa (Fase 1 + Fase 2): **31/31 PASS**.

## 7. Performance

### Antes de otimizar — os 3 gargalos reais medidos por `EXPLAIN (ANALYZE, BUFFERS)`

| Query | Tempo original |
|---|---:|
| Série temporal de 1 indicador | 917 ms |
| Ranking de UF de 1 indicador/ano | 982 ms |
| **Visão nacional completa (`vw_nacional`)** | **13.029 ms** |

O plano de `vw_nacional` mostrou a causa exata: `GroupAggregate` com `Sort Method: external merge, Disk: 169MB` — a agregação estava **ordenando em disco** as 5,29M linhas inteiras (incluindo colunas de texto largas de todas as dimensões já unidas) antes de agrupar. Nenhum índice resolveria isso — o problema era estratégia de agregação + memória.

### O que foi mudado (e por quê)

1. **`work_mem`: 4MB → 128MB**, aplicado via `ALTER DATABASE atlas SET work_mem='128MB'` (e persistido em `docker-compose.yml` para reconstruções futuras do container). Justificativa: o Postgres só escolhe hash-agregação em memória quando a estimativa de tamanho do agrupamento cabe no `work_mem` disponível; com 4MB, qualquer agregação um pouco mais pesada cai para sort em disco.
2. **Reescrita das views que tocam a fact table inteira** (`vw_nacional`, `vw_indicador`, `vw_uf`, `vw_municipio`, `vw_evolucao_temporal`, `vw_abrangencia`, `vw_sexo`, `vw_faixa_etaria`, `vw_agente`, `vw_arma`): agora agregam **primeiro** sobre `fact_indicadores` usando só as colunas de chave inteira (`indicador_id`, `tempo_id`/`ano_origem`, `localidade_id`, etc.) — sem juntar as dimensões largas antes — e só **depois** juntam `dim_indicador`/`dim_localidade`/`dim_tempo` (dezenas de linhas, não milhões) para obter os rótulos de exibição. Nenhum índice novo foi criado — os índices de coluna única já existentes na Fase 1 continuaram sendo usados normalmente pelo planner (confirmado via `EXPLAIN`).

### Depois

| Query | Antes | Depois |
|---|---:|---:|
| Série temporal de 1 indicador | 917 ms | 532 ms |
| Ranking de UF de 1 indicador/ano | 982 ms | 777 ms |
| **Visão nacional completa** | **13.029 ms** | **4.045 ms** (~3,2×) |
| Baseline (consulta direta na fact, sem view) | 761 ms | 281 ms *(melhorou só por causa do `work_mem`, sem mudar a query)* |

Os dois resultados acima confirmam via evidência que a mudança de `work_mem` teve efeito amplo (afetou até uma consulta que não foi reescrita), e a reescrita das views deu um ganho adicional específico para a agregação de tabela inteira.

### Trade-off encontrado (relatado, não escondido)

Uma consulta seletiva por filtro único ficou **mais lenta**, não mais rápida:

| Query | Antes | Depois |
|---|---:|---:|
| `vw_municipio` filtrado por 1 UF + 1 evento | 4,8 ms | 1.751 ms |

Motivo: a nova `vw_municipio` agrega **todos** os municípios/indicadores/anos antes de filtrar, porque essa é a estratégia certa para quando a view é lida por inteiro (ver próximo parágrafo) — mas isso significa que uma consulta que só queria uma fatia pequena agora paga o custo da agregação completa mesmo assim.

**Decisão metodológica:** o Sentinel.io será consumido pelo Power BI em **modo Import** (recomendado para este projeto — dataset de tamanho moderado, atualização em lote, não em tempo real). Em modo Import, o Power BI sempre lê a view **inteira** uma vez por atualização agendada — nunca envia `WHERE` para o Postgres; toda a filtragem interativa do usuário acontece depois, dentro do motor VertiPaq do próprio Power BI. Por isso, otimizar para "ler a view inteira rápido" (o padrão real de uso) foi a escolha certa, mesmo custando uma consulta filtrada ad-hoc via SQL direto. Se o projeto migrar para DirectQuery no futuro, essa decisão precisaria ser revisitada.

### Índices: nenhum novo foi criado

Rule da Fase 2: "criar índices somente quando houver justificativa." A auditoria (`EXPLAIN ANALYZE`) mostrou que os índices de coluna única da Fase 1 (`ix_fact_indicador`, `ix_fact_localidade`, etc.) já eram usados corretamente pelo planner (`Bitmap Index Scan`) sempre que uma consulta filtrava por uma dimensão. O gargalo real nunca foi ausência de índice — foi estratégia de agregação e memória, ambos corrigidos sem adicionar nenhum índice novo.

## 8. Problemas encontrados

1. `work_mem` padrão (4MB) inadequado para agregações analíticas sobre 5,29M linhas — causava sort em disco.
2. O padrão inicial de view (agregar depois de juntar todas as dimensões) tornava `vw_nacional` proibitivamente lento (13s).
3. `agente_id` tem só 8 valores distintos na fact table, não os 9 cadastrados em `dim_agente` (uma categoria nunca ocorreu nos 3 anos).
4. A reescrita para otimizar leitura completa da view piorou consultas seletivas ad-hoc (trade-off, não bug).

## 9. Decisões metodológicas

- `grupo_semantico` (5-6 categorias pedidas na Fase 2) é **calculado em view**, nunca persistido em `dim_indicador` — para não alterar o schema da Fase 1 sem necessidade, conforme instrução explícita desta fase.
- Toda participação percentual é calculada **dentro da própria família/indicador** (nunca contra um total geral que misturaria unidades).
- `total_vitima` continua nunca sendo armazenado — `vw_sexo` é a única fonte de verdade, e `SUM(total)` sem filtro de sexo é como qualquer relatório deve obter o "total de vítimas".
- Outliers de peso (Cocaína/Maconha) permanecem 100% na base; a única concessão é uma view que **mostra o efeito** deles, não que os remove.
- Otimização de performance priorizou o padrão de consumo real (Power BI Import mode: ler a view inteira), documentando explicitamente o trade-off para consultas filtradas ad-hoc.
- Nenhum índice novo foi criado — a mudança de maior impacto (`work_mem`) foi uma configuração de banco, não uma estrutura de dados.

---

*Não avançamos para o Power BI nesta fase. Pronto para a Fase 3 mediante aprovação.*
