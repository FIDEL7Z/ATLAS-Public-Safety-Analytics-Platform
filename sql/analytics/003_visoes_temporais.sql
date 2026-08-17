-- ATLAS — Fase 2 — 02: Evolução temporal + métricas de série (MoM, média
-- móvel, comparação ano-a-ano respeitando ano parcial, desvio em relação à
-- média histórica).
--
-- Mesma estratégia de performance do arquivo 002: agrega direto sobre
-- fact_indicadores usando só (indicador_id, tempo_id) — dois inteiros — e só
-- depois junta dim_indicador/dim_tempo (30 linhas) para os rótulos.

DROP VIEW IF EXISTS analytics._agg_indicador_tempo CASCADE;
CREATE VIEW analytics._agg_indicador_tempo AS
SELECT indicador_id, tempo_id, SUM(valor) AS total
FROM fact_indicadores
GROUP BY indicador_id, tempo_id;

-- 02a — série mensal por indicador (base para as métricas de série abaixo)
DROP VIEW IF EXISTS analytics.vw_evolucao_temporal CASCADE;
CREATE VIEW analytics.vw_evolucao_temporal AS
SELECT
    i.evento, i.familia_medida, i.unidade,
    CASE
        WHEN i.tipo_indicador LIKE 'Vítima%' OR i.tipo_indicador LIKE 'Pessoa%' THEN 'Vítimas'
        WHEN i.tipo_indicador = 'Ação Policial' THEN 'Ações Policiais'
        WHEN i.tipo_indicador LIKE 'Ocorrência%' THEN 'Ocorrências'
        WHEN i.tipo_indicador = 'Apreensão - Peso' THEN 'Apreensões (Peso)'
        WHEN i.tipo_indicador = 'Apreensão - Unidade' THEN 'Apreensões (Unidade)'
        WHEN i.tipo_indicador LIKE 'Serviço%' THEN 'Serviços'
        ELSE 'Outro'
    END AS grupo_semantico,
    t.data_referencia, t.ano, t.mes, t.trimestre, t.nome_mes, t.is_partial_year,
    a.total
FROM analytics._agg_indicador_tempo a
JOIN dim_indicador i ON a.indicador_id = i.indicador_id
JOIN dim_tempo t ON a.tempo_id = t.tempo_id;

COMMENT ON VIEW analytics.vw_evolucao_temporal IS '02 — Série mensal de total por indicador.';

-- 02b — métricas derivadas da série: variação mês a mês, média móvel de 3
-- meses, valor do mesmo mês no ano anterior (para YoY mês-a-mês).
-- Estas janelas operam sobre a série já agregada (31 indicadores x 30 meses
-- = ~930 linhas no máximo), não sobre a fact table.
DROP VIEW IF EXISTS analytics.vw_evolucao_temporal_metricas CASCADE;
CREATE VIEW analytics.vw_evolucao_temporal_metricas AS
SELECT
    e.*,
    LAG(total) OVER w AS total_mes_anterior,
    total - LAG(total) OVER w AS variacao_absoluta_mom,
    ROUND(100.0 * (total - LAG(total) OVER w) / NULLIF(LAG(total) OVER w, 0), 2) AS variacao_pct_mom,
    AVG(total) OVER (
        PARTITION BY evento ORDER BY data_referencia
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS media_movel_3m,
    LAG(total, 12) OVER w AS total_mesmo_mes_ano_anterior,
    ROUND(
        100.0 * (total - LAG(total, 12) OVER w) / NULLIF(LAG(total, 12) OVER w, 0),
        2
    ) AS variacao_pct_yoy_mesmo_mes
FROM analytics.vw_evolucao_temporal e
WINDOW w AS (PARTITION BY evento ORDER BY data_referencia);

COMMENT ON VIEW analytics.vw_evolucao_temporal_metricas IS
'02 — Variação mês a mês (absoluta e %), média móvel de 3 meses, e comparação ano-a-ano MÊS A MÊS (ex.: fev/2026 vs fev/2025) — nunca ano completo vs ano parcial.';

-- 02c — período comparável entre anos: o maior mês disponível em QUALQUER
-- ano marcado como parcial define o corte aplicado a TODOS os anos (não
-- hardcoded para 2026 — se um ano futuro também vier parcial, o corte se
-- ajusta automaticamente ao mês mais restritivo).
DROP VIEW IF EXISTS analytics.vw_periodo_comparavel CASCADE;
CREATE VIEW analytics.vw_periodo_comparavel AS
SELECT COALESCE(MIN(mes_maximo_ano_parcial), 12) AS mes_limite
FROM (
    SELECT MAX(mes) AS mes_maximo_ano_parcial
    FROM dim_tempo WHERE is_partial_year
) sub;

COMMENT ON VIEW analytics.vw_periodo_comparavel IS
'Mês-limite (1-12) usado para comparações ano-a-ano justas: o menor entre "meses disponíveis nos anos parciais" e 12. Se não houver ano parcial, vale 12 (ano cheio).';

-- 02d — comparação anual JUSTA (mesmo intervalo de meses em todos os anos)
DROP VIEW IF EXISTS analytics.vw_comparacao_anual_comparavel CASCADE;
CREATE VIEW analytics.vw_comparacao_anual_comparavel AS
SELECT
    e.evento, e.familia_medida, e.unidade, e.ano,
    bool_or(e.is_partial_year) AS is_partial_year,
    p.mes_limite AS meses_incluidos,
    SUM(e.total) AS total_periodo_comparavel
FROM analytics.vw_evolucao_temporal e
CROSS JOIN analytics.vw_periodo_comparavel p
WHERE e.mes <= p.mes_limite
GROUP BY e.evento, e.familia_medida, e.unidade, e.ano, p.mes_limite;

COMMENT ON VIEW analytics.vw_comparacao_anual_comparavel IS
'Compara anos usando SEMPRE o mesmo intervalo de meses (ex.: Jan-Jun em todos os anos, se 2026 só tem até junho) — nunca ano completo contra ano parcial.';

-- desvio em relação à média histórica (z-score, método explicável — sem ML)
DROP VIEW IF EXISTS analytics.vw_desvio_media_historica CASCADE;
CREATE VIEW analytics.vw_desvio_media_historica AS
WITH stats AS (
    SELECT evento, AVG(total) AS media_historica, STDDEV_POP(total) AS desvio_padrao_historico
    FROM analytics.vw_evolucao_temporal
    GROUP BY evento
)
SELECT
    e.evento, e.familia_medida, e.unidade, e.data_referencia, e.ano, e.mes, e.is_partial_year,
    e.total, st.media_historica, st.desvio_padrao_historico,
    CASE WHEN st.desvio_padrao_historico > 0
         THEN ROUND((e.total - st.media_historica) / st.desvio_padrao_historico, 2)
         ELSE NULL END AS z_score
FROM analytics.vw_evolucao_temporal e
JOIN stats st ON e.evento = st.evento;

COMMENT ON VIEW analytics.vw_desvio_media_historica IS
'Z-score de cada mês em relação à média histórica do PRÓPRIO indicador (nunca comparado entre indicadores de família diferente). |z| > 2 é candidato a mês atípico.';
