# Sentinel.io — Validação PostgreSQL vs. Power BI

Regra da Fase 3 (seção 15): nenhuma diferença pode ser ignorada. A coluna **PostgreSQL** abaixo é o valor real, obtido por consulta direta ao banco (não estimado). A coluna **Power BI** deve ser preenchida ao abrir o `.pbix` já construído (colocar o visual/medida correspondente numa página, ler o número, colar aqui) — o **Status** só pode ser PASS se a diferença for zero (ou dentro de arredondamento de exibição, nunca de cálculo).

## Como preencher

Para cada linha: aplicar o mesmo filtro (indicador/ano/UF) num card ou tabela do Power BI usando a medida indicada na coluna "Medida DAX", copiar o valor mostrado, e comparar.

## Tabela de validação

| # | Métrica | Filtro | Medida DAX | PostgreSQL (real) | Power BI | Diferença | Status |
|---|---|---|---|---:|---|---|---|
| 1 | Total geral — família vítima | `familia_medida = 'vitima'` | `[Total Vítimas]` | 923.856 | _preencher_ | _preencher_ | _PASS/FAIL_ |
| 2 | Total geral — família contagem | `familia_medida = 'contagem'` | `[Total Ocorrências e Ações]` (ajustar filtro) | 12.771.602 | | | |
| 3 | Total geral — família peso | `familia_medida = 'peso'` | `[Total Peso Apreendido (kg)]` | 6.953.845,717 | | | |
| 4 | Feminicídio — total 2024 | evento=Feminicídio, ano=2024 | `[Total Vítimas]` (com slicer de indicador) | 1.501 | | | |
| 5 | Feminicídio — total 2025 | evento=Feminicídio, ano=2025 | idem | 1.559 | | | |
| 6 | Feminicídio — total 2026 (parcial) | evento=Feminicídio, ano=2026 | idem | 741 | | | |
| 7 | Feminicídio 2025 — % Feminino | evento=Feminicídio, ano=2025, sexo=Feminino | `[Participação % Sexo (no indicador)]` | 99,29% | | | |
| 8 | Feminicídio 2025 — % Masculino | idem, sexo=Masculino | idem | 0,45% | | | |
| 9 | Feminicídio 2025 — % Não Informado | idem, sexo=Não Informado | idem | 0,26% | | | |
| 10 | Homicídio doloso 2025 — Top 1 UF | evento=Homicídio doloso, ano=2025 | `[Ranking UF]` = 1 → UF | BA (3.663) | | | |
| 11 | Homicídio doloso 2025 — Top 2 UF | idem | `[Ranking UF]` = 2 → UF | RJ (3.342) | | | |
| 12 | Homicídio doloso — comparável Jan-Jun 2024 | `[Total Período Comparável]`, ano=2024 | `[Total Período Comparável]` | 17.786 | | | |
| 13 | Homicídio doloso — comparável Jan-Jun 2025 | idem, ano=2025 | idem | 16.081 | | | |
| 14 | Homicídio doloso — comparável Jan-Jun 2026 | idem, ano=2026 | idem | 13.931 | | | |
| 15 | Apreensão de Cocaína — soma (todos os anos) | evento=Apreensão de Cocaína | `[Total Peso Apreendido (kg)]` | 499.195,813 | | | |
| 16 | Apreensão de Maconha — soma (todos os anos) | evento=Apreensão de Maconha | idem | 6.454.649,904 | | | |
| 17 | Apreensão de Cocaína — P99 (3 anos agregados) | evento=Apreensão de Cocaína | `[P99 Peso (kg)]` | 3.330,84 | | | |
| 17b | Apreensão de Maconha — P99 (3 anos agregados) | evento=Apreensão de Maconha | idem | 66.296,56 | | | |
| 18 | Impacto outliers — Cocaína (3 anos agregados) | evento=Apreensão de Cocaína | `[Impacto % dos Outliers na Média]` | 16,2% | | | |
| 18b | Impacto outliers — Maconha (3 anos agregados) | evento=Apreensão de Maconha | idem | 28,3% | | | |
| 19 | Radar — maior \|Z-Score\| do período | Morte por intervenção de Agente do Estado, out/2025 | `[Z-Score]` | 3,03 (total 706, média histórica 536,47) | | | |
| 20 | Data Quality — total de indicadores | (sem filtro) | `[Total Indicadores]` | 31 | | | |
| 21 | Data Quality — total de UFs | (sem filtro) | `[Total UFs]` | 27 | | | |
| 22 | Data Quality — meses em anos parciais | (sem filtro) | `[Meses em Anos Parciais]` | 6 | | | |
| 23 | Data Quality — % não informado, Tráfico de drogas | evento=Tráfico de drogas | `[% Não Informado (indicador selecionado)]` | 0,00% | | | |
| 24 | Data Quality — % não informado, Roubo de carga | evento=Roubo de carga | idem | 51,36% | | | |

## Consultas SQL usadas para gerar a coluna PostgreSQL (reprodutíveis)

```sql
-- Linhas 1-3
SELECT di.familia_medida, SUM(f.valor) FROM fact_indicadores f
JOIN dim_indicador di ON f.indicador_id = di.indicador_id GROUP BY 1;

-- Linhas 4-6
SELECT t.ano, SUM(f.valor) FROM fact_indicadores f
JOIN dim_indicador di ON f.indicador_id = di.indicador_id
JOIN dim_tempo t ON f.tempo_id = t.tempo_id
WHERE di.evento = 'Feminicídio' GROUP BY t.ano ORDER BY t.ano;

-- Linhas 7-9
SELECT * FROM analytics.vw_sexo WHERE evento = 'Feminicídio' AND ano = 2025;

-- Linhas 10-11
SELECT uf, SUM(f.valor) AS total FROM fact_indicadores f
JOIN dim_indicador di ON f.indicador_id=di.indicador_id
JOIN dim_localidade l ON f.localidade_id=l.localidade_id
JOIN dim_tempo t ON f.tempo_id=t.tempo_id
WHERE di.evento='Homicídio doloso' AND t.ano=2025
GROUP BY uf ORDER BY total DESC LIMIT 5;

-- Linhas 12-14
SELECT * FROM analytics.vw_comparacao_anual_comparavel WHERE evento = 'Homicídio doloso';

-- Linhas 15-18
SELECT * FROM analytics.vw_pesos_percentis;
SELECT * FROM analytics.vw_pesos_impacto_outliers;

-- Linha 19
SELECT * FROM analytics.vw_desvio_media_historica
WHERE evento = 'Morte por intervenção de Agente do Estado' AND data_referencia = '2025-10-01';

-- Linhas 20-24
SELECT * FROM analytics.vw_qualidade_resumo;
SELECT * FROM analytics.vw_qualidade_nao_informado
WHERE evento IN ('Tráfico de drogas', 'Roubo de carga');
```

## Sobre diferenças de arredondamento

Percentuais exibidos com 2 casas decimais podem divergir na última casa entre SQL (`ROUND` no Postgres) e Power BI (formatação de exibição do DAX) sem que isso seja um FAIL real — conferir o valor **não arredondado** (aumentar casas decimais no card) antes de marcar FAIL nesses casos.
